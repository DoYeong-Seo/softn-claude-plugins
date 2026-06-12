---
name: blog-editor
description: BlogN 블로그/포스트 관리 REST API(`api.v1.controller.blog`)를 자연어로 호출하여 블로그 조회·포스트 CRUD·본문 블록 일괄 저장·증분 편집·분류·댓글·좋아요를 처리하고, Editor.js 블록 JSON을 생성/검증/저장합니다. 11개 블록 타입(paragraph/header/list/checklist/code/quote/delimiter/table/image/embed/attaches), 이미지·첨부 파일 업로드(`POST /api/v1/files/upload`, PAT `file`+`blog` scope), YouTube·Vimeo 임베드, Markdown 양방향 변환(`markdown_to_document` / `document_to_markdown`)을 지원합니다. PAT(Personal Access Token) 인증 사용. 블록 본문은 Editor.js 표준 JSON 구조로 다루며 `PUT .../posts/{postId}/contents` 로 일괄 교체하거나, `POST/PUT/DELETE .../posts/{postId}/blocks*` 로 블록 1개 단위 증분 편집 후 `POST .../posts/{postId}/contents/sync` 로 스냅샷을 동기화한다.
allowed-tools: Read, Bash, Write, Grep
---

# Blog Editor

BlogN 프로젝트의 블로그·포스트 백엔드(`api.v1.controller.blog.*`)를 자연어 명령으로 조작하는 스킬입니다.
포스트 본문은 Editor.js 블록 구조로 관리되며, 본 스킬은 그 JSON을 생성·검증·전송합니다.

## 핵심 원칙 — 절대 위반 금지

1. **읽기 외 작업은 모두 PAT(Personal Access Token) `blog` 스코프로 호출한다.**
   - 토큰은 우선순위 따라 환경변수 → 메모리/저장소 → 대화 입력 순으로 탐색 (자세히는 [환경 설정](#환경-설정) 참조).
   - 토큰 누락/만료 시 401. 사용자에게 PAT 재발급/재입력 안내 후 작업 중단.
   - **토큰 값은 절대 응답·로그·예시 명령어에 평문으로 노출하지 않는다.** 마스킹(`softn_pat_...xxxx`) 필수.
2. **삭제(DELETE) 호출은 반드시 사용자 확인 후 실행한다.**
   - 포스트 삭제는 **두 단계로 분리**되어 있다:
     - `DELETE /posts/{postId}` → **소프트 삭제(휴지통 이동)**. 자식 테이블 보존, 복원 가능.
     - `DELETE /posts/{postId}/permanent` → **영구 삭제(cascade hard delete)**. 블록·댓글·좋아요·편집자 전부 삭제, **복구 불가**.
   - 자연어에 "삭제"·"제거"·"지워"만 있으면 기본적으로 **소프트 삭제(휴지통 이동)** 으로 처리하고, "휴지통에 들어갑니다. 복원 가능합니다." 안내.
   - 자연어에 "영구"·"완전히"·"복구 불가"·"휴지통 비워"가 명시되면 영구 삭제 의도. 그 경우 한 번 더 강하게 확인 ("복구할 수 없습니다. 정말 진행하시겠습니까?").
   - 영구 삭제는 휴지통 상태(`POST_STATUS='DELETED'`) 포스트에만 허용 — 일반 포스트에 곧바로 호출하면 400.
3. **수정(PUT) 호출은 변경 요약을 먼저 보여주고 진행한다.**
   - 단순 제목/태그 변경은 즉시 가능. 상태 전환(`DRAFT ↔ PUBLISHED`)은 발행 효과를 알리고 확인.
   - **발행/발행취소는 전용 엔드포인트만 사용한다**: `PUT /api/v1/blog/{blogId}/posts/{postId}/publish` body: `{publishFlag: 0|1, lockTimestamp}`. 서버가 `POST_STATUS` 와 `PUBLISH_FLAG` 두 컬럼을 원자적으로 동시 갱신한다(`publishFlag=1` → POST_STATUS='PUBLISHED', `publishFlag=0` → POST_STATUS='DRAFT').
   - **메타 PUT(`/posts/{postId}`)으로는 발행 불가**: `BlogPostGeneratedDAO.updateSettings` SQL 에 `POST_STATUS`/`PUBLISH_FLAG` 컬럼이 빠져 있어 보내도 무시된다. 발행은 반드시 `/publish` 사용.
   - 본문 PUT(`/contents`)의 `postStatus: "PUBLISHED"` 만으로는 `PUBLISH_FLAG` 가 갱신되지 않는다. 본문 저장과 동시에 발행하려면 본문 PUT 직후 `PUT /publish` 를 별도 호출하거나, `block_builder.publish_post(...)` 헬퍼를 사용한다.
4. **블록 JSON은 [BLOCKS.md](BLOCKS.md) 스펙을 엄격히 따른다.**
   - 비표준 type 임의 생성 금지. 알 수 없는 type 요청 시 사용자에게 paragraph/code 등 대체안 확인.
5. **메타데이터 vs 본문 — 두 개의 PUT을 구분한다**
   - 메타데이터(제목/분류/태그/상태/노출/복사/공유): `PUT /api/v1/blog/{blogId}/posts/{postId}` — `postContents` 미수신.
   - 본문 블록 일괄 갱신: `PUT /api/v1/blog/{blogId}/posts/{postId}/contents` — Editor.js 풀 JSON(`time`/`version`/`blocks[]`)을 받아 `BLOG_POST_BLOCK` 행을 모두 삭제 후 재INSERT, `POST_CONTENTS` 컬럼도 동기화.
   - 본문 블록 증분 편집: `POST/PUT/DELETE .../{postId}/blocks*` — 블록 1개 단위 추가/수정/삭제/이동. **lockTimestamp 미사용**(add/move=서버 postId 락, modify=`versionNo`). 편집 후 **`POST .../{postId}/contents/sync`** 로 스냅샷 갱신 필요. 자세히는 [증분 블록 편집](#증분-블록-편집--blocks--contentssync).
   - 메타 PUT·본문 PUT은 `lockTimestamp` 필수, 충돌 시 409. 본문 PUT/블록 편집 모두 편집 권한(`BlogPostEditUserService.isAuthorized`) 보유자만 호출 가능 (403).

## 환경 설정

| 항목 | 값 |
|------|-----|
| Base URL | `https://back.softn.kr` (하드코딩) |
| 인증 헤더 | `Authorization: Bearer ${BLOGN_PAT_TOKEN}` |
| 토큰 prefix | `softn_pat_` |
| 필수 scope | `blog` (블로그·포스트 전반). **파일 업로드(`/api/v1/files/upload`)는 `file` scope 추가 필요** — repository=BLOG_POST 는 `file` + `blog` 두 scope 모두 보유해야 한다. |

토큰은 **다음 우선순위로 탐색**한다 — 환경마다 가용 자원이 다르므로 한쪽이 없다고 즉시 중단하지 말 것:

### 토큰 탐색 우선순위

1. **환경변수 `BLOGN_PAT_TOKEN`** — Claude Code(CLI) / 로컬 셸 환경의 기본 경로.
2. **메모리 / 영구 저장소** — claude.ai 같이 환경변수가 없는 환경의 fallback. 다음 위치를 차례로 확인:
   - 어시스턴트 자체 메모리(저장된 사실/사용자 프로필) 중 `BlogN PAT`, `softn_pat_` prefix를 가진 항목.
   - `~/.claude/skills/blog-editor/secrets.json` 또는 `<현재 작업 디렉토리>/.claude/skills/blog-editor/secrets.json` — 파일시스템 접근이 허용된 환경에서만. 형식: `{ "patToken": "softn_pat_..." }`. **`.gitignore`에 반드시 포함**.
   - **현재 대화에서 사용자가 직접 알려준 값** (1회용, 대화 종료 시 휘발).
3. 위 모두 없으면 — 사용자에게 한 번 묻고, **저장 방식을 선택**하게 한다 (아래 절차 참조).

### claude.ai 환경에서 사용하는 절차

claude.ai에는 환경변수가 없다. 사용자가 첫 호출에서 본 스킬을 사용할 때 다음 절차를 따른다:

1. **메모리 확인** — 이미 메모리에 BlogN PAT(`softn_pat_` 시작)이 저장되어 있으면 그것을 사용한다. 사용자에게 "저장된 PAT을 사용합니다" 한 줄 안내.
2. **없으면 사용자에게 요청**:
   ```
   BlogN PAT 토큰이 필요합니다.
   - 발급: https://back.softn.kr → 마이페이지 → PAT 발급 (scope에 'blog' 포함, 파일 업로드도 쓸 거면 'file' 도 함께 체크)
   - 형식: softn_pat_xxxxxxxx...
   토큰을 알려주시겠어요? (이번 대화에서만 쓸지, 다음 대화에서도 쓸지 함께 선택해 주세요)
   ```
3. **저장 방식 선택지를 함께 제시**:
   | 선택 | 동작 | 보안 |
   |------|------|------|
   | A. 이번 대화에서만 사용 | 메모리에 저장하지 않음, 새 대화에서 다시 입력 필요 | 가장 안전 |
   | B. 메모리에 영구 저장 | "BlogN PAT: softn_pat_..." 형태로 어시스턴트 메모리에 기록. 다음 대화부터 자동 재사용 | 보통 (claude.ai 계정 노출 시 함께 노출) |
   | C. 발급 후 만료까지만 (수동 회전) | B와 동일하나, 사용자가 만료/회전 시 직접 메모리에서 삭제 요청 | B와 동일 |
4. **B/C 선택 시 메모리 저장 절차** — claude.ai 메모리 도구가 있으면 다음 키로 저장:
   - 키 이름(예): `blogn_pat_token`
   - 값: 토큰 문자열 그대로 (앞뒤 공백 제거)
   - 함께 저장할 메타: 발급일, 만료 예상일(있으면), scope = `blog`
5. **저장 후 즉시 검증** — `GET /api/v1/blog`로 한 번 호출하여 200 + `success:true` 반환되는지 확인. 401이면 저장된 토큰을 폐기하고 재입력 안내.

### 보안 절대 원칙

- **토큰을 평문으로 응답에 출력하지 않는다.** 마지막 4자리만 노출 (`softn_pat_...xxxx`).
- **로그·테스트 출력·임시 파일에도 토큰을 남기지 않는다.** curl 호출 시에도 `-H "Authorization: Bearer $TOKEN"` 형태로 변수 참조만 사용, 명령어 자체를 사용자에게 보여줄 때는 토큰을 `<MASKED>`로 치환.
- **401 발생 시 메모리의 토큰을 즉시 무효화 후보로 표시**하고 사용자에게 알린다. 자동 삭제는 사용자 동의 후에만.
- **사용자가 "토큰 잊어줘" / "PAT 삭제해" / "로그아웃" 의도를 표명하면 즉시 메모리에서 제거**하고 확인 보고.
- **토큰을 외부 시스템(GitHub gist, 다른 API 등)에 전송하지 않는다.** 본 스킬은 `https://back.softn.kr` 외 다른 URL로 토큰을 보내면 안 된다.
- **세 환경(env, secrets.json, 메모리)에 동일 토큰이 다중 저장된 상태를 피한다** — 환경변수가 있으면 메모리 사본을 만들지 않는다.

### 토큰 회전 / 만료 시나리오

- 401이 발생하면: (1) 만료/취소 가능성을 사용자에게 알리고, (2) 새 토큰 발급 안내, (3) 메모리/secrets.json의 기존 값 제거 동의 요청, (4) 새 값으로 갱신.
- 사용자가 명시적으로 "토큰 갱신했어"라고 하면: 즉시 새 값을 받아 검증 호출(`GET /api/v1/blog`) 후 메모리 업데이트.

> 조회는 두 종류로 나뉜다:
> - **인증 필요**: `GET /api/v1/blog` (내 블로그 목록).
> - **인증 불필요**: `GET /api/v1/blog/public`, `GET /api/v1/blog/{blogId}`, 공개 포스트 목록·단건, 댓글 목록 등.
> claude.ai에서 토큰이 없는 상태로 들어왔어도 **인증 불필요 GET은 그대로 호출 가능**. 변경/내 블로그 조회 단계에서만 위 토큰 탐색 흐름으로 진입.
> 토큰 없이 인증 불필요 GET 호출 시 `myLikeFlag`만 0으로 고정되며 나머지 동작은 동일.

## 기본 블로그

이 스킬은 **프로젝트별·사용자별로 다른 블로그**를 쓸 수 있도록, 대상 블로그(`blogId`)와 선택적 기본값을 **설정 파일**에서 읽는다. 스킬 본문에 blogId를 하드코딩하지 않는다. 자연어 입력에 `blogId`/블로그명이 명시되지 않으면 다음 **순서대로** 설정 파일을 찾아 첫 번째로 발견된 값을 **기본 대상 블로그**로 사용한다.

1. `<현재 작업 디렉토리>/.claude/skills/blog-editor/project.json` — **프로젝트별 설정** (해당 프로젝트에서만 적용, 최우선)
2. `~/.claude/skills/blog-editor/project.json` — **사용자 전역 설정** (프로젝트 설정이 없을 때 fallback)

설정 파일은 특정 blogId를 담으므로 플러그인에 번들되지 않으며, 사용자가 직접 생성한다. 형식·예시는 플러그인의 [`project.example.json`](project.example.json) 참고.

파일 형식:
```json
{
  "blogId": "<UUID — 필수>",
  "blogName": "<블로그 표시명 — 선택, 안내 메시지용>",
  "defaultClsfId": "<선택: 신규 포스트 기본 분류 ID>",
  "defaultClsfName": "<선택: 기본 분류명 (clsfId 미상 시 이름 매칭용)>",
  "defaultPostTag": "<선택: 신규 포스트 기본 태그, 쉼표 구분>"
}
```

적용 규칙:
- `blogId`만 필수. 나머지 필드는 선택이며, 비어 있거나 없으면 해당 기본값을 적용하지 않는다.
- **프로젝트 설정(1)이 있으면 전역 설정(2)보다 항상 우선**한다. (같은 머신에서 프로젝트마다 다른 블로그, 사용자마다 다른 전역 기본값이 공존 가능.)
- 입력에 다른 블로그가 명시되면(이름·ID 매칭) 설정 파일보다 입력값을 우선한다.
- 첫 호출 직전 한 번 "기본 블로그 `<blogName 또는 blogId>`을 사용합니다." 안내 후 진행 (재차 알릴 필요 없음).
- `defaultClsfId`/`defaultClsfName`가 설정돼 있고 포스트 생성 시 분류가 명시되지 않으면 그 값을 기본 분류로 적용한다 (사용자가 다른 분류를 말하면 그쪽 우선 — 자동 강제 아님).
- `defaultPostTag`가 설정돼 있고 태그가 명시되지 않으면 기본 태그로 채운다.
- 두 파일 모두 없거나 `blogId`가 비어 있으면 아래 [프로젝트 설정 부트스트랩](#프로젝트-설정-부트스트랩--파일이-없을-때-생성-유도) 절차로 진입한다.
- "공개 블로그 목록", "전체 공개 블로그", "다른 사람 블로그"처럼 외부 디스커버리를 가리키면 **`GET /api/v1/blog/public`** 사용, 기본값 미적용.

### 프로젝트 설정 부트스트랩 — 파일이 없을 때 생성 유도

프로젝트별 설정(`<현재 작업 디렉토리>/.claude/skills/blog-editor/project.json`)이 없으면, **이 프로젝트 폴더에 설정 파일을 만들도록 1회 유도**한다. 같은 머신의 다른 프로젝트와 블로그가 섞이지 않게 하기 위함이다.

**언제 유도하는가 (트리거 시점):**
- **blogId가 필요한 첫 변경/내-블로그 작업 직전에만** 유도한다 — 포스트 생성·수정·삭제·발행, 본문/메타 PUT, 댓글/분류/좋아요, `GET /api/v1/blog`(내 블로그 목록) 등.
- **순수 조회·생성은 유도하지 않는다** — 인증 불필요 GET(공개 블로그/포스트 조회), 블록 JSON 생성·검증, Markdown↔본문 변환처럼 특정 blogId가 필요 없는 작업에서는 절대 끼어들지 않는다.
- 자연어 입력에 blogId/블로그명이 명시돼 있으면 그 입력을 우선 적용하되, 작업 종료 후 "이 블로그를 프로젝트 설정으로 저장해 둘까요?"를 가볍게 덧붙일 수 있다.
- **세션당 1회**. 사용자가 한 번 거절하면 이 대화에서는 다시 묻지 않고, 전역 설정(2) 또는 목록 선택으로 계속 진행한다.

**유도 절차:**
1. **안내 한 줄** — "이 프로젝트에는 blog-editor 설정(`./.claude/skills/blog-editor/project.json`)이 없습니다. 기본 블로그를 정해 두면 이후 호출이 간편합니다. 지금 만들까요?"
2. **동의하면 대상 블로그 확정** — `GET /api/v1/blog`(PAT 필수)로 내 블로그 목록을 받아 후보를 제시하고, 모호하면 사용자에게 하나를 고르게 한다. (자연어에 이미 블로그가 지정됐으면 그것으로 확정.)
3. **`Write` 도구로 파일 생성** — 경로 `<현재 작업 디렉토리>/.claude/skills/blog-editor/project.json`. 상위 디렉토리가 없으면 함께 만든다. 내용은 확정한 `blogId`(필수)와, 사용자가 함께 정해준 선택 필드(`blogName`/`defaultClsfId`/`defaultClsfName`/`defaultPostTag`)만 채운다. 모르는 선택 필드는 넣지 않는다.
   ```json
   {
     "blogId": "<확정한 UUID>",
     "blogName": "<선택>"
   }
   ```
4. **생성 보고** — "프로젝트 설정을 저장했습니다: `./.claude/skills/blog-editor/project.json` (blogId `…마스킹/표시명`)." 안내 후 원래 요청한 작업을 이어서 진행한다.
5. **거절 시** — 파일을 만들지 않고, 전역 설정(`~/.claude/skills/blog-editor/project.json`)이 있으면 그것을, 없으면 목록에서 고른 blogId를 **이번 작업에만** 적용한다. (다음 호출에서 다시 묻지 않음.)

> 형식·예시 필드는 플러그인의 [`project.example.json`](project.example.json) 참고. 이 파일은 특정 blogId를 담으므로 커밋 대상에서 제외하거나 `.gitignore`에 추가하도록 안내할 수 있다.

## 작동 방식

### 1) 자연어 → 의도 분류

| 의도 | 예시 입력 | 동작 |
|------|----------|------|
| **조회(read)** | "내 블로그 포스트 목록", "포스트 X 본문 보여줘", "분류 목록" | GET 호출 후 정리해서 답변 |
| **포스트 생성(create)** | "포스트 만들어줘 — 제목 X" | 필수 필드 확인 → POST 호출 (메타데이터만) |
| **포스트 수정(update)** | "이 포스트 제목 바꿔", "발행해줘" | 변경 요약 → PUT 호출 (메타데이터만) |
| **포스트 휴지통 이동(soft delete)** | "이 포스트 지워", "삭제해줘" | 영향 범위 안내 → `DELETE /posts/{postId}` (복원 가능) |
| **포스트 복원(restore)** | "되살려", "복원해줘", "휴지통에서 꺼내" | `GET /posts/trash`로 확인 → `PUT /posts/{postId}/restore` |
| **포스트 영구 삭제(hard delete)** | "영구 삭제", "완전히 지워", "휴지통 비워" | **강한 재확인 필수** — cascade, 복구 불가. `DELETE /posts/{postId}/permanent` |
| **블록 JSON 생성** | "이 포스트 본문 마크다운으로 만들어줘", "Editor.js JSON 생성" | [BLOCKS.md](BLOCKS.md) 스펙으로 JSON 작성 → 사용자에게 제공 |
| **블록 JSON 검증** | "이 JSON이 Editor.js 호환인지 봐줘" | type/data 필드 검증 후 보고 |
| **증분 블록 편집** | "이 블록만 고쳐", "문단 하나 끼워넣어", "블록 순서 바꿔", "이 블록 지워" | 블록 1개 단위 `/blocks*` 호출(lockTimestamp 불필요) → **마지막에 `/contents/sync` 1회**. [증분 블록 편집](#증분-블록-편집--blocks--contentssync) 절 참조 |
| **Markdown → 본문** | "이 md 파일을 포스트 본문에 넣어줘", "md 로 포스트 만들어" | `markdown_to_document(md)` → `put_post_contents(...)` |
| **본문 → Markdown** | "이 포스트 본문 markdown 으로 뽑아줘", "내용 md 로 export" | `get_post(...)` → `document_to_markdown(post['postContents'])` |
| **이미지 삽입** | "이 png 파일 본문에 넣어줘", "이미지 추가" | `upload_image(path, post_id=...)` → image 블록 dict, blocks 에 append 후 `put_post_contents` |
| **첨부 파일 삽입** | "이 pdf 첨부해줘", "파일 붙여" | `upload_attachment(path, post_id=...)` → attaches 블록 dict, blocks 에 append 후 `put_post_contents` |
| **YouTube/Vimeo 임베드** | "이 유튜브 영상 본문에 임베드", "vimeo 링크 추가" | `embed(url)` → embed 블록 dict (업로드 불필요) |
| **위키링크/백링크** | "이 글을 OO 포스트에 연결", "내부 링크 걸어줘", "[[ 자동완성", "이 글 역링크 보여줘" | 대상은 `wiki-search`로 탐색 → 본문 블록 텍스트에 `<a class="wikilink" data-post-id="…" data-blog-id="…">` 앵커 삽입 후 `/contents` 저장(백엔드가 `BLOG_POST_LINK` 자동 동기화). 역링크 조회는 `/backlinks`. 상세는 [BLOCKS.md §4.1](BLOCKS.md) |
| **댓글/좋아요/분류** | "댓글 달아줘", "좋아요 눌러줘", "분류 만들어줘" | 해당 엔드포인트 호출 |

### 2) 의도 → API 호출 매핑

전체 엔드포인트 카탈로그는 [ENDPOINTS.md](ENDPOINTS.md) 참조. 자연어 → 엔드포인트 매핑은 ENDPOINTS.md의 **"자연어 매핑 힌트"** 섹션을 우선 참고한다.

### 3) HTTP 호출 패턴

curl로 호출한다. 조회 예:

```bash
curl -sS -X GET "https://back.softn.kr/api/v1/blog/${BLOG_ID}/posts?pageIndex=1" \
  -H "Authorization: Bearer ${BLOGN_PAT_TOKEN}" \
  -H "Accept: application/json"
```

생성 예 (JSON body):

```bash
curl -sS -X POST "https://back.softn.kr/api/v1/blog/${BLOG_ID}/posts" \
  -H "Authorization: Bearer ${BLOGN_PAT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"postTitle":"새 글","postStatus":"DRAFT","postTag":"공지,업데이트"}'
```

응답은 항상 다음 형태로 래핑되어 있다:

```json
{
  "success": true|false,
  "message": "...",
  "data": [...],            // 항상 배열 (단건도 [VO])
  "pagenation": {...}       // 목록 조회만
}
```

`success=false` 또는 HTTP 4xx/5xx이면 [에러 처리](#에러-처리) 섹션 참조.

### 4) 다단계 흐름

자연어 한 문장이 여러 호출을 요구할 수 있다. 예:

> "내 블로그의 '공지' 분류에 '서비스 점검 안내' 포스트 만들어줘"

처리 순서:
1. 기본 blogId 결정 (project.json 또는 list)
2. `GET /api/v1/blog/{blogId}/clsf` → "공지" 매칭되는 `clsfId` 찾기 (없으면 사용자에게 확인)
3. `POST /api/v1/blog/{blogId}/posts` body: `{postTitle:"서비스 점검 안내", clsfId, postStatus:"DRAFT"}`
4. 결과 요약 응답 (postId 보고)

## 블록 JSON 생성

블록 JSON은 Editor.js 2.28.1 스키마를 따른다 (`buildEditorData`가 GET 응답에 사용하는 형식 동일).

**상위 wrapper:**
```json
{
  "time": 1735689600000,
  "version": "2.28.1",
  "blocks": [ ... ]
}
```

**블록 단위 (모든 블록 공통):**
```json
{
  "id": "<10자리 영숫자>",
  "type": "paragraph|header|list|checklist|code|quote|delimiter|table|image",
  "data": { ... type별 필드 }
}
```

전체 type별 data 스키마와 예시는 [BLOCKS.md](BLOCKS.md) 참조. 블록 ID는 새로 생성 시 `[a-zA-Z0-9]{10}` 패턴(Editor.js 기본)을 따른다.

### 권장 — `block_builder.py` 공용 헬퍼

긴 본문(수십 블록 이상)을 한 번에 작성·저장할 때는 매번 인라인으로 JSON을 짜는 대신 공용 빌더 모듈을 사용한다. ID 무작위화, wrapper 구성, PAT 헤더 부착, lockTimestamp 흐름 등 보일러플레이트가 모두 제거된다.

**경로**: `${CLAUDE_PLUGIN_ROOT}/skills/blog-editor/block_builder.py`

**전체 11개 블록 타입 지원** + HTTP 헬퍼 + 파일 업로드 + Markdown 양방향 변환:
- 블록 빌더: `paragraph`, `header(text, level)`, `code(source)`, `ulist(items)`, `olist(items)`, `checklist(items)`, `quote(text, caption, alignment)`, `delimiter()`, `table(rows, with_headings)`, `image(url, caption, ...)`, `embed(source, caption, …)`, `attaches(file_id, file_name, file_size, extension, url?, title?)`
- 문서 wrapper: `document(blocks)` — `{time, version, blocks}` 자동 구성
- HTTP (PAT): `create_post(...)`, `get_post(...)`, `update_post_meta(...)`, `put_post_contents(...)` — `BLOGN_PAT_TOKEN` 환경변수 자동 사용, `BlognApiError` 로 표준화된 에러
- 증분 블록 편집 (PAT): `add_block(...)`, `update_block(...)`, `delete_block(...)`, `move_block(...)`, `sync_contents(...)` — 블록 1개 단위 편집 후 스냅샷 동기화. lockTimestamp 불필요 (자세히는 [증분 블록 편집](#증분-블록-편집--blocks--contentssync) 절)
- 파일 업로드 (PAT): `upload_image(path, post_id=…)`, `upload_attachment(path, post_id=…)`, `get_file(file_id=…)`, `delete_file(file_id=…)` — `POST /api/v1/files/upload` (PAT `file`+`blog` scope) 로 multipart 업로드 후 image/attaches 블록 dict 를 반환. CSRF prefetch 불필요
- Markdown 변환: `markdown_to_document(md)` ↔ `document_to_markdown(doc)` — 11개 블록 + 인라인 마크업 round-trip 가능 (자세한 규칙·한계는 BLOCKS.md §6)

**사용 패턴** — 생성 → 본문 저장을 한 스크립트로:
```python
import os, sys
sys.path.insert(0, os.environ["CLAUDE_PLUGIN_ROOT"] + "/skills/blog-editor")
from block_builder import (
    header, paragraph, code, ulist, table, document,
    create_post, put_post_contents,
)

blocks = [
    header("배경"),
    paragraph("본문 한 문단 — <b>인라인 HTML</b> 그대로 가능."),
    code("SELECT * FROM BLOG_POST"),
    ulist(["항목 A", "항목 B"]),
    table([["키", "값"], ["a", "1"]]),
]

post = create_post(
    blog_id="DY-DEVEL",
    title="새 포스트",
    clsf_id="BC...",
    post_tag="tag1,tag2",
    post_status="DRAFT",
)
put_post_contents(
    blog_id="DY-DEVEL",
    post_id=post["postId"],
    lock_timestamp=post["lockTimestamp"],
    blocks=blocks,  # 또는 post_contents=document(blocks)
)
```

**원칙**:
- 빌더 함수는 BLOCKS.md 스펙을 엄격히 준수한다. 표준 외 필드(예: `code` 의 `language`)는 받지 않는다 — 핵심 원칙 #4 와 일치.
- 보안 — PAT 토큰은 `BLOGN_PAT_TOKEN` 환경변수에서만 읽으며, 빌더는 토큰 값을 stdout/stderr 에 노출하지 않는다.
- 단일 호출은 굳이 빌더가 필요 없다. 블록 수가 적고 보일러플레이트가 작을 때는 그대로 인라인 JSON 사용해도 무방.

### 파일 업로드 흐름 — `upload_image` / `upload_attachment`

이미지(image 블록) · 첨부 파일(attaches 블록) 은 본문에 끼우기 전 백엔드에 먼저 업로드해야 한다. 스킬·MCP 전용 PAT 엔드포인트(`POST /api/v1/files/upload`, `SysFileApiController`)를 사용한다. SPA 의 `/core/file/upload`(세션+CSRF) 와 동일한 업로드/검증 정책을 PAT Bearer 인증으로 복제한 것이다.

```python
# 예: 새 포스트에 이미지 1장 + PDF 1개 + YouTube 임베드 1개를 함께 삽입
post = create_post(blog_id="DY-DEVEL", title="릴리스 소식")
img_block = upload_image("./screenshot.png", post_id=post["postId"], caption="대시보드")
pdf_block = upload_attachment("./changelog.pdf", post_id=post["postId"], title="변경 로그 v1.4")
yt_block  = embed("https://youtu.be/dQw4w9WgXcQ", caption="데모")

put_post_contents(
    blog_id="DY-DEVEL",
    post_id=post["postId"],
    lock_timestamp=post["lockTimestamp"],
    blocks=[
        paragraph("이번 릴리스의 변경사항입니다."),
        img_block,
        pdf_block,
        header("데모 영상", level=2),
        yt_block,
    ],
)
```

**주의 사항**:
- 업로드 진입점은 **`POST /api/v1/files/upload`** — 다른 `/api/v1` 호출과 동일하게 PAT Bearer 로 인증한다. 단 `file` scope 가 capability gate 이고, `repository=BLOG_POST`(기본값) 는 추가로 `blog` scope 가 필요하다. PAT 에 `file` scope 가 없으면 업로드 거부, `blog` 가 없으면 403 `INSUFFICIENT_SCOPE`. CSRF prefetch·세션 쿠키는 불필요.
- multipart 파라미터: `repository`(기본 `BLOG_POST`), `type`(`image`|`thumb`|`attach`), `bindingKey`(= postId), `file`. 헬퍼가 `post_id` 인자를 `bindingKey` 로 매핑한다.
- `post_id` 는 사실상 필수. 누락하면 백엔드가 `SYS_FILE.BINDING_KEY=null` 로 저장하고 포스트 삭제 cascade 가 깨진다 (백엔드 로그에 경고).
- 업로드한 파일은 본인(토큰 userId) 소유로 기록된다. `get_file(file_id=…)` 로 메타 조회, `delete_file(file_id=…)` 로 삭제 — 둘 다 **소유자 본인만** 가능(타인 파일은 403 `FILE_FORBIDDEN`).
- 사이즈 상한과 차단 확장자는 BLOCKS.md §10.3 참조. 헬퍼가 호출 직전 사이즈를 사전 검증한다. attach 는 백엔드가 Tika magic-number 검사까지 수행한다.
- 임베드(YouTube/Vimeo)는 업로드가 아니라 URL 만 필요하므로 `embed(url)` 한 번으로 충분하다. 다른 서비스 URL 은 `ValueError` (CSP 화이트리스트와 정렬).

### Markdown 양방향 변환 — `markdown_to_document` / `document_to_markdown`

긴 본문을 외부에서 markdown 으로 작성·관리하거나, 기존 포스트를 markdown 파일로 백업할 때 사용한다. 변환 규칙은 BLOCKS.md §6 의 표와 일치한다 — 11개 블록 + 인라인 마크업 (`**굵게**`, `*기울임*`, `==형광펜==`, `` `코드` ``, `[링크](url)`, `==형광펜==`).

```python
# md 파일 → 본문 PUT
md = open("draft.md", encoding="utf-8").read()
doc = markdown_to_document(md)
post = get_post(blog_id="DY-DEVEL", post_id="P00001")
put_post_contents(
    blog_id="DY-DEVEL",
    post_id="P00001",
    lock_timestamp=post["lockTimestamp"],
    post_contents=doc,
)

# 본문 → md 파일 (백업/export)
post = get_post(blog_id="DY-DEVEL", post_id="P00001")
open("backup.md", "w", encoding="utf-8").write(
    document_to_markdown(post["postContents"])
)
```

**한계**: round-trip 시 손실되는 정보 — 블록 ID, image tunes(`alignLeft`/`sizeMedium` 등), embed `width/height`, attaches `title`(파일명과 다른 표시명), `<u>` 밑줄(markdown 토큰 부재). 편집 흐름은 가급적 Editor.js JSON 으로 직접 다루고, markdown 은 import/export 보조 경로로 사용한다.

### 본문 저장 흐름 — `PUT .../posts/{postId}/contents`

사용자가 "본문 채워줘", "포스트 내용 작성해줘", "본문 갱신"을 요청하면 다음 순서로 처리한다:

1. **lockTimestamp 확보** — 어디서 얻는지가 케이스마다 다르다:
   - **포스트를 방금 생성한 직후** → `POST /api/v1/blog/{blogId}/posts` 응답 `data[0].lockTimestamp` 그대로 사용. 별도 GET 불필요.
   - **방금 다른 메타/본문 PUT을 한 직후** → 그 응답의 `data[0].lockTimestamp` 그대로 사용.
   - **그 외 (시간 경과, 동시 편집 우려, 알 수 없는 상태)** → `GET /api/v1/blog/{blogId}/posts/{postId}`로 최신 `lockTimestamp` 확보.
2. **블록 JSON 작성** — [BLOCKS.md](BLOCKS.md) 스펙으로 `time`/`version`/`blocks[]` 구성. (신규 블록 ID는 `[a-zA-Z0-9]{10}` 무작위, 기존 블록 갱신은 원본 ID 유지). **본문이 길거나 표·코드·리스트가 섞이는 경우 `block_builder.py` 헬퍼 사용을 권장** (위 절 참조).
3. **저장 호출** — `PUT /api/v1/blog/{blogId}/posts/{postId}/contents` body:
   ```json
   {
     "lockTimestamp": "<직전 응답 또는 GET에서 받은 값>",
     "postStatus": "SAVED",
     "postContents": { "time": 1735689600000, "version": "2.28.1", "blocks": [ ... ] }
   }
   ```
   - `postContents`는 객체(자동 stringify) 또는 이미 stringify된 JSON 문자열 모두 허용.
   - `postStatus`는 선택(기본 `SAVED`). `PUBLISHED`/`DRAFT`로 보내면 상태 전환 효과 → 사용자 사전 확인.
4. **결과 반영** — 응답 `data[0].postContents`(서버가 재구성한 Editor.js 형식)와 새 `lockTimestamp`를 사용자에게 보고.

**서버 동작 요약**: 클라이언트 `lockTimestamp` **사전 검증**(불일치 시 즉시 409) → 기존 `BLOG_POST_BLOCK` 모든 행 삭제 → `blocks[]`를 BLOCK_INDEX 0..N으로 재INSERT → **위키링크 인덱스 동기화**(각 블록 HTML을 `WikiLinkParser`로 파싱해 `<a class="wikilink" data-post-id data-blog-id>` 앵커를 추출·유효 대상 필터링 후 `BLOG_POST_LINK`에 일괄 반영) → 포스트 상태를 EDIT로 갱신(`BLOG_POST.LOCK_TIMESTAMP` 갱신됨) → 갱신된 `LOCK_TIMESTAMP`를 사용해 `BLOG_POST.POST_CONTENTS` 컬럼에 풀 JSON 스냅샷 저장 → 편집 로그 기록. 사전 검증 단계에서 충돌 시 어떤 변경도 일어나지 않는다.

> **백링크는 `/contents` 저장의 부수효과로 자동 생성된다.** 별도 링크 등록 API가 없으므로, 다른 글을 인용·연결하려면 본문 블록에 위키링크 앵커(§위 [BLOCKS.md §4.1])를 심어 저장하면 된다. 앵커를 빼고 저장하면 해당 백링크도 사라진다(매 저장 시 전체 재계산).

> ⚠️ **2026-05-19 이전 동작과의 차이**: 이전에는 서버가 lockTimestamp를 `replaceAllBlocks` 이후에 비교했기 때문에, 포스트를 막 생성하고 본문 PUT을 첫 시도하는 흐름에서도 자기 자신의 부수효과로 인해 409가 발생했다. 현재는 사전 검증으로 바뀌어 **POST 응답의 lockTimestamp를 그대로 첫 본문 PUT에 사용 가능**하다.

### 증분 블록 편집 — `/blocks*` + `/contents/sync`

본문을 통째로 갈아끼우는 `PUT /contents`(일괄 교체) 외에, **블록 1개 단위로 추가/수정/삭제/이동**하는 증분 경로가 있다. 이미 긴 본문이 있고 일부 블록만 손대거나, 순서만 바꾸는 작업에서는 전체를 다시 보내는 대신 증분 경로가 효율적이다.

| 연산 | 엔드포인트 | body | 동시성 |
|------|-----------|------|--------|
| 블록 추가 | `POST .../{postId}/blocks` | `{type, index, data?, blockId?}` | 서버 postId 락 (lockTimestamp 불필요) |
| 블록 수정 | `PUT .../{postId}/blocks/{blockId}` | `{type, data, versionNo?}` | `versionNo` 낙관적 동시성 (불일치 409) |
| 블록 삭제 | `DELETE .../{postId}/blocks/{blockId}` | 없음 | — (이후 인덱스 자동 당김) |
| 블록 이동 | `PUT .../{postId}/blocks/{blockId}/move` | `{fromIndex, toIndex}` | 서버 postId 락 (lockTimestamp 불필요) |
| 본문 동기화 | `POST .../{postId}/contents/sync` | 없음 | — |

**일괄 교체 vs 증분 — 잠금 모델이 다르다:**
- **일괄 교체 `PUT /contents`**: `lockTimestamp` 필수(포스트 단위 Optimistic Lock), 블록 전삭제+재INSERT, 위키링크 전체 재계산, `POST_CONTENTS`/`POST_SEARCH` 스냅샷 즉시 갱신.
- **증분 `/blocks*`**: `lockTimestamp` **안 씀**. add/move 는 서버가 postId 단위 락으로 인덱스 원자성 보장, modify 는 블록별 `versionNo` 로 충돌 검출(생략하면 마지막-쓰기-우선). **두 경로의 동시성 토큰을 혼동하지 말 것** — 증분 호출에 lockTimestamp 를 넣어도 무시된다.

> ⚠️ **반드시 기억할 것 — 증분 편집 후 `/contents/sync`**: `/blocks*` 호출은 `BLOG_POST_BLOCK` 행만 바꾼다. 공개 본문 스냅샷(`POST_CONTENTS`)과 검색 인덱스(`POST_SEARCH`)는 **자동으로 갱신되지 않는다.** 블록 편집 한 묶음을 끝낸 뒤 **`POST /contents/sync` 를 한 번 호출**해 스냅샷을 플러시한다. 호출하기 전에는 GET 단건의 `postContents` 가 옛 내용을 보일 수 있다. (add/modify 시 해당 블록의 위키링크는 그 자리에서 동기화되지만, 스냅샷·검색은 sync 전까지 stale.)

**IDOR/권한**: 모든 `/blocks*` 호출은 편집 권한(EDITOR) 검증 후, `blockId` 가 해당 `postId` 소속인지 확인한다 — 타 포스트 블록을 건드리려 하면 404. 포스트 미존재/blogId 불일치도 404.

**권장 — `block_builder.py` 헬퍼**:
```python
import os, sys
sys.path.insert(0, os.environ["CLAUDE_PLUGIN_ROOT"] + "/skills/blog-editor")
from block_builder import (
    paragraph, header,
    add_block, update_block, delete_block, move_block, sync_contents,
)

# 3번 위치에 새 문단 삽입
add_block(blog_id="DY-DEVEL", post_id="P00001", block=paragraph("추가 문단"), index=3)
# 특정 블록 내용 교체 (헤더로)
update_block(blog_id="DY-DEVEL", post_id="P00001", block_id="abc1234567", block=header("새 제목", level=2))
# 블록 삭제 / 이동
delete_block(blog_id="DY-DEVEL", post_id="P00001", block_id="def8901234")
move_block(blog_id="DY-DEVEL", post_id="P00001", block_id="ghi5678901", from_index=5, to_index=2)
# 편집 마무리 — 스냅샷/검색 인덱스 플러시 (꼭 마지막에 1회)
sync_contents(blog_id="DY-DEVEL", post_id="P00001")
```
- `add_block`/`update_block` 의 `block` 인자는 `paragraph()`/`header()`/`table()` 등 빌더가 반환한 dict 를 그대로 받는다(빌더가 `type`/`data` 를 채움).
- `update_block(version_no=...)` 로 협업 충돌 검출(409). 단독 편집이면 생략 가능.

## 안전 규칙 체크리스트

매 호출 직전 다음을 확인:

- [ ] 변경 호출(POST/PUT/DELETE)인 경우 PAT이 확보되었는가? (환경변수 → 메모리 → 대화 입력 순으로 탐색)
- [ ] 응답·예시 명령어에 토큰을 평문으로 출력하지 않았는가? (마스킹 `softn_pat_...xxxx`)
- [ ] 호출 대상 엔드포인트가 `/api/v1/blog/...` 패턴인가? 다른 도메인 API를 잘못 호출하려는 건 아닌가?
- [ ] DELETE 호출인 경우, 사용자 확인을 받았는가? (소프트 vs 영구 삭제 의도를 명확히 구별했는가?)
- [ ] `/permanent` 호출인 경우, 휴지통 상태(`postStatus='DELETED'`)를 사전 확인했는가? + "복구 불가" 강한 재확인을 받았는가?
- [ ] PUT/DELETE인 경우 body에 최신 `lockTimestamp`를 포함했는가? (Optimistic Lock)
- [ ] 블록 JSON을 생성한 경우, type/data 스키마가 [BLOCKS.md](BLOCKS.md)와 일치하는가?
- [ ] 본문 저장 요청인 경우, `lockTimestamp`를 적절히 확보(직전 응답 재사용 또는 GET)했고, `postStatus` 변경(특히 `PUBLISHED`)에 대해 사용자 확인을 받았는가?
- [ ] 본문 PUT의 `postContents`가 wrapper(`time`/`version`/`blocks`) 형식을 갖췄는가? (단순 blocks 배열만 보내면 400)
- [ ] **증분 블록 편집(`/blocks*`)인 경우**: lockTimestamp 를 넣지 않았는가?(무시됨) 블록 수정은 협업 충돌 검출이 필요하면 `versionNo` 를 포함했는가? 그리고 **편집 묶음 끝에 `POST /contents/sync` 를 호출**해 `POST_CONTENTS`/`POST_SEARCH` 스냅샷을 플러시했는가?
- [ ] **발행(PUBLISHED 전환)인 경우, 메타 PUT(`/posts/{postId}`)이 아니라 전용 `PUT /posts/{postId}/publish` 를 사용했는가?** body: `{publishFlag: 1, lockTimestamp}`. 발행 취소는 `{publishFlag: 0, lockTimestamp}`. 메타 PUT body 에 `postStatus`/`publishFlag` 를 넣어도 SQL 이 받지 않아 무시된다.
- [ ] **이미지/첨부 업로드**: PAT 이 `file` scope(+ BLOG_POST 면 `blog`) 를 보유했는가? `post_id`(→ bindingKey) 를 전달했는가? (누락 시 SYS_FILE.BINDING_KEY=null → 포스트 삭제 cascade 누락). 사이즈 상한(image 10MB / attach 20MB) 과 차단 확장자(`svg`, `exe`, `php` 등) 를 호출 전 검토했는가?
- [ ] **embed 블록**: source URL 이 YouTube/Vimeo 화이트리스트에 해당하는가? (CSP `frame-src` 와 일치해야 iframe 이 렌더된다)
- [ ] **markdown 변환**: round-trip 손실 항목(블록 ID, image tunes, embed width/height, attaches title) 을 사용자에게 사전 고지했는가? 편집은 가급적 JSON 직접 다루고 markdown 은 import/export 보조용.

## 에러 처리

| HTTP | 의미 | 대응 |
|------|------|------|
| 400 | 요청 파라미터 오류 / 댓글 본문 누락 / 포스트가 있는 분류 삭제 시도 / **휴지통 외 포스트에 `/restore` 또는 `/permanent` 호출 (`errorCode: BLOG_POST_NOT_IN_TRASH`)** | `message` 그대로 전달 후 입력 보정 안내. `BLOG_POST_NOT_IN_TRASH`이면 먼저 `DELETE /posts/{postId}`로 휴지통 이동 후 재시도 안내 |
| 401 | 토큰 만료/잘못됨 | 사용자에게 PAT 재발급 안내 |
| 403 | 편집 권한·소유자 권한 부족 | 어떤 권한이 필요한지 안내 (블로그 소유자 / 포스트 작성자 / 편집 권한 보유자) |
| 404 | 블로그·포스트·댓글·분류 미존재, 또는 DRAFT 비소유자 접근 | 사용자에게 ID 또는 이름 재확인 요청 |
| 409 | Optimistic Lock 충돌 (`lockTimestamp` 불일치) | 최신 데이터 다시 GET → lockTimestamp 갱신 후 재시도 |
| 5xx | 서버 오류 | `message` 그대로 전달, 재시도 1회 |

## 자연어 입력 예시 → 처리 흐름

**예 1:** "내 블로그 포스트 목록 보여줘 — 첫 페이지"
- 기본 blogId 결정 → `GET /api/v1/blog/{blogId}/posts?pageIndex=1`
- 표 형태로 출력 (postId, postTitle, postStatus, hitCount, likeCount, modifyDatetime)

**예 2:** "포스트 '안녕하세요 블로그'를 DRAFT로 생성"
- `POST /api/v1/blog/{blogId}/posts` body: `{"postTitle":"안녕하세요 블로그","postStatus":"DRAFT"}`
- 응답에서 `postId`, `lockTimestamp` 추출하여 사용자에게 보고. (응답은 항상 최신 등록 상태의 VO를 반환하므로 곧바로 본문 PUT을 이어갈 수 있다.)

**예 3:** "포스트 abc123 발행해줘"
- `GET /api/v1/blog/{blogId}/posts/abc123` → 현재 `lockTimestamp` fetch
- `PUT /api/v1/blog/{blogId}/posts/abc123/publish` body: `{"publishFlag":1,"lockTimestamp":"<fetch한 값>"}`
- 서버가 `POST_STATUS='PUBLISHED'` 와 `PUBLISH_FLAG=1` 을 원자적으로 동시 갱신.
- 반대로 "비공개로 돌려" / "발행 취소" 의도면 동일 엔드포인트에 `{"publishFlag":0,"lockTimestamp":"..."}` 전송 → `POST_STATUS='DRAFT'` + `PUBLISH_FLAG=0` 복원.
- 발행 효과 안내 후 결과 보고

**예 4:** "포스트 abc123 본문을 다음 마크다운으로 채워줘 — # 제목\n\n첫 문단..."
- `lockTimestamp` 확보: 직전에 POST로 만들었거나 다른 PUT을 한 직후라면 그 응답값을 그대로 사용. 그렇지 않으면 `GET /api/v1/blog/{blogId}/posts/abc123`로 fetch.
- 마크다운 → [BLOCKS.md](BLOCKS.md) 매핑 규칙으로 블록 JSON 생성:
  ```json
  {
    "time": 1735689600000,
    "version": "2.28.1",
    "blocks": [
      {"id":"abcDEF1234","type":"header","data":{"text":"제목","level":1}},
      {"id":"xyzGHI5678","type":"paragraph","data":{"text":"첫 문단..."}}
    ]
  }
  ```
- `PUT /api/v1/blog/{blogId}/posts/abc123/contents` body:
  ```json
  {
    "lockTimestamp": "<직전 응답 또는 GET에서 받은 값>",
    "postStatus": "SAVED",
    "postContents": { "time": 1735689600000, "version": "2.28.1", "blocks": [ ... 위 블록들 ... ] }
  }
  ```
- 응답 `data[0]`의 새 `lockTimestamp`·블록 수 요약 보고. 발행이 필요하면 별도로 메타 PUT(`postStatus:"PUBLISHED"`) 또는 본문 PUT의 `postStatus` 필드로 처리.

**예 5:** "포스트 abc123 삭제"
- 사용자 확인: "포스트 'XXX'를 **휴지통으로 이동**합니다. (복원 가능, 영구 삭제는 추가 단계 필요) 진행할까요?"
- 동의 시 `GET` → lockTimestamp 확보 → `DELETE /api/v1/blog/{blogId}/posts/abc123` body: `{"lockTimestamp":"..."}` → 휴지통 이동 안내

**예 5b:** "포스트 abc123 영구 삭제" / "휴지통에서 abc123 완전히 지워"
- 휴지통 상태 확인: `GET /api/v1/blog/{blogId}/posts/trash` 또는 `GET /posts/abc123`에서 `postStatus='DELETED'` 확인
- 휴지통 상태가 아니면: "이 포스트는 휴지통에 없습니다. 먼저 삭제하시겠습니까? 또는 휴지통 단계 없이 한 번에 영구 삭제할까요?" — 사용자가 후자를 원하면 두 단계(soft → permanent) 연속 실행
- **강한 재확인**: "이 포스트와 모든 블록·댓글·좋아요·편집자 정보가 **완전히 삭제되며 복구할 수 없습니다**. 정말 진행하시겠습니까?"
- 동의 시 `GET` → 최신 lockTimestamp → `DELETE /api/v1/blog/{blogId}/posts/abc123/permanent` body: `{"lockTimestamp":"..."}`

**예 5c:** "휴지통 보여줘" / "삭제한 글 목록"
- `GET /api/v1/blog/{blogId}/posts/trash` → 표 출력 (postId, postTitle, deleteRequestDatetime, userId)
- 사용자가 그 중 특정 포스트 복원/영구삭제를 원하면 후속 처리

**예 5d:** "방금 지운 거 되살려줘" / "휴지통에서 abc123 복원"
- 휴지통 상태 확인 (필요 시 `GET /posts/trash`)
- `GET /api/v1/blog/{blogId}/posts/abc123` → 최신 lockTimestamp
- `PUT /api/v1/blog/{blogId}/posts/abc123/restore` body: `{"lockTimestamp":"..."}` → "DRAFT 상태로 복원되었습니다" 안내

**예 6:** "공지 분류 만들어줘"
- `POST /api/v1/blog/{blogId}/clsf` body: `{"clsfName":"공지","clsfOrder":1}`
- 생성된 `clsfId` 보고

**예 7:** "포스트 abc123에 '잘 봤습니다' 댓글 달아줘"
- `POST /api/v1/blog/{blogId}/posts/abc123/comments` body: `{"cmntContents":"잘 봤습니다"}`
- 등록된 cmntId 보고

**예 8:** "이 markdown 파일을 abc123 본문으로 넣어줘"
- `block_builder.markdown_to_document(open(path).read())` 로 Editor.js wrapper 생성 → 블록 수·이미지/임베드/첨부 갯수 요약을 사용자에게 보여주고 확인
- `get_post` 로 최신 lockTimestamp 확보 → `put_post_contents(..., post_contents=doc)` 호출
- 발행 의도면 별도 `publish_post(...)` 안내

**예 9:** "포스트 abc123 본문을 markdown 파일로 받아"
- `get_post(blog_id, "abc123")` → `data['postContents']` 추출
- `document_to_markdown(post_contents)` → markdown 문자열 반환 (한계: BLOCKS.md §6.2 round-trip 손실 항목 함께 안내)

**예 10:** "이 screenshot.png 를 포스트 abc123 본문 상단에 추가해줘"
- `upload_image("./screenshot.png", post_id="abc123", caption="설명")` → image 블록 dict
- `get_post` 로 현재 본문 + lockTimestamp fetch → blocks 배열 맨 앞에 image 블록 prepend → `put_post_contents(..., blocks=new_blocks)`
- 10MB 초과, 차단 확장자(svg 등), scope 부족(`file`/`blog`) 시 `BlognApiError` 메시지를 그대로 전달

**예 11:** "이 youtube 영상 본문에 임베드해줘 — https://youtu.be/dQw4w9WgXcQ"
- `embed("https://youtu.be/dQw4w9WgXcQ", caption="...")` → embed 블록 dict (업로드 불필요)
- 기존 본문 + lockTimestamp fetch → blocks 배열 끝에 append → `put_post_contents`
- YouTube/Vimeo 외 URL 이면 `ValueError` — 사용자에게 화이트리스트(CSP 와 정렬) 사유 안내

**예 12:** "포스트 abc123 의 3번째 블록만 이 문장으로 고치고, 맨 앞에 인용구 하나 추가해줘"
- 증분 경로 사용 (전체 본문 재전송 불필요, lockTimestamp 불필요):
  - 수정: `update_block(blog_id, post_id="abc123", block_id="<3번째 블록 ID>", block=paragraph("새 문장"))`
  - 추가: `add_block(blog_id, post_id="abc123", block=quote("인용 문구"), index=0)`
- **마무리**: `sync_contents(blog_id, post_id="abc123")` 1회 호출 → `POST_CONTENTS`/`POST_SEARCH` 스냅샷 플러시. (이 호출 전까지 공개 본문/검색 결과는 옛 내용)
- 블록 ID 를 모르면 먼저 `GET /posts/abc123` 로 `postContents.blocks[]` 의 `id`/순서를 확인

**예 13:** "포스트 abc123 의 마지막 블록을 두 번째 위치로 올려줘"
- `GET /posts/abc123` 로 현재 블록 순서·개수 파악 → `move_block(blog_id, post_id="abc123", block_id="<해당 블록 ID>", from_index=<마지막>, to_index=1)`
- `sync_contents(...)` 로 마무리

## 사용자가 명시하지 않은 정보 처리

- **blogId 누락**: project.json(프로젝트별 → 전역) → 둘 다 없으면 [프로젝트 설정 부트스트랩](#프로젝트-설정-부트스트랩--파일이-없을-때-생성-유도)으로 진입(변경/내-블로그 작업에 한해 1회 생성 유도) → `GET /api/v1/blog`로 후보 추출 → 모호하면 사용자 확인.
- **postId 누락**: 가장 최근 조회 결과 또는 `GET /api/v1/blog/{blogId}/posts`로 제목 매칭 → 모호하면 사용자 확인.
- **lockTimestamp가 필요한 PUT/DELETE**: 호출 직전 GET으로 최신값 fetch → body에 포함.
- **블록 ID**: 새로 생성 시 `[a-zA-Z0-9]{10}` 무작위 (Editor.js 기본). 기존 블록 갱신은 원본 ID 유지.
- **블록 type 미지정**: paragraph로 기본 처리.

## 참고 파일

- [ENDPOINTS.md](ENDPOINTS.md) — 전체 엔드포인트 카탈로그 + 자연어 매핑 힌트
- [BLOCKS.md](BLOCKS.md) — Editor.js 블록 JSON 스펙 (paragraph/header/list/checklist/code/quote/delimiter/table/image)
- [block_builder.py](block_builder.py) — 공용 블록 빌더 + HTTP 헬퍼. 긴 본문 작성·저장 시 권장
- 컨트롤러 원본: `src/main/java/com/softn/blogn/api/v1/controller/blog/`
- 에디터 화면: `src/main/webapp/WEB-INF/jsp/blog/post/post_edit.jsp`
- 에디터 커스텀 JS: `src/main/webapp/webdata/js/editorjs_custom.js`
