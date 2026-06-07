#!/usr/bin/env python3
"""
ERD Design — DDL Export

ERD 메타데이터(/api/v1/erd/...)를 PAT 토큰으로 조회하여 MySQL DDL 텍스트로 변환한다.
실제 DB에는 절대 실행하지 않고, 파일(또는 stdout)로만 출력한다.

Usage:
    python3 ddl_export.py --diagram-id <DIAGRAM_ID> [-o <out>] [--dry-run]
    python3 ddl_export.py --project-id <PROJECT_ID> [-o <out>] [--dry-run]

Env:
    BLOGN_PAT_TOKEN — Personal Access Token (prefix "softn_pat_", scope must include "erd")
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE_URL = "https://back.softn.kr"
TIMEOUT = 30


class ApiError(RuntimeError):
    pass


def _headers() -> Dict[str, str]:
    token = os.environ.get("BLOGN_PAT_TOKEN")
    if not token:
        raise ApiError(
            "BLOGN_PAT_TOKEN environment variable is not set.\n"
            "  Issue a PAT at https://back.softn.kr (scope must include 'erd') and:\n"
            "    export BLOGN_PAT_TOKEN=\"softn_pat_xxxxxxxx...\""
        )
    if not token.startswith("softn_pat_"):
        raise ApiError("BLOGN_PAT_TOKEN must start with 'softn_pat_'.")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def _get(path: str) -> Any:
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.get(url, headers=_headers(), timeout=TIMEOUT)
    except requests.RequestException as e:
        raise ApiError(f"GET {path} failed: {e}") from e
    if resp.status_code == 401:
        raise ApiError("401 Unauthorized — PAT may be expired or invalid.")
    if resp.status_code == 403:
        raise ApiError(f"403 Forbidden — insufficient role for {path}.")
    if resp.status_code == 404:
        raise ApiError(f"404 Not Found — {path}")
    if resp.status_code >= 400:
        raise ApiError(f"GET {path} → HTTP {resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    if not body.get("success", False):
        raise ApiError(f"GET {path} → success=false: {body.get('message')}")
    return body.get("data")


def fetch_project(project_id: str) -> Dict[str, Any]:
    return _get(f"/api/v1/erd/project/{project_id}") or {}


def fetch_diagrams(project_id: str) -> List[Dict[str, Any]]:
    return _get(f"/api/v1/erd/project/{project_id}/diagram/list") or []


def fetch_tables(diagram_id: str) -> List[Dict[str, Any]]:
    return _get(f"/api/v1/erd/diagram/{diagram_id}/table/list") or []


def fetch_indexes(table_id: str) -> List[Dict[str, Any]]:
    try:
        return _get(f"/api/v1/erd/table/{table_id}/index/list") or []
    except ApiError:
        return []


def fetch_table_columns(table_id: str) -> List[Dict[str, Any]]:
    try:
        return _get(f"/api/v1/erd/table/{table_id}/column/list") or []
    except ApiError:
        return []


def project_id_from_diagram(diagram_id: str) -> Optional[str]:
    diagram = _get(f"/api/v1/erd/diagram/{diagram_id}")
    if isinstance(diagram, dict):
        return diagram.get("projectId")
    return None


# ───────────────────────────── DDL formatting ─────────────────────────────

WARN_BANNER = (
    "-- ============================================================\n"
    "-- WARNING: This DDL is generated from ERD metadata.\n"
    "-- The erd-design skill never executes DDL against real databases.\n"
    "-- Review carefully and apply manually via your migration process.\n"
    "-- ============================================================\n"
)


def _q(name: str) -> str:
    return f"`{name}`"


def _flag(col: Dict[str, Any], key: str) -> bool:
    val = col.get(key)
    return val == 1 or val == "1" or val is True


def _physical_name(col: Dict[str, Any]) -> str:
    """컬럼 물리명 = columnId (ERD_COLUMN 컨벤션: columnId=물리명, columnName=한글 논리명)."""
    return col.get("columnId") or col.get("columnName") or "UNNAMED"


def _column_def(col: Dict[str, Any]) -> str:
    name = _physical_name(col)
    data_type = (col.get("dataType") or "VARCHAR(255)").strip()
    parts: List[str] = [_q(name), data_type]

    if _flag(col, "notnullFlag") or _flag(col, "primarykeyFlag"):
        parts.append("NOT NULL")
    else:
        parts.append("NULL")

    if _flag(col, "autoIncreaseFlag"):
        parts.append("AUTO_INCREMENT")

    default = col.get("defaultValue")
    if default not in (None, ""):
        s = str(default).strip()
        upper = s.upper()
        if upper in ("CURRENT_TIMESTAMP", "NULL") or s.startswith("'") or s.replace(".", "", 1).isdigit():
            parts.append(f"DEFAULT {s}")
        else:
            esc = s.replace("'", "''")
            parts.append(f"DEFAULT '{esc}'")

    # 한글 논리명(columnName)은 컬럼 COMMENT 로 보존
    logical = (col.get("columnName") or "").strip()
    if logical and logical != name:
        esc = logical.replace("'", "''")
        parts.append(f"COMMENT '{esc}'")

    return " ".join(parts)


def _primary_key_clause(columns: List[Dict[str, Any]]) -> Optional[str]:
    pk_cols = [c for c in columns if _flag(c, "primarykeyFlag")]
    if not pk_cols:
        return None
    pk_cols.sort(key=lambda c: c.get("displayOrder") or 0)
    names = ", ".join(_q(_physical_name(c)) for c in pk_cols)
    return f"PRIMARY KEY ({names})"


def _index_clauses(table_id: str, columns_by_id: Dict[str, Dict[str, Any]]) -> List[str]:
    clauses: List[str] = []
    indexes = fetch_indexes(table_id)
    for idx in indexes or []:
        idx_type = (idx.get("indexType") or "").upper()
        if idx_type == "PRIMARY":
            continue  # PK는 _primary_key_clause로 처리
        if idx_type == "FOREIGN":
            continue  # FK는 _fk_clauses로 ALTER 문으로 처리

        unique = _flag(idx, "uniqueFlag") or idx_type == "UNIQUE"
        idx_name = idx.get("indexName") or idx.get("indexId") or "IDX"
        idx_cols = sorted(
            idx.get("indexColumns") or [],
            key=lambda c: c.get("displayOrder") or 0,
        )
        col_exprs: List[str] = []
        for ic in idx_cols:
            col_id = ic.get("columnId")
            col = columns_by_id.get(col_id)
            # 물리명 = columnId. indexColumns[].columnId 가 이미 물리명이므로 fallback 도 col_id.
            col_name = _physical_name(col) if col else col_id
            if not col_name:
                continue
            sort = (ic.get("sortType") or "").upper()
            expr = _q(col_name)
            if sort in ("ASC", "DESC"):
                expr += f" {sort}"
            col_exprs.append(expr)
        if not col_exprs:
            continue
        kw = "UNIQUE KEY" if unique else "KEY"
        clauses.append(f"{kw} {_q(idx_name)} ({', '.join(col_exprs)})")
    return clauses


def _table_ddl(table: Dict[str, Any]) -> str:
    physical = table.get("physicalName") or table.get("logicalName") or table.get("tableId")
    logical = table.get("logicalName") or ""
    columns = sorted(table.get("columns") or [], key=lambda c: c.get("displayOrder") or 0)

    lines: List[str] = [f"CREATE TABLE {_q(physical)} ("]
    body: List[str] = [f"  {_column_def(c)}" for c in columns]

    pk = _primary_key_clause(columns)
    if pk:
        body.append(f"  {pk}")

    columns_by_id = {c.get("columnId"): c for c in columns}
    body.extend(f"  {clause}" for clause in _index_clauses(table.get("tableId"), columns_by_id))

    lines.append(",\n".join(body))
    suffix = "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    if logical:
        suffix += f" COMMENT='{logical.replace(chr(39), chr(39)*2)}'"
    lines.append(f") {suffix};")
    return "\n".join(lines)


def _fk_clauses(tables: List[Dict[str, Any]]) -> List[str]:
    """FK 인덱스(indexType=FOREIGN)로부터 FOREIGN KEY ALTER 문 생성.

    각 자식 테이블의 인덱스 중 FOREIGN 타입을 추출하여 indexColumns 의
    columnId(자식 FK 컬럼) ↔ sourceColumnId(부모 PK 컬럼) 정확한 매핑으로 ALTER 생성.
    onDeleteAction / onUpdateAction 도 반영.
    cross-diagram source 인 경우 응답의 sourcePhysicalName 사용 fallback.
    """
    table_by_id = {t.get("tableId"): t for t in tables}

    # 부모 컬럼 lookup 캐시 (cross-diagram 대비 — 다른 다이어그램 테이블의 컬럼은 별도 fetch)
    parent_columns_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def _parent_columns_by_id(parent_table_id: str) -> Dict[str, Dict[str, Any]]:
        if parent_table_id in parent_columns_cache:
            return parent_columns_cache[parent_table_id]
        parent = table_by_id.get(parent_table_id)
        if parent and parent.get("columns"):
            mapping = {c.get("columnId"): c for c in parent.get("columns")}
        else:
            # cross-diagram fallback — 별도 컬럼 조회
            mapping = {c.get("columnId"): c for c in fetch_table_columns(parent_table_id)}
        parent_columns_cache[parent_table_id] = mapping
        return mapping

    out: List[str] = []
    for child in tables:
        child_id = child.get("tableId")
        child_phys = child.get("physicalName") or child_id
        child_cols_by_id = {c.get("columnId"): c for c in (child.get("columns") or [])}

        indexes = fetch_indexes(child_id)
        for idx in indexes or []:
            if (idx.get("indexType") or "").upper() != "FOREIGN":
                continue
            source_id = idx.get("sourceTableId")
            if not source_id:
                continue

            parent = table_by_id.get(source_id)
            parent_phys = (parent and parent.get("physicalName")) or idx.get("sourcePhysicalName") or source_id
            parent_cols = _parent_columns_by_id(source_id)

            idx_cols = sorted(idx.get("indexColumns") or [], key=lambda c: c.get("displayOrder") or 0)
            child_col_names: List[str] = []
            parent_col_names: List[str] = []
            for ic in idx_cols:
                # 자식·부모 FK 컬럼 물리명 = columnId / sourceColumnId (둘 다 물리명).
                c_id = ic.get("columnId")
                c_col = child_cols_by_id.get(c_id)
                child_col_names.append(_q((c_col and _physical_name(c_col)) or c_id))

                p_id = ic.get("sourceColumnId")
                if p_id:
                    p_col = parent_cols.get(p_id)
                    parent_col_names.append(_q((p_col and _physical_name(p_col)) or p_id))
                else:
                    parent_col_names.append("/* TODO: sourceColumnId 누락 */")

            if not child_col_names:
                continue

            fk_name = idx.get("indexName") or idx.get("indexId") or f"FK_{child_phys}"

            on_delete_raw = (idx.get("onDeleteAction") or "").upper()
            on_update_raw = (idx.get("onUpdateAction") or "").upper()
            actions: List[str] = []
            if on_delete_raw and on_delete_raw != "NO_ACTION":
                actions.append(f"ON DELETE {on_delete_raw.replace('_', ' ')}")
            if on_update_raw and on_update_raw != "NO_ACTION":
                actions.append(f"ON UPDATE {on_update_raw.replace('_', ' ')}")
            actions_str = (" " + " ".join(actions)) if actions else ""

            src_diagram = idx.get("sourceDiagramName") or idx.get("sourceDiagramId")
            comment = f"-- FK {child_phys} -> {parent_phys}"
            if src_diagram and parent and src_diagram != child.get("diagramName"):
                comment += f" (cross-diagram: {src_diagram})"
            elif not parent:
                comment += " (cross-diagram source)"

            out.append(
                f"{comment}\n"
                f"ALTER TABLE {_q(child_phys)}\n"
                f"  ADD CONSTRAINT {_q(fk_name)} FOREIGN KEY ({', '.join(child_col_names)})\n"
                f"  REFERENCES {_q(parent_phys)} ({', '.join(parent_col_names)}){actions_str};"
            )
    return out


def build_ddl_for_diagram(diagram_id: str, header: str = "") -> str:
    tables = fetch_tables(diagram_id)
    chunks: List[str] = [WARN_BANNER]
    if header:
        chunks.append(header.rstrip() + "\n")
    chunks.append(f"-- diagramId: {diagram_id}")
    chunks.append(f"-- table count: {len(tables)}\n")
    for t in tables:
        chunks.append(_table_ddl(t))
        chunks.append("")
    fk = _fk_clauses(tables)
    if fk:
        chunks.append("-- Foreign keys")
        chunks.extend(fk)
        chunks.append("")
    return "\n".join(chunks)


# ────────────────────────────────── CLI ──────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export ERD metadata to MySQL DDL (read-only; never executes against DB)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--diagram-id", help="Single diagram to export.")
    group.add_argument("--project-id", help="All diagrams in the project.")
    parser.add_argument("-o", "--output", help="Output file path. Default: temp/erd-export/<diagramId>/ddl.sql")
    parser.add_argument("--dry-run", action="store_true", help="Print DDL to stdout without writing a file.")

    args = parser.parse_args(argv)

    try:
        if args.diagram_id:
            ddl = build_ddl_for_diagram(args.diagram_id)
            default_out = Path("temp/erd-export") / args.diagram_id / "ddl.sql"
        else:
            project = fetch_project(args.project_id)
            project_name = project.get("projectName") or args.project_id
            diagrams = fetch_diagrams(args.project_id)
            if not diagrams:
                print(f"No diagrams found for project {args.project_id}.", file=sys.stderr)
                return 1
            parts: List[str] = [WARN_BANNER, f"-- project: {project_name} ({args.project_id})", ""]
            for d in diagrams:
                did = d.get("diagramId")
                dname = d.get("diagramName") or did
                parts.append(f"-- ---- diagram: {dname} ({did}) ----")
                parts.append(build_ddl_for_diagram(did))
                parts.append("")
            ddl = "\n".join(parts)
            default_out = Path("temp/erd-export") / args.project_id / "ddl.sql"
    except ApiError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if args.dry_run:
        sys.stdout.write(ddl)
        return 0

    out_path = Path(args.output) if args.output else default_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(ddl, encoding="utf-8")
    print(f"Wrote DDL to {out_path}")
    print("Reminder: this file is NOT executed against any database. Review and apply manually.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
