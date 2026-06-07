# ERD DDL 생성 (B 모드)

ERD 메타에서 MySQL DDL 추출. **DB에 실행하지 않고 파일로만 저장한다.**

## 사용 시점

자연어에 다음 키워드가 포함되면 발동:
- "DDL 생성/추출", "SQL 스크립트", "CREATE TABLE 만들어줘", "스키마 추출"

## 실행

```bash
# 프로젝트 루트(cwd)에서 실행 — 산출물 temp/erd-export/ 가 현재 프로젝트에 생성된다
python3 "${CLAUDE_PLUGIN_ROOT}/skills/erd-design/ddl_export.py" --diagram-id <DIAGRAM_ID>
# 또는
python3 "${CLAUDE_PLUGIN_ROOT}/skills/erd-design/ddl_export.py" --project-id <PROJECT_ID>
```

옵션:
- `--diagram-id <id>` — 단일 다이어그램만 추출
- `--project-id <id>` — 프로젝트 내 모든 다이어그램 추출
- `-o <path>` — 출력 파일 경로 (기본: `temp/erd-export/<diagramId>/ddl.sql`)
- `--dry-run` — 파일 저장 없이 stdout으로 출력

## 사전 조건

- `BLOGN_PAT_TOKEN` 환경변수 설정
- `pip3 install -r "${CLAUDE_PLUGIN_ROOT}/skills/erd-design/requirements.txt"`

## 컬럼명 규칙

DDL의 물리 컬럼명은 `ERD_COLUMN.columnId`(물리명, 예: `DOC_ID`)에서 산출하고, `columnName`(한글 논리명, 예: `문서 아이디`)은 컬럼 `COMMENT '...'` 로 보존한다. PK·인덱스·FK 컬럼 참조도 모두 `columnId` 기준이다 ([CONVENTIONS.md §4](CONVENTIONS.md)).

## 산출 파일

```
temp/erd-export/{diagramId}/
└── ddl.sql        # CREATE TABLE + INDEX + FK 제약 (모두 SQL 텍스트, 실행 안 됨)
```

`ddl.sql` 상단에는 다음 경고 주석이 자동 삽입된다:

```sql
-- WARNING: This DDL is generated from ERD metadata.
-- Review carefully before applying. The erd-design skill never executes DDL.
-- Apply manually via your DB migration process.
```
