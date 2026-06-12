"""BlogN blog-editor — Editor.js 블록 빌더 + HTTP 헬퍼.

긴 본문을 한 번에 작성·저장할 때 보일러플레이트(블록 ID 랜덤화, wrapper 구성,
PAT 헤더, lockTimestamp 흐름) 를 제거하는 공용 유틸리티.

사용:
    import os, sys; sys.path.insert(0, os.environ["CLAUDE_PLUGIN_ROOT"] + "/skills/blog-editor")
    from block_builder import (
        header, paragraph, code, ulist, olist, checklist, quote,
        delimiter, table, image, embed, attaches,
        document, create_post, get_post, put_post_contents, update_post_meta,
        upload_image, upload_attachment, get_file, delete_file,
        markdown_to_document, document_to_markdown,
    )

    blocks = [
        header("배경"),
        paragraph("본문 한 문단..."),
        code("SELECT 1"),
    ]
    post = create_post(blog_id="DY-DEVEL", title="제목", clsf_id="...")
    put_post_contents(
        blog_id="DY-DEVEL",
        post_id=post["postId"],
        lock_timestamp=post["lockTimestamp"],
        blocks=blocks,
    )

스펙 출처: ${CLAUDE_PLUGIN_ROOT}/skills/blog-editor/BLOCKS.md (Editor.js 2.28.1).
표준 외 필드는 추가하지 않는다.
"""

from __future__ import annotations

import json
import os
import random
import string
import time
import urllib.error
import urllib.request
from typing import Any, Iterable

BASE_URL = "https://back.softn.kr"
EDITORJS_VERSION = "2.28.1"
_ID_ALPHABET = string.ascii_letters + string.digits


# ─────────────────────────────────────────────────────────────────────
# 블록 빌더 — 모든 함수는 Editor.js 블록 dict 를 반환한다.
# ─────────────────────────────────────────────────────────────────────

def random_block_id() -> str:
    """10자 [a-zA-Z0-9] 무작위 블록 ID."""
    return "".join(random.choices(_ID_ALPHABET, k=10))


def _block(block_type: str, data: dict, *, id: str | None = None) -> dict:
    return {"id": id or random_block_id(), "type": block_type, "data": data}


def paragraph(text: str, *, id: str | None = None) -> dict:
    return _block("paragraph", {"text": text}, id=id)


def header(text: str, level: int = 1, *, id: str | None = None) -> dict:
    if level not in (1, 2, 3, 4, 5, 6):
        raise ValueError(f"header level must be 1..6, got {level}")
    return _block("header", {"text": text, "level": level}, id=id)


def code(source: str, *, id: str | None = None) -> dict:
    """Editor.js Code plugin. BLOCKS.md 스펙상 language 필드는 없음."""
    return _block("code", {"code": source}, id=id)


def _list(items: Iterable[Any], style: str, *, id: str | None = None) -> dict:
    return _block("list", {"style": style, "items": list(items)}, id=id)


def ulist(items: Iterable[Any], *, id: str | None = None) -> dict:
    """Unordered list. items 는 문자열 또는 {content, items?} 객체(NestedList)."""
    return _list(items, "unordered", id=id)


def olist(items: Iterable[Any], *, id: str | None = None) -> dict:
    """Ordered list."""
    return _list(items, "ordered", id=id)


def checklist(items: Iterable[Any], *, id: str | None = None) -> dict:
    """체크박스 목록. items 는 (text, checked) 튜플 또는 {text, checked} dict.
    문자열만 주어지면 checked=False 로 처리한다.
    """
    normalized = []
    for it in items:
        if isinstance(it, dict):
            normalized.append({"text": str(it.get("text", "")), "checked": bool(it.get("checked", False))})
        elif isinstance(it, (tuple, list)) and len(it) == 2:
            normalized.append({"text": str(it[0]), "checked": bool(it[1])})
        else:
            normalized.append({"text": str(it), "checked": False})
    return _block("checklist", {"items": normalized}, id=id)


def quote(text: str, caption: str = "", alignment: str = "left", *, id: str | None = None) -> dict:
    if alignment not in ("left", "center"):
        raise ValueError(f"quote alignment must be 'left' or 'center', got {alignment!r}")
    return _block("quote", {"text": text, "caption": caption, "alignment": alignment}, id=id)


def delimiter(*, id: str | None = None) -> dict:
    return _block("delimiter", {}, id=id)


def table(rows: list[list[str]], with_headings: bool = True, *, id: str | None = None) -> dict:
    """rows 는 2차원 문자열 배열. with_headings=True 면 첫 행이 헤더.

    모든 행의 컬럼 수가 동일해야 한다. 불일치 시 ValueError — Editor.js 가 깨진 표를 렌더하는 것보다
    호출 시점에 명시적 에러를 발생시키는 편이 안전하다(자동 패딩은 데이터 손실 인상을 줄 수 있어 거부).
    """
    if not rows:
        raise ValueError("table rows must be non-empty")
    expected_cols = len(rows[0])
    if expected_cols == 0:
        raise ValueError("table rows must have at least one column")
    content: list[list[str]] = []
    for i, row in enumerate(rows):
        if len(row) != expected_cols:
            raise ValueError(
                f"table row {i} has {len(row)} cell(s) but expected {expected_cols} "
                f"(first row defines column count)"
            )
        content.append([str(cell) for cell in row])
    return _block("table", {"withHeadings": bool(with_headings), "content": content}, id=id)


def image(
    url: str,
    caption: str = "",
    *,
    with_border: bool = False,
    with_background: bool = False,
    stretched: bool = False,
    align_left: bool = False,
    align_right: bool = False,
    size_small: bool = False,
    size_medium: bool = False,
    id: str | None = None,
) -> dict:
    """업로드된 이미지 URL 을 받아 image 블록을 만든다.
    BlogN 의 /app/file/uploadImage 또는 /app/file/fetchUrl 응답 URL 을 그대로 넘긴다.
    """
    return _block(
        "image",
        {
            "file": {"url": url},
            "caption": caption,
            "withBorder": with_border,
            "withBackground": with_background,
            "stretched": stretched,
            "alignLeft": align_left,
            "alignRight": align_right,
            "sizeSmall": size_small,
            "sizeMedium": size_medium,
        },
        id=id,
    )


# ─────────────────────────────────────────────────────────────────────
# embed / attaches — BLOCKS.md §3.10 ~ §3.11
# ─────────────────────────────────────────────────────────────────────

# `@editorjs/embed/dist/embed.mjs` 의 youtube/vimeo 정의를 미러. 새 SPA 의 화이트리스트
# (tools.ts: services.youtube=true, services.vimeo=true) 와 백엔드 CSP frame-src
# (SecurityConfig: youtube.com / youtube-nocookie.com / player.vimeo.com) 과 짝이다.
# 다른 서비스를 추가하려면 본 모듈 / tools.ts / CSP 셋을 동시에 갱신해야 한다.
_EMBED_SERVICES: dict[str, dict[str, Any]] = {
    "youtube": {
        # 라이브러리 본체 정규식보다 관대 — 라이브러리는 paste 흐름에서 동작하지만 본 스킬은
        # 사용자가 짧은 형태(`https://youtu.be/<id>`) 만 줘도 인식되어야 함.
        "regex": __import__("re").compile(
            r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|v/|shorts/))([a-zA-Z0-9_-]+)"
        ),
        "embed_url": "https://www.youtube.com/embed/{id}",
    },
    "vimeo": {
        "regex": __import__("re").compile(r"vimeo\.com/(?:video/)?(\d+)"),
        "embed_url": "https://player.vimeo.com/video/{id}?title=0&byline=0",
    },
}


def _resolve_embed(url: str) -> tuple[str, str]:
    """URL → (service, embed_url) 매칭. 미지원 서비스는 ValueError.

    임의 서비스 자동 추가를 막기 위해 화이트리스트 외에는 에러로 처리한다 (BLOCKS.md §3.10).
    """
    for service, cfg in _EMBED_SERVICES.items():
        m = cfg["regex"].search(url)
        if m:
            return service, cfg["embed_url"].format(id=m.group(1))
    raise ValueError(
        f"embed 는 YouTube · Vimeo URL 만 지원합니다 (입력: {url!r}). "
        "다른 서비스가 필요하면 tools.ts/CSP/본 모듈 셋을 함께 갱신해야 합니다."
    )


def embed(
    source: str,
    caption: str = "",
    *,
    width: int = 580,
    height: int = 320,
    id: str | None = None,
) -> dict:
    """YouTube · Vimeo URL 로 embed 블록 dict 를 만든다.

    `source` URL 에서 자동으로 service 와 embed iframe URL 을 추출한다.
    `width`/`height` 는 라이브러리 기본값과 일치 (580x320). 일부 테마는 CSS 로 덮어쓴다.
    """
    service, embed_url = _resolve_embed(source)
    return _block(
        "embed",
        {
            "service": service,
            "source": source,
            "embed": embed_url,
            "width": int(width),
            "height": int(height),
            "caption": caption,
        },
        id=id,
    )


def attaches(
    *,
    file_id: str,
    file_name: str,
    file_size: int,
    extension: str,
    url: str | None = None,
    title: str = "",
    id: str | None = None,
) -> dict:
    """첨부 파일 블록. 일반적으로 `upload_attachment()` 응답으로 만든다.

    - ``url`` 미지정 시 `/app/file/download/{file_id}` 로 자동 조립 (백엔드 표준 다운로드 경로).
    - ``title`` 은 카드 표시명. 빈 문자열이면 라이브러리가 file_name 을 fallback 으로 표시.
    - ``extension`` 은 소문자, 점(.) 없는 형태로 통일. 차단 확장자(`BLOCKS.md §3.11`)는 ValueError.
    """
    ext = extension.lstrip(".").lower()
    forbidden = {
        "exe", "bat", "sh", "msi", "jar", "apk", "com", "cmd", "scr", "vbs", "ps1", "dll",
        "jsp", "jspx", "asp", "aspx", "php", "phtml", "py", "rb",
        "js", "mjs", "ts", "html", "htm", "svg",
    }
    if ext in forbidden:
        raise ValueError(
            f"attaches: 차단 확장자 .{ext} 는 블록 빌더에서 허용되지 않습니다. "
            "백엔드 CoreFileController 의 BLOCKED_FILE_EXT 와 동일 정책."
        )
    resolved_url = url or f"/app/file/download/{file_id}"
    return _block(
        "attaches",
        {
            "file": {
                "url": resolved_url,
                "name": file_name,
                "size": int(file_size),
                "extension": ext,
                "fileId": file_id,
            },
            "title": title or file_name,
        },
        id=id,
    )


def document(blocks: list[dict], *, time_ms: int | None = None, version: str = EDITORJS_VERSION) -> dict:
    """Editor.js 풀 wrapper. PUT .../contents 의 postContents 값으로 그대로 사용."""
    return {
        "time": int(time_ms if time_ms is not None else time.time() * 1000),
        "version": version,
        "blocks": list(blocks),
    }


# ─────────────────────────────────────────────────────────────────────
# HTTP 헬퍼 — PAT 토큰은 BLOGN_PAT_TOKEN 환경변수에서 읽는다.
# ─────────────────────────────────────────────────────────────────────


class BlognApiError(RuntimeError):
    def __init__(self, status: int, message: str, body: Any = None):
        super().__init__(f"BlogN API {status}: {message}")
        self.status = status
        self.body = body


def _resolve_token(token: str | None) -> str:
    if token:
        return token
    env = os.environ.get("BLOGN_PAT_TOKEN")
    if env:
        return env
    raise BlognApiError(
        0,
        "PAT 토큰을 찾을 수 없습니다. BLOGN_PAT_TOKEN 환경변수를 설정하거나 token= 인자로 전달하세요.",
    )


def _request(
    method: str,
    path: str,
    *,
    body: Any = None,
    token: str | None = None,
    base_url: str = BASE_URL,
    timeout: int = 30,
    retry_5xx: int = 1,
) -> dict:
    """BlogN API 호출 공용 헬퍼.

    - 5xx 응답은 ``retry_5xx`` 회만큼 0.5s backoff 후 재시도 (SKILL.md 의 5xx 처리 정책).
    - 4xx 는 즉시 BlognApiError.
    - 네트워크 예외(URLError, ConnectionResetError) 는 친절 메시지로 감싸 BlognApiError 로 변환.
    - 에러 메시지에 method + url 을 항상 포함하여 디버깅을 돕는다.
    """
    url = base_url.rstrip("/") + path
    label = f"{method} {url}"
    data: bytes | None = None
    headers = {
        "Authorization": f"Bearer {_resolve_token(token)}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    last_err: BlognApiError | None = None
    for attempt in range(retry_5xx + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
                message = parsed.get("message") or raw
            except json.JSONDecodeError:
                parsed = raw
                message = raw
            err = BlognApiError(e.code, f"{label} — {message}", parsed)
            if 500 <= e.code < 600 and attempt < retry_5xx:
                last_err = err
                time.sleep(0.5)
                continue
            raise err from None
        except urllib.error.URLError as e:
            raise BlognApiError(0, f"{label} — BlogN 백엔드 연결 실패: {e.reason}") from None
        except (ConnectionResetError, TimeoutError) as e:
            raise BlognApiError(0, f"{label} — 네트워크 오류: {e}") from None

        if not payload.get("success", False):
            raise BlognApiError(
                200,
                f"{label} — {payload.get('message') or '응답 success=false'}",
                payload,
            )
        return payload

    # 도달 불가 — 안전망
    assert last_err is not None
    raise last_err


def _first(payload: dict) -> dict:
    """data 배열의 첫 항목 반환 (BlogN 응답은 항상 배열로 래핑)."""
    data = payload.get("data") or []
    if not data:
        raise BlognApiError(200, "응답 data 배열이 비어 있습니다.", payload)
    return data[0]


def create_post(
    *,
    blog_id: str,
    title: str,
    clsf_id: str | None = None,
    post_tag: str | None = None,
    post_status: str = "DRAFT",
    extra: dict | None = None,
    token: str | None = None,
) -> dict:
    """POST /api/v1/blog/{blogId}/posts — 메타데이터만 등록. 응답의 첫 data 항목(VO) 반환.

    반환 dict 의 ``postId`` 와 ``lockTimestamp`` 를 이어지는 put_post_contents 에 넘기면 된다.
    """
    body: dict[str, Any] = {"postTitle": title, "postStatus": post_status}
    if clsf_id:
        body["clsfId"] = clsf_id
    if post_tag is not None:
        body["postTag"] = post_tag
    if extra:
        body.update(extra)
    return _first(_request("POST", f"/api/v1/blog/{blog_id}/posts", body=body, token=token))


def get_post(*, blog_id: str, post_id: str, token: str | None = None) -> dict:
    """GET /api/v1/blog/{blogId}/posts/{postId} — 최신 lockTimestamp 확보용."""
    return _first(_request("GET", f"/api/v1/blog/{blog_id}/posts/{post_id}", token=token))


def update_post_meta(
    *,
    blog_id: str,
    post_id: str,
    lock_timestamp: str,
    updates: dict,
    token: str | None = None,
) -> dict:
    """PUT /api/v1/blog/{blogId}/posts/{postId} — 제목/태그/상태 등 메타데이터 갱신.

    `updates` 는 변경할 필드만 (예: {"postStatus": "PUBLISHED"}). lockTimestamp 는 자동 포함.
    """
    body = dict(updates)
    body["lockTimestamp"] = lock_timestamp
    return _first(_request("PUT", f"/api/v1/blog/{blog_id}/posts/{post_id}", body=body, token=token))


def set_post_publish(
    *,
    blog_id: str,
    post_id: str,
    publish_flag: int,
    lock_timestamp: str | None = None,
    token: str | None = None,
) -> dict:
    """PUT /api/v1/blog/{blogId}/posts/{postId}/publish — 발행/발행취소 전용 엔드포인트.

    서버가 POST_STATUS 와 PUBLISH_FLAG 두 컬럼을 원자적으로 함께 갱신한다.
    - publish_flag=1 → POST_STATUS='PUBLISHED', PUBLISH_FLAG=1
    - publish_flag=0 → POST_STATUS='DRAFT',     PUBLISH_FLAG=0
    lock_timestamp 미지정 시 GET 으로 최신값 확보 후 진행.
    """
    if publish_flag not in (0, 1):
        raise ValueError("publish_flag 는 0 또는 1 이어야 합니다.")
    if lock_timestamp is None:
        lock_timestamp = get_post(blog_id=blog_id, post_id=post_id, token=token)["lockTimestamp"]
    body: dict[str, Any] = {"publishFlag": publish_flag, "lockTimestamp": lock_timestamp}
    return _first(_request(
        "PUT", f"/api/v1/blog/{blog_id}/posts/{post_id}/publish",
        body=body, token=token,
    ))


def publish_post(*, blog_id: str, post_id: str, lock_timestamp: str | None = None, token: str | None = None) -> dict:
    """포스트 발행 — set_post_publish(publish_flag=1) 의 별칭."""
    return set_post_publish(blog_id=blog_id, post_id=post_id, publish_flag=1, lock_timestamp=lock_timestamp, token=token)


def unpublish_post(*, blog_id: str, post_id: str, lock_timestamp: str | None = None, token: str | None = None) -> dict:
    """포스트 발행 취소 — set_post_publish(publish_flag=0) 의 별칭."""
    return set_post_publish(blog_id=blog_id, post_id=post_id, publish_flag=0, lock_timestamp=lock_timestamp, token=token)


def put_post_contents(
    *,
    blog_id: str,
    post_id: str,
    lock_timestamp: str,
    blocks: list[dict] | None = None,
    post_contents: dict | None = None,
    post_status: str | None = None,
    token: str | None = None,
) -> dict:
    """PUT /api/v1/blog/{blogId}/posts/{postId}/contents — 본문 일괄 저장.

    - ``blocks`` 만 넘기면 document() wrapper 로 자동 감싼다.
    - 이미 wrapper(time/version/blocks) 가 있는 dict 는 ``post_contents`` 로 전달.
    - 둘 중 하나만 지정. ``post_status`` 미지정 시 서버 기본(SAVED).
    """
    if (blocks is None) == (post_contents is None):
        raise ValueError("blocks 또는 post_contents 중 정확히 하나를 전달해야 합니다.")
    payload_contents = post_contents if post_contents is not None else document(blocks)  # type: ignore[arg-type]
    body: dict[str, Any] = {
        "lockTimestamp": lock_timestamp,
        "postContents": payload_contents,
    }
    if post_status is not None:
        body["postStatus"] = post_status
    return _first(_request("PUT", f"/api/v1/blog/{blog_id}/posts/{post_id}/contents", body=body, token=token))


# ─────────────────────────────────────────────────────────────────────
# 증분 블록 편집 (block-level edit) — .../{postId}/blocks*
#
# put_post_contents 가 본문 전체 교체(전 블록 삭제 후 재INSERT, lockTimestamp 필수,
# 위키링크 전체 재계산, POST_CONTENTS 스냅샷 즉시 갱신)인 반면, 아래 헬퍼는 블록 1개
# 단위로 증분 편집한다. lockTimestamp 를 쓰지 않는다:
#   - add_block / move_block : 서버가 postId 단위 락으로 BLOCK_INDEX 원자성을 보장
#   - update_block           : versionNo(블록별 VERSION_NO) 낙관적 동시성 — 불일치 시 409
# 증분 편집은 BLOG_POST_BLOCK 행만 바꾸며 POST_CONTENTS/POST_SEARCH 스냅샷은 자동 갱신되지
# 않는다(add/update 는 블록별 위키링크만 동기화, delete 는 이후 인덱스를 당김). 편집을 마치면
# sync_contents(...) 를 한 번 호출해 스냅샷 + 검색 인덱스를 플러시한다.
# ─────────────────────────────────────────────────────────────────────


def add_block(
    *,
    blog_id: str,
    post_id: str,
    block: dict,
    index: int,
    token: str | None = None,
) -> dict:
    """POST /api/v1/blog/{blogId}/posts/{postId}/blocks — 블록 1개를 index 위치에 삽입.

    ``block`` 은 paragraph()/header()/table()/... 빌더가 반환한 dict({id,type,data}).
    blockId 는 block["id"] 를 그대로 보내며, 비어 있으면 서버가 자동 생성한다.
    lockTimestamp 불필요. 반환: 저장된 블록 VO(data[0]).
    """
    body: dict[str, Any] = {"type": block["type"], "data": block.get("data", {}), "index": index}
    if block.get("id"):
        body["blockId"] = block["id"]
    return _first(_request(
        "POST", f"/api/v1/blog/{blog_id}/posts/{post_id}/blocks", body=body, token=token,
    ))


def update_block(
    *,
    blog_id: str,
    post_id: str,
    block_id: str,
    block: dict,
    version_no: int | None = None,
    token: str | None = None,
) -> dict:
    """PUT /api/v1/blog/{blogId}/posts/{postId}/blocks/{blockId} — 블록 1개 내용 교체.

    ``block`` 은 빌더가 반환한 dict(type/data 사용). ``version_no`` 를 주면 블록별 VERSION_NO
    낙관적 동시성 검증(불일치 시 409). lockTimestamp 불필요. 반환: 수정된 블록 VO(data[0]).
    """
    body: dict[str, Any] = {"type": block["type"], "data": block.get("data", {})}
    if version_no is not None:
        body["versionNo"] = version_no
    return _first(_request(
        "PUT", f"/api/v1/blog/{blog_id}/posts/{post_id}/blocks/{block_id}",
        body=body, token=token,
    ))


def delete_block(*, blog_id: str, post_id: str, block_id: str, token: str | None = None) -> dict:
    """DELETE /api/v1/blog/{blogId}/posts/{postId}/blocks/{blockId} — 블록 1개 삭제.

    삭제 후 이후 블록 인덱스가 1씩 당겨진다(공백 제거). body 불필요. 반환: 응답 payload.
    """
    return _request(
        "DELETE", f"/api/v1/blog/{blog_id}/posts/{post_id}/blocks/{block_id}", token=token,
    )


def move_block(
    *,
    blog_id: str,
    post_id: str,
    block_id: str,
    from_index: int,
    to_index: int,
    token: str | None = None,
) -> dict:
    """PUT /api/v1/blog/{blogId}/posts/{postId}/blocks/{blockId}/move — 블록 위치 이동.

    from_index/to_index 둘 다 필수이며 서로 달라야 한다(같으면 400). lockTimestamp 불필요.
    반환: 응답 payload.
    """
    body: dict[str, Any] = {"fromIndex": from_index, "toIndex": to_index}
    return _request(
        "PUT", f"/api/v1/blog/{blog_id}/posts/{post_id}/blocks/{block_id}/move",
        body=body, token=token,
    )


def sync_contents(*, blog_id: str, post_id: str, token: str | None = None) -> dict:
    """POST /api/v1/blog/{blogId}/posts/{postId}/contents/sync — 블록 → 스냅샷 동기화.

    BLOG_POST_BLOCK 전체를 Editor.js JSON 으로 직렬화해 POST_CONTENTS 에 쓰고, 평문 추출 →
    형태소 토큰화 후 POST_SEARCH 에도 반영한다. 증분 블록 편집(add/update/delete/move) 을
    마친 뒤 한 번 호출한다. lockTimestamp 불필요. 반환: 갱신된 포스트 VO(postContents 포함).
    """
    return _first(_request(
        "POST", f"/api/v1/blog/{blog_id}/posts/{post_id}/contents/sync", token=token,
    ))


# ─────────────────────────────────────────────────────────────────────
# 파일 업로드 (image / thumb / attach) — BLOCKS.md §10
#
# 진입점은 `POST /api/v1/files/upload` (SysFileApiController — 외부 클라이언트/스킬·MCP 전용).
# PAT Bearer 인증을 그대로 사용한다 (다른 /api/v1 호출과 동일). `file` scope 가 capability
# gate 이며, repository=BLOG_POST 는 추가로 `blog` scope 가 필요하다. 따라서 블로그 본문
# 업로드용 PAT 은 반드시 **`file` + `blog` 두 scope 를 모두 보유**해야 한다.
#
# 구 `/core/file/upload` CSRF flow 를 대체한다 — XSRF prefetch·세션 쿠키 불필요.
# ─────────────────────────────────────────────────────────────────────

import mimetypes
import uuid as _uuid
from pathlib import Path


def _encode_multipart(fields: dict[str, str], file_field: str, file_path: Path, file_mime: str) -> tuple[bytes, str]:
    """간단한 multipart/form-data 인코더. 외부 의존성 없이 동작."""
    boundary = "----blog-editor-" + _uuid.uuid4().hex
    crlf = b"\r\n"
    body = bytearray()
    for name, value in fields.items():
        body += f"--{boundary}{chr(13)}{chr(10)}".encode("utf-8")
        body += f'Content-Disposition: form-data; name="{name}"{chr(13)}{chr(10)}{chr(13)}{chr(10)}'.encode("utf-8")
        body += value.encode("utf-8") + crlf
    body += f"--{boundary}{chr(13)}{chr(10)}".encode("utf-8")
    body += (
        f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"{chr(13)}{chr(10)}'
        f"Content-Type: {file_mime}{chr(13)}{chr(10)}{chr(13)}{chr(10)}"
    ).encode("utf-8")
    body += file_path.read_bytes()
    body += crlf
    body += f"--{boundary}--{chr(13)}{chr(10)}".encode("utf-8")
    return bytes(body), boundary


def _upload(
    file_path: str | Path,
    *,
    upload_type: str,
    binding_key: str | None,
    repository: str,
    token: str | None,
    base_url: str,
    timeout: int,
) -> dict:
    """`POST /api/v1/files/upload` 로 단일 파일 업로드 후 SysFileVO dict 반환.

    PAT Bearer 인증. multipart/form-data 로 `repository`/`type`/`bindingKey`/`file` 전송.
    """
    path = Path(file_path)
    if not path.is_file():
        raise BlognApiError(0, f"업로드할 파일이 존재하지 않습니다: {file_path}")

    # 사이즈 사전 검증 — 백엔드 정책 미러. 클라이언트에서 미리 거절하면 라운드트립 절약.
    size = path.stat().st_size
    if size == 0:
        raise BlognApiError(0, "FILE_REQUIRED — 빈 파일은 업로드할 수 없습니다.")
    if upload_type in ("image", "thumb") and size > 10 * 1024 * 1024:
        raise BlognApiError(0, "FILE_TOO_LARGE — 이미지는 10MB 까지 업로드할 수 있습니다.")
    if upload_type == "attach" and size > 20 * 1024 * 1024:
        raise BlognApiError(0, "FILE_TOO_LARGE — 첨부 파일은 20MB 까지 업로드할 수 있습니다.")

    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    fields = {"repository": repository, "type": upload_type}
    if binding_key:
        fields["bindingKey"] = binding_key
    body, boundary = _encode_multipart(fields, "file", path, mime)

    upload_url = base_url.rstrip("/") + "/api/v1/files/upload"
    req = urllib.request.Request(
        upload_url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {_resolve_token(token)}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        message = parsed.get("message") if isinstance(parsed, dict) else raw
        raise BlognApiError(e.code, f"POST /api/v1/files/upload — {message}", parsed) from None
    except urllib.error.URLError as e:
        raise BlognApiError(0, f"POST /api/v1/files/upload — 백엔드 연결 실패: {e.reason}") from None

    if not payload.get("success", False):
        raise BlognApiError(
            200,
            f"POST /api/v1/files/upload — {payload.get('message') or payload.get('errorCode') or '응답 success=false'}",
            payload,
        )
    data = payload.get("data") or []
    if not data:
        raise BlognApiError(200, "/api/v1/files/upload 응답 data 가 비어 있습니다.", payload)
    return data[0]


def upload_image(
    file_path: str | Path,
    *,
    post_id: str | None = None,
    repository: str = "BLOG_POST",
    caption: str = "",
    token: str | None = None,
    base_url: str = BASE_URL,
    timeout: int = 60,
) -> dict:
    """이미지 업로드 → image 블록 dict 반환.

    응답의 fileId 를 사용해 `file.url = /app/file/view/{fileId}` 로 조립한다.
    `post_id` 가 있으면 `bindingKey`(SYS_FILE.BINDING_KEY) 에 매핑되어 포스트 삭제 cascade ·
    권한 가드 대상이 된다. PAT 은 `file` + `blog`(repository=BLOG_POST) scope 가 모두 필요.
    """
    sys_file = _upload(
        file_path,
        upload_type="image",
        binding_key=post_id,
        repository=repository,
        token=token,
        base_url=base_url,
        timeout=timeout,
    )
    file_id = sys_file["fileId"]
    return image(f"/app/file/view/{file_id}", caption=caption)


def upload_attachment(
    file_path: str | Path,
    *,
    post_id: str | None = None,
    repository: str = "BLOG_POST",
    title: str = "",
    token: str | None = None,
    base_url: str = BASE_URL,
    timeout: int = 60,
) -> dict:
    """첨부 파일 업로드 → attaches 블록 dict 반환.

    응답의 fileId · fileName · fileSize · fileExt 를 attaches 블록 file.* 필드에 그대로 매핑.
    `title` 미지정 시 fileName 을 fallback. PAT 은 `file` + `blog` scope 가 모두 필요.
    """
    sys_file = _upload(
        file_path,
        upload_type="attach",
        binding_key=post_id,
        repository=repository,
        token=token,
        base_url=base_url,
        timeout=timeout,
    )
    return attaches(
        file_id=sys_file["fileId"],
        file_name=sys_file["fileName"],
        file_size=int(sys_file.get("fileSize", 0) or 0),
        extension=sys_file.get("fileExt") or Path(sys_file.get("fileName", "")).suffix.lstrip("."),
        title=title,
    )


def get_file(*, file_id: str, token: str | None = None, base_url: str = BASE_URL, timeout: int = 30) -> dict:
    """GET /api/v1/files/{fileId} — 파일 메타 조회 (소유자 본인만). SysFileVO dict 반환.

    PAT `file` scope 필요. 소유자가 아니면 403(FILE_FORBIDDEN), 없으면 404(FILE_NOT_FOUND).
    """
    return _first(_request("GET", f"/api/v1/files/{file_id}", token=token, base_url=base_url, timeout=timeout))


def delete_file(*, file_id: str, token: str | None = None, base_url: str = BASE_URL, timeout: int = 30) -> dict:
    """DELETE /api/v1/files/{fileId} — 파일 삭제 (소유자 본인만). 응답 envelope 그대로 반환.

    PAT `file` scope 필요. 본문에 참조 중인 파일이라도 즉시 삭제되므로 호출 전 사용자 확인 권장.
    """
    return _request("DELETE", f"/api/v1/files/{file_id}", token=token, base_url=base_url, timeout=timeout)


# ─────────────────────────────────────────────────────────────────────
# Markdown ↔ Editor.js 블록 변환 — BLOCKS.md §6
#
# 외부 의존성 없이 표준 라이브러리만 사용. 풀 CommonMark 가 아니라 BlogN 본문에서 자주
# 쓰이는 8개 블록 + 이미지 + embed + attaches 만 다룬다. round-trip 시 image tunes,
# embed width/height, attaches title 같은 비-마크다운 정보는 손실되므로 markdown 은
# 어디까지나 export/import 보조 경로로 사용한다.
# ─────────────────────────────────────────────────────────────────────

import re as _re

_INLINE_PATTERNS = [
    # (markdown, html_open, html_close, capture_re, render_back)
    # 우선순위 — 더 긴/specific 토큰부터.
    (_re.compile(r"\*\*(.+?)\*\*"), r"<b>\1</b>"),
    (_re.compile(r"__(.+?)__"), r"<b>\1</b>"),
    (_re.compile(r"(?<!\*)\*(?!\s)([^\*\n]+?)\*(?!\*)"), r"<i>\1</i>"),
    (_re.compile(r"(?<!_)_(?!\s)([^_\n]+?)_(?!_)"), r"<i>\1</i>"),
    (_re.compile(r"==(.+?)=="), r'<mark class="cdx-marker">\1</mark>'),
    (_re.compile(r"`([^`\n]+?)`"), r'<code class="inline-code">\1</code>'),
    (_re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), r'<a href="\2">\1</a>'),
]


def _inline_md_to_html(text: str) -> str:
    """문장 안의 markdown 인라인 토큰을 Editor.js 가 저장하는 HTML 로 변환."""
    out = text
    for pattern, repl in _INLINE_PATTERNS:
        out = pattern.sub(repl, out)
    return out


_HTML_TO_MD: list[tuple[_re.Pattern[str], str]] = [
    (_re.compile(r"<b>(.+?)</b>", _re.S), r"**\1**"),
    (_re.compile(r"<strong>(.+?)</strong>", _re.S), r"**\1**"),
    (_re.compile(r"<i>(.+?)</i>", _re.S), r"*\1*"),
    (_re.compile(r"<em>(.+?)</em>", _re.S), r"*\1*"),
    (_re.compile(r'<mark[^>]*>(.+?)</mark>', _re.S), r"==\1=="),
    (_re.compile(r'<code[^>]*class="inline-code"[^>]*>(.+?)</code>', _re.S), r"`\1`"),
    (_re.compile(r"<code>(.+?)</code>", _re.S), r"`\1`"),
    (_re.compile(r'<a[^>]*href="([^"]+)"[^>]*>(.+?)</a>', _re.S), r"[\2](\1)"),
]


def _inline_html_to_md(text: str) -> str:
    """텍스트 블록 안의 Editor.js HTML 을 markdown 토큰으로 역변환.

    `<u>` 는 markdown 표기가 없어 그대로 유지한다 (사용자가 수동으로 처리하도록).
    """
    out = text
    for pattern, repl in _HTML_TO_MD:
        out = pattern.sub(repl, out)
    return out


def _is_embed_url(line: str) -> bool:
    try:
        _resolve_embed(line)
        return True
    except ValueError:
        return False


_ATTACH_RE = _re.compile(
    r'^\[\s*📎\s*(?P<name>[^\]]+?)\]\((?P<url>\S+?)(?:\s+"(?P<meta>[^"]*)")?\)\s*$'
)
_IMAGE_RE = _re.compile(r'^!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)\)\s*$')
_HEADER_RE = _re.compile(r'^(#{1,6})\s+(.*)$')
_ULI_RE = _re.compile(r'^[-*]\s+(.*)$')
_CHECK_RE = _re.compile(r'^[-*]\s+\[( |x|X)\]\s+(.*)$')
_OLI_RE = _re.compile(r'^\d+\.\s+(.*)$')
_QUOTE_RE = _re.compile(r'^>\s?(.*)$')
_HR_RE = _re.compile(r'^(---|\*\*\*|___)\s*$')
_TABLE_SEP_RE = _re.compile(r'^\|?(?:\s*:?-+:?\s*\|)+\s*$')
_FENCE_RE = _re.compile(r'^```([^\n`]*)$')


def _table_row(line: str) -> list[str] | None:
    """`| a | b |` 형태의 줄을 셀 배열로. 표 줄이 아니면 None."""
    if not line.lstrip().startswith("|"):
        return None
    inner = line.strip()
    # 시작/끝 파이프 제거
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def markdown_to_document(md: str, *, time_ms: int | None = None) -> dict:
    """마크다운 문자열 → Editor.js document(wrapper) dict.

    `put_post_contents(post_contents=markdown_to_document(md), ...)` 형태로 그대로 본문 PUT 가능.
    """
    lines = md.splitlines()
    blocks: list[dict] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # 빈 줄 — 블록 분리
        if not stripped:
            i += 1
            continue

        # 코드 펜스
        fence = _FENCE_RE.match(stripped)
        if fence:
            i += 1
            buf: list[str] = []
            while i < n and not _FENCE_RE.match(lines[i].strip()):
                buf.append(lines[i])
                i += 1
            if i < n:
                i += 1  # 종료 fence 소비
            blocks.append(code("\n".join(buf)))
            continue

        # 헤더
        m = _HEADER_RE.match(stripped)
        if m:
            level = len(m.group(1))
            blocks.append(header(_inline_md_to_html(m.group(2).strip()), level=level))
            i += 1
            continue

        # 구분선
        if _HR_RE.match(stripped):
            blocks.append(delimiter())
            i += 1
            continue

        # 이미지 (단독 라인)
        m = _IMAGE_RE.match(stripped)
        if m:
            blocks.append(image(m.group("url"), caption=m.group("alt")))
            i += 1
            continue

        # 첨부 파일 (단독 라인) — title 의 메타 어트리뷰트로 size,ext,fileId 전달
        m = _ATTACH_RE.match(stripped)
        if m:
            meta = m.group("meta") or ""
            size_s, _, rest = meta.partition(",")
            ext_s, _, file_id_s = rest.partition(",")
            try:
                size_val = int(size_s.strip()) if size_s.strip() else 0
            except ValueError:
                size_val = 0
            ext_val = ext_s.strip() or Path(m.group("name")).suffix.lstrip(".")
            fid_val = file_id_s.strip() or m.group("url").rsplit("/", 1)[-1]
            blocks.append(
                attaches(
                    file_id=fid_val,
                    file_name=m.group("name").strip(),
                    file_size=size_val,
                    extension=ext_val,
                    url=m.group("url"),
                )
            )
            i += 1
            continue

        # YouTube/Vimeo 단독 URL → embed
        if _is_embed_url(stripped):
            blocks.append(embed(stripped))
            i += 1
            continue

        # 체크리스트 (연속 - [ ] / - [x])
        if _CHECK_RE.match(stripped):
            items: list[tuple[str, bool]] = []
            while i < n:
                cm = _CHECK_RE.match(lines[i].strip())
                if not cm:
                    break
                items.append((_inline_md_to_html(cm.group(2).strip()), cm.group(1).lower() == "x"))
                i += 1
            blocks.append(checklist(items))
            continue

        # 비순서 리스트
        if _ULI_RE.match(stripped) and not _CHECK_RE.match(stripped):
            items_u: list[str] = []
            while i < n:
                um = _ULI_RE.match(lines[i].strip())
                if not um or _CHECK_RE.match(lines[i].strip()):
                    break
                items_u.append(_inline_md_to_html(um.group(1).strip()))
                i += 1
            blocks.append(ulist(items_u))
            continue

        # 순서 리스트
        if _OLI_RE.match(stripped):
            items_o: list[str] = []
            while i < n:
                om = _OLI_RE.match(lines[i].strip())
                if not om:
                    break
                items_o.append(_inline_md_to_html(om.group(1).strip()))
                i += 1
            blocks.append(olist(items_o))
            continue

        # 인용 (연속 > 줄)
        if _QUOTE_RE.match(stripped):
            buf_q: list[str] = []
            caption_q = ""
            while i < n:
                qm = _QUOTE_RE.match(lines[i].strip())
                if not qm:
                    break
                content = qm.group(1).strip()
                if content.startswith("— "):
                    caption_q = content[2:].strip()
                else:
                    buf_q.append(content)
                i += 1
            blocks.append(quote(_inline_md_to_html(" ".join(buf_q).strip()), caption=caption_q))
            continue

        # 표 (`|...|` + 구분줄)
        row = _table_row(line)
        if row is not None and (i + 1) < n and _TABLE_SEP_RE.match(lines[i + 1].strip()):
            with_headings = True
            rows_t: list[list[str]] = [row]
            i += 2  # 헤더 + 구분줄 소비
            while i < n:
                nxt = _table_row(lines[i])
                if nxt is None:
                    break
                rows_t.append(nxt)
                i += 1
            blocks.append(table(rows_t, with_headings=with_headings))
            continue

        # 그 외 — 한 라인 = paragraph (연속 라인은 공백으로 join)
        buf_p = [stripped]
        i += 1
        while i < n and lines[i].strip() and not _is_special_line(lines[i].strip()):
            buf_p.append(lines[i].strip())
            i += 1
        blocks.append(paragraph(_inline_md_to_html(" ".join(buf_p))))

    return document(blocks, time_ms=time_ms)


def _is_special_line(s: str) -> bool:
    """paragraph 안에 끌어들이지 말아야 할 라인 패턴 — 다음 블록의 시작을 알리는 토큰."""
    return bool(
        _HEADER_RE.match(s)
        or _HR_RE.match(s)
        or _IMAGE_RE.match(s)
        or _ATTACH_RE.match(s)
        or _FENCE_RE.match(s)
        or _ULI_RE.match(s)
        or _OLI_RE.match(s)
        or _CHECK_RE.match(s)
        or _QUOTE_RE.match(s)
        or _is_embed_url(s)
        or (s.startswith("|") and "|" in s[1:])
    )


def _block_to_markdown(b: dict) -> str:
    """단일 블록 dict → markdown 문자열 (블록 간 빈 줄은 호출 측에서 처리)."""
    btype = b.get("type")
    data = b.get("data") or {}

    if btype == "header":
        level = max(1, min(6, int(data.get("level", 2))))
        return f"{'#' * level} {_inline_html_to_md(data.get('text', ''))}"

    if btype == "paragraph":
        return _inline_html_to_md(data.get("text", ""))

    if btype == "list":
        style = data.get("style", "unordered")
        items = data.get("items", [])

        def render_items(it: list[Any], depth: int) -> list[str]:
            out: list[str] = []
            for idx, entry in enumerate(it, start=1):
                if isinstance(entry, dict):
                    content = entry.get("content", "")
                    prefix = "- " if style == "unordered" else f"{idx}. "
                    out.append("  " * depth + prefix + _inline_html_to_md(str(content)))
                    children = entry.get("items") or []
                    if children:
                        out.extend(render_items(children, depth + 1))
                else:
                    prefix = "- " if style == "unordered" else f"{idx}. "
                    out.append("  " * depth + prefix + _inline_html_to_md(str(entry)))
            return out

        return "\n".join(render_items(items, 0))

    if btype == "checklist":
        items = data.get("items", [])
        return "\n".join(
            f"- [{'x' if it.get('checked') else ' '}] {_inline_html_to_md(it.get('text', ''))}"
            for it in items
        )

    if btype == "code":
        return f"```\n{data.get('code', '')}\n```"

    if btype == "quote":
        text = _inline_html_to_md(data.get("text", ""))
        body = "\n".join(f"> {line}" for line in text.splitlines() or [""])
        caption = (data.get("caption") or "").strip()
        return body + (f"\n> — {caption}" if caption else "")

    if btype == "delimiter":
        return "---"

    if btype == "table":
        content = data.get("content") or []
        if not content:
            return ""
        with_headings = bool(data.get("withHeadings", False))
        rows = ["| " + " | ".join(r) + " |" for r in content]
        if with_headings and len(rows) > 0:
            sep = "|" + "|".join(["---"] * len(content[0])) + "|"
            rows.insert(1, sep)
        return "\n".join(rows)

    if btype == "image":
        file = data.get("file") or {}
        url = file.get("url", "")
        caption = data.get("caption", "") or ""
        return f"![{caption}]({url})"

    if btype == "embed":
        return data.get("source", "")

    if btype == "attaches":
        file = data.get("file") or {}
        url = file.get("url", "")
        name = file.get("name", "")
        size = file.get("size", 0)
        ext = file.get("extension", "")
        fid = file.get("fileId", "")
        meta = f'"{size},{ext},{fid}"'
        return f"[📎 {name}]({url} {meta})"

    # 미지원 타입은 데이터 손실 방지 차원에서 paragraph 처럼 텍스트만 노출.
    return _inline_html_to_md(str(data))


def document_to_markdown(doc: dict) -> str:
    """Editor.js document(wrapper) → markdown 문자열.

    블록 간 항상 빈 줄로 분리. round-trip 시 손실 항목은 BLOCKS.md §6.2 의 경고 박스 참조.
    """
    blocks = doc.get("blocks") if isinstance(doc, dict) else None
    if not isinstance(blocks, list):
        raise ValueError("document_to_markdown: document.blocks 배열이 없습니다.")
    parts = [_block_to_markdown(b) for b in blocks]
    # 빈 결과는 제거하지 않고 그대로 — 사용자가 빈 블록의 위치를 잃지 않도록.
    return "\n\n".join(parts).rstrip() + ("\n" if parts else "")


__all__ = [
    "BASE_URL",
    "EDITORJS_VERSION",
    "BlognApiError",
    "random_block_id",
    "paragraph",
    "header",
    "code",
    "ulist",
    "olist",
    "checklist",
    "quote",
    "delimiter",
    "table",
    "image",
    "embed",
    "attaches",
    "document",
    "create_post",
    "get_post",
    "update_post_meta",
    "set_post_publish",
    "publish_post",
    "unpublish_post",
    "put_post_contents",
    "add_block",
    "update_block",
    "delete_block",
    "move_block",
    "sync_contents",
    "upload_image",
    "upload_attachment",
    "get_file",
    "delete_file",
    "markdown_to_document",
    "document_to_markdown",
]


if __name__ == "__main__":
    # 스모크 테스트 — 네트워크 호출 없이 빌더와 md↔blocks 변환만 확인.
    demo = document(
        [
            header("Demo"),
            paragraph("Hello <b>BlogN</b>."),
            code("print('hi')"),
            ulist(["A", "B"]),
            olist(["1st", "2nd"]),
            checklist([("done", True), ("todo", False)]),
            quote("말씀", caption="누군가"),
            delimiter(),
            table([["k", "v"], ["a", "1"]]),
            image("/uploaded/x.png", caption="cap"),
            embed("https://www.youtube.com/watch?v=dQw4w9WgXcQ", caption="rickroll"),
            attaches(
                file_id="F0001234",
                file_name="release_notes.pdf",
                file_size=245760,
                extension="pdf",
                title="릴리스 노트",
            ),
        ]
    )
    print("=== document JSON ===")
    print(json.dumps(demo, ensure_ascii=False, indent=2))

    print("\n=== document → markdown ===")
    md = document_to_markdown(demo)
    print(md)

    print("=== markdown → document → markdown (round-trip) ===")
    print(document_to_markdown(markdown_to_document(md)))
