# Blog REST API Endpoints

전체 `api.v1.controller.blog.*` REST API 카탈로그.
변경 계열은 `Authorization: Bearer ${BLOGN_PAT_TOKEN}` 헤더 필수, scope `blog` 필요.
조회 계열(GET)은 인증 없이 접근 가능 (토큰 있으면 `myLikeFlag` 추가).

## 권한 등급

| 등급 | 의미 |
|------|------|
| PUBLIC | 인증 불필요 |
| AUTH | 유효한 PAT 필요 (scope `blog`) |
| OWNER | 블로그 소유자 (`blogInfo.userId == 토큰 userId`) |
| AUTHOR | 포스트 작성자 (`postVO.userId == 토큰 userId`) |
| EDITOR | `BlogPostEditUserService.isAuthorized` 통과 — 편집자 명단 등록자 |

응답 공통 포맷:
```json
{
  "success": true|false,
  "message": "...",
  "data": [...],            // 항상 배열 (단건 응답도 [VO] 형식)
  "pagenation": {            // 목록 응답에만 포함
    "currentPage": 1,
    "totalPages": 10,
    "itemsPerPage": 10,
    "totalItems": 95
  }
}
```

---

## 1. Blog Info (블로그 정보) — `BlogInfoApiController`

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/blog` | AUTH | **내 블로그 목록** — 토큰 사용자 본인 소유 블로그 전체 (모든 `useStatus`·`searchExposeType`) |
| GET | `/api/v1/blog/public` | PUBLIC | **공개 블로그 목록** — `useStatus=ACTIVE` AND `searchExposeType=PUBLIC` 고정 |
| GET | `/api/v1/blog/{blogId}` | PUBLIC | 블로그 단건 (ACTIVE 상태만) |

**내 블로그 vs 공개 블로그**:
- 내 것을 보려면 PAT(`blog` scope) 필수 → `GET /api/v1/blog`. 본인 소유면 비활성·비공개도 모두 보임.
- 디스커버리·외부 노출용 → `GET /api/v1/blog/public`. 인증 불필요, ACTIVE+PUBLIC 고정.

**쿼리 파라미터(두 목록 공통):**
- `pageIndex` (Integer, optional) — 기본 1
- `blogType` (String, optional) — 블로그 유형 필터
- `searchText` (String, optional) — 블로그 이름 검색 (LIKE)

**응답 필드 (`ApiBlogInfoVO`):**
`blogId`, `blogName`, `blogType`, `blogDesc`, `userId`, `userName`, `postCount`, `hitCount`, `likeCount`, `cmntCount`, `createDatetime`

---

## 2. Blog Post (블로그 포스트) — `BlogPostApiController`

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/blog/{blogId}/posts` | PUBLIC | 공개 포스트 목록 (`postStatus=PUBLISHED` AND `searchExposeFlag=1` 고정, **휴지통 자동 제외**). 본문 비포함 |
| GET | `/api/v1/blog/{blogId}/posts/{postId}` | PUBLIC* | 포스트 단건 + 블록 본문(Editor.js JSON). DRAFT는 작성자 본인만 |
| POST | `/api/v1/blog/{blogId}/posts` | AUTH | 포스트 생성 — **메타데이터만** |
| PUT | `/api/v1/blog/{blogId}/posts/{postId}` | EDITOR | 포스트 설정 수정 — **메타데이터만**. ⚠️ `postStatus`/`publishFlag` 는 이 엔드포인트로 갱신되지 않음(SQL 미포함) — 발행은 `/publish` 사용 |
| PUT | `/api/v1/blog/{blogId}/posts/{postId}/publish` | AUTHOR 또는 EDITOR | **포스트 발행/발행취소 전용** — `POST_STATUS` 와 `PUBLISH_FLAG` 동시 갱신. body: `{publishFlag:0|1, lockTimestamp}`. publishFlag=1 → POST_STATUS='PUBLISHED' + PUBLISH_FLAG=1, publishFlag=0 → POST_STATUS='DRAFT' + PUBLISH_FLAG=0 |
| PUT | `/api/v1/blog/{blogId}/posts/{postId}/contents` | EDITOR | 포스트 본문(블록) **일괄 교체** — Editor.js JSON, BLOG_POST_BLOCK 전체 삭제 후 재INSERT. `lockTimestamp` 필수 |
| POST | `/api/v1/blog/{blogId}/posts/{postId}/blocks` | EDITOR | **블록 1개 추가** (증분) — `index` 위치에 삽입. `lockTimestamp` 불필요(서버 postId 락) |
| PUT | `/api/v1/blog/{blogId}/posts/{postId}/blocks/{blockId}` | EDITOR | **블록 1개 수정** (증분) — `versionNo` 낙관적 동시성(불일치 시 409). `lockTimestamp` 미사용 |
| DELETE | `/api/v1/blog/{blogId}/posts/{postId}/blocks/{blockId}` | EDITOR | **블록 1개 삭제** (증분) — 삭제 후 이후 블록 인덱스 1씩 당김. body 없음 |
| PUT | `/api/v1/blog/{blogId}/posts/{postId}/blocks/{blockId}/move` | EDITOR | **블록 이동** (증분) — `fromIndex`→`toIndex` 재정렬. `lockTimestamp` 불필요(서버 postId 락) |
| POST | `/api/v1/blog/{blogId}/posts/{postId}/contents/sync` | EDITOR | **본문 스냅샷 동기화** — BLOG_POST_BLOCK 전체 → `POST_CONTENTS`(Editor.js JSON) + `POST_SEARCH`(형태소). 증분 편집 후 호출. body 없음 |
| DELETE | `/api/v1/blog/{blogId}/posts/{postId}` | OWNER 또는 AUTHOR | **소프트 삭제(휴지통 이동)** — `POST_STATUS='DELETED'`, `DELETE_REQUEST_DATETIME=now()`. 자식 테이블 보존 |
| GET | `/api/v1/blog/{blogId}/posts/trash` | OWNER 또는 AUTHOR | 휴지통(`POST_STATUS='DELETED'`) 목록. OWNER=블로그 전체 휴지통, AUTHOR=본인 글만. 삭제 요청 시각 내림차순 |
| PUT | `/api/v1/blog/{blogId}/posts/{postId}/restore` | OWNER 또는 AUTHOR | 휴지통 포스트 **복원** (`POST_STATUS='DRAFT'`, `DELETE_REQUEST_DATETIME=NULL`). 휴지통 상태 아니면 400 (`BLOG_POST_NOT_IN_TRASH`) |
| DELETE | `/api/v1/blog/{blogId}/posts/{postId}/permanent` | OWNER 또는 AUTHOR | **영구 삭제 (cascade hard delete, 복구 불가)** — 블록·댓글·좋아요·편집자 등 자식 테이블 전부 삭제. 휴지통 상태 아니면 400 |
| POST | `/api/v1/blog/{blogId}/posts/{postId}/like` | AUTH | 좋아요 토글 (등록 ↔ 취소) |
| GET | `/api/v1/blog/{blogId}/posts/wiki-search` | MEMBER 또는 OWNER | 위키 링크 자동완성 검색. query: `q`(필수), `limit`(1–20, 기본 8), `excludePostId`(optional). 비인가 멤버는 빈 결과로 200. `data[]` 원소: `{href, name, description, postId, blogId, thumbUrl, clsfName}` |
| GET | `/api/v1/blog/{blogId}/posts/{postId}/backlinks` | PUBLIC* | 이 포스트를 참조하는(역링크) 포스트 목록. 응답 `data[]`: `ApiBlogPostLinkVO` |
| GET | `/api/v1/blog/{blogId}/posts/{postId}/forward-links` | PUBLIC* | 이 포스트가 참조하는(전진링크) 포스트 목록. 응답 `data[]`: `ApiBlogPostLinkVO` |

**삭제 흐름 — 두 단계 분리**:
1. `DELETE /posts/{postId}` → 휴지통 이동 (소프트 삭제, 복원 가능, 일반 목록에서 사라짐)
2. `DELETE /posts/{postId}/permanent` → 휴지통에서 완전 삭제 (cascade, 복구 불가). **휴지통 상태(`POST_STATUS='DELETED'`)인 포스트만 허용**. 일반 포스트로 곧바로 호출하면 400.

**쿼리 파라미터(목록):**
- `pageIndex` (Integer, optional) — 기본 1
- `clsfId` (String, optional) — 분류 필터
- `postTag` (String, optional) — 태그 필터
- `searchText` (String, optional) — **제목/태그 부분 일치 검색** (`POST_TITLE LIKE %x% OR POST_TAG LIKE %x%`)

**쿼리 파라미터(단건):**
- `increaseHit` (Boolean, optional) — `true`면 조회수 1 증가 (기본 false)

**POST/PUT body (`BlogPostVO`):**

| 필드 | 타입 | POST | PUT | 비고 |
|------|------|------|-----|------|
| `postTitle` | String | 필수 | 선택 | 제목 |
| `clsfId` | String | 선택 | 선택 | 분류 ID |
| `postTag` | String | 선택 | 선택 | 콤마 구분 |
| `postStatus` | String | 선택 | 무시됨 | POST 시 `DRAFT`(기본)/`PUBLISHED` 지정 가능. **메타 PUT 에서는 무시됨** — `BlogPostGeneratedDAO.updateSettings` UPDATE 절에 컬럼이 없다. 발행/취소는 전용 `PUT /publish` 사용. |
| `publishFlag` | Integer | — | 무시됨 | 메타 POST/PUT 모두 처리되지 않음. 발행/취소는 전용 `PUT /publish` 엔드포인트로만 가능. |
| `searchExposeFlag` | Integer | 선택 | 선택 | 0/1 |
| `copyableFlag` | Integer | 선택 | 선택 | 0/1 |
| `shareableFlag` | Integer | 선택 | 선택 | 0/1 |
| `lockTimestamp` | String | — | **필수** | Optimistic Lock |

서버 자동 설정: `postId`(서비스 자동 UUID), `blogId`(path), `userId`(토큰).

**DELETE / restore / permanent body:**
- `lockTimestamp` (String, 필수) — 세 엔드포인트 모두 동일

**휴지통 관련 추가 에러**:
- `restore` 또는 `permanent` 호출 시 포스트가 휴지통 상태가 아니면 → 400 + `errorCode: BLOG_POST_NOT_IN_TRASH`

**📝 본문(블록) PUT — `/posts/{postId}/contents` body:**

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `lockTimestamp` | String | ✓ | Optimistic Lock 비교용. 직전 POST/PUT 응답값 또는 GET 응답값 어느 쪽이든 사용 가능. |
| `postContents` | Object 또는 String | ✓ | Editor.js 풀 JSON: `{ time, version, blocks[] }`. 객체로 보내면 자동 stringify, 문자열도 허용. |
| `postStatus` | String | 선택 | `SAVED`(기본) / `PUBLISHED` / `DRAFT` |

각 `blocks[]` 항목 형식: `{ "id": "<10자 영숫자, 누락 시 서버 자동 생성>", "type": "...", "data": { ... } }`. type/data 스키마는 [BLOCKS.md](BLOCKS.md) 참조.

**서버 동작**: 클라이언트 `lockTimestamp` **사전 검증**(불일치 시 즉시 409로 종료, 어떤 변경도 일어나지 않음) → 기존 `BLOG_POST_BLOCK` 모든 행 삭제 → 요청 `blocks[]`를 `BLOCK_INDEX` 0..N으로 재INSERT → 포스트 상태 `EDIT` 갱신(이 시점에 `LOCK_TIMESTAMP`가 한 번 바뀜) → 갱신된 lockTimestamp로 `BLOG_POST.POST_CONTENTS` 컬럼 스냅샷 저장 → 편집 로그 기록. 충돌·예외 시 전체 롤백.

> 🔄 **2026-05-19 동작 변경**: 이전에는 lockTimestamp 검증이 블록 교체 *이후*에 일어나 자기 자신의 부수효과로 인한 409가 발생할 수 있었다. 현재는 사전 검증으로 변경되어, `POST /posts` 응답의 lockTimestamp를 그대로 첫 본문 PUT에 사용해도 안전하다.

**메타 PUT vs 본문 PUT 분리 원칙**: 메타 PUT(`/posts/{postId}`)은 `postContents`를 수신하지 않는다. 본문 PUT(`/posts/{postId}/contents`)은 메타 필드(제목·태그·분류·노출 등)를 수신하지 않는다. 두 가지를 동시에 바꿔야 한다면 두 번 호출하거나, 본문 PUT의 `postStatus`만 함께 보낸다.

---

### 🧩 증분 블록 편집 — `/posts/{postId}/blocks*` + `/contents/sync`

본문 갱신에는 **두 가지 경로**가 있다. 둘은 잠금 모델·부수효과가 다르므로 섞지 말고 작업 성격에 맞게 택한다.

| 구분 | 일괄 교체 `PUT /contents` | 증분 편집 `/blocks*` |
|------|--------------------------|----------------------|
| 단위 | 본문 전체(blocks[] 통째) | 블록 1개 |
| 동시성 제어 | **`lockTimestamp`** (포스트 단위 Optimistic Lock, 불일치 409) | add/move=**서버 postId 락**(lockTimestamp 불필요) / modify=**`versionNo`**(블록별, 불일치 409) |
| BLOG_POST_BLOCK | 전체 삭제 후 재INSERT | 해당 블록만 INSERT/UPDATE/DELETE, 인덱스 자동 재정렬 |
| 위키링크(BLOG_POST_LINK) | 전체 재계산(`syncPost`) | add/modify 시 **해당 블록만** 동기화(`syncBlock`) |
| `POST_CONTENTS`/`POST_SEARCH` 스냅샷 | **즉시** 갱신 | **자동 갱신 안 됨** → 편집 후 `POST /contents/sync` 호출 필요 |
| 포스트 상태 | `EDIT` 로 전환, `LOCK_TIMESTAMP` 갱신 | 변경 없음 |

> ⚠️ **증분 편집의 핵심**: `/blocks*` 호출만으로는 `POST_CONTENTS`(공개 본문 스냅샷)와 `POST_SEARCH`(검색 인덱스)가 갱신되지 않는다. 블록 add/update/delete/move 를 한 묶음 끝낸 뒤 **반드시 `POST /contents/sync` 를 한 번 호출**해 스냅샷을 플러시한다. 호출 전까지 GET 단건의 `postContents` 는 옛 스냅샷을 보여줄 수 있다.

**블록 추가 — `POST /posts/{postId}/blocks` body:**

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `type` | String | ✓ | 블록 타입(paragraph/header/...). 누락 시 400 |
| `index` | Integer | ✓ | 삽입 위치(0-based). 누락 시 400 |
| `data` | Object | 선택 | 블록 data. 누락 시 `{}` |
| `blockId` | String | 선택 | 미지정 시 서버가 10자 자동 생성 |

**블록 수정 — `PUT /posts/{postId}/blocks/{blockId}` body:**

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `type` | String | ✓ | 누락 시 400 |
| `data` | Object | 선택 | 누락 시 `{}` |
| `versionNo` | Integer | 선택 | DB 현재값과 비교. 불일치 시 **409**. 생략하면 버전 검증 없이 덮어씀 |

**블록 이동 — `PUT /posts/{postId}/blocks/{blockId}/move` body:**

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `fromIndex` | Integer | ✓ | 현재 위치 |
| `toIndex` | Integer | ✓ | 이동 후 위치. `fromIndex==toIndex` 이면 400 |

**블록 삭제 — `DELETE /posts/{postId}/blocks/{blockId}`**: body 없음. 삭제 후 이후 블록 인덱스가 1씩 당겨진다.

**본문 동기화 — `POST /posts/{postId}/contents/sync`**: body 없음. 응답 `data[0]` 에 갱신된 `ApiBlogPostVO`(서버 재구성 `postContents` 포함).

**공통 응답**: 블록 add/update/sync 는 `data[0]` 에 VO(블록 또는 포스트)를 반환. delete/move 는 `success`/`message` 만(블록 VO 없음).

**공통 에러**:
| HTTP | 의미 |
|------|------|
| 400 | `type`/`index`/`fromIndex`/`toIndex` 누락, move 의 같은 인덱스, 인덱스 범위 초과 |
| 403 | 편집 권한(`BlogPostEditUserService.isAuthorized`) 없음 |
| 404 | 포스트 없음 / blogId 불일치 / **blockId 가 해당 포스트 소속이 아님(IDOR 차단)** |
| 409 | 블록 수정 시 `versionNo` 불일치 |

> **VERSION_NO 흐름**: GET 단건의 블록 본문은 Editor.js 형식이라 블록별 `versionNo` 가 노출되지 않는다. 충돌 가능성이 있는 협업 편집에서 `versionNo` 를 활용하려면 별도 블록 조회 경로가 필요하며, 단독 편집 시에는 `versionNo` 를 생략해 마지막-쓰기-우선으로 처리해도 된다.

**응답**: `ApiResponseListVO<ApiBlogPostVO>` — `data[0]`에 갱신된 포스트 단건(새 `lockTimestamp` + `postContents` Map 포함).

**응답 필드 (`ApiBlogPostVO`):**
`postId`, `blogId`, `clsfId`, `clsfName`, `userId`, `userName`, `postTitle`, `postContents`(GET 단건만, Editor.js Map), `postTag`, `postStatus`, `versionNo`, `searchExposeFlag`, `copyableFlag`, `shareableFlag`, `hitCount`, `likeCount`, `commentCount`, `myLikeFlag`, `createDatetime`, `modifyDatetime`, `lockTimestamp`

> **lockTimestamp 형식**: `"yyyy-MM-dd HH:mm:ss"` (서버 로컬 시간, 보통 KST). PUT/DELETE 호출 시 응답에서 받은 값을 **그대로** 다시 보내야 한다. ISO 8601이나 UTC로 변환하면 문자열 equals 비교에 실패하여 409가 발생한다.

---

## 3. Post Classification (포스트 분류) — `BlogPostClsfApiController`

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/blog/{blogId}/clsf` | PUBLIC | 분류 목록 + 분류별 상태별 포스트 수 (`postCount`/`publishedCount`/`deletedCount`) |
| POST | `/api/v1/blog/{blogId}/clsf` | OWNER | 분류 생성 (`clsfId` 자동 UUID) |
| PUT | `/api/v1/blog/{blogId}/clsf/{clsfId}` | OWNER | 분류 수정 |
| DELETE | `/api/v1/blog/{blogId}/clsf/{clsfId}` | OWNER | 분류 삭제 (포스트가 있으면 400) |

**POST/PUT body (`BlogPostClsfVO`):**

| 필드 | POST | PUT | 비고 |
|------|------|-----|------|
| `clsfName` | 필수 | 선택 | |
| `parentClsfId` | 선택 | 선택 | 부모 분류 ID |
| `clsfOrder` | 선택 | 선택 | 미지정 시 99 |
| `lockTimestamp` | — | **필수** | Optimistic Lock |

**응답 필드 (`ApiBlogPostClsfVO`):**
`clsfId`, `blogId`, `parentClsfId`, `clsfName`, `clsfLevel`, `clsfOrder`, `postCount`, `publishedCount`, `deletedCount`, `lockTimestamp`(PUT/DELETE 시 그대로 다시 송부)

**상태별 카운트 정의:**
| 필드 | 의미 | SQL 조건 |
|------|------|----------|
| `postCount` | 분류 내 **전체** 포스트 (휴지통 포함) | `CLSF_ID = ?` |
| `publishedCount` | **게시된** 포스트 | `CLSF_ID = ? AND PUBLISH_FLAG = 1 AND POST_STATUS != 'DELETED'` |
| `deletedCount` | **휴지통**에 있는 포스트 | `CLSF_ID = ? AND POST_STATUS = 'DELETED'` |

> `publishedCount + deletedCount <= postCount`. 차이는 DRAFT 등 미게시 비휴지통 포스트 수.

---

## 4. Post Comment (포스트 댓글) — `BlogPostCmntApiController`

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/blog/{blogId}/posts/{postId}/comments` | PUBLIC | 댓글 목록 (페이징) |
| POST | `/api/v1/blog/{blogId}/posts/{postId}/comments` | AUTH | 댓글 등록 |
| DELETE | `/api/v1/blog/{blogId}/posts/{postId}/comments/{cmntId}` | AUTHOR(댓글 작성자) 또는 OWNER(블로그 소유자) | 댓글 삭제 |

**POST body (`BlogPostCmntVO`):**

| 필드 | 비고 |
|------|------|
| `cmntContents` | 필수, 공백 불가 → 400 |
| `anonymousFlag` | 선택, 0/1 |

**DELETE body:**
- `lockTimestamp` (String, 필수)

**응답 필드 (`ApiBlogPostCmntVO`):**
`cmntId`, `postId`, `userId`, `userName`, `cmntContents`, `likeCount`, `myLikeFlag`, `createDatetime`, `lockTimestamp`(DELETE 시 그대로 다시 송부)

---

## 5. File (파일 업로드) — `SysFileApiController`

스킬·MCP 같은 외부 클라이언트 전용 파일 API. **PAT Bearer 인증** (다른 `/api/v1` 호출과 동일). `file` scope 가 capability gate 이며, repository 별로 추가 도메인 scope 와 자원 소유권을 함께 검증한다. (SPA 의 `/core/file/upload` 세션+CSRF flow 와 동일 업로드/검증 정책을 PAT 인증으로 복제.)

| Method | Path | Role | 용도 |
|--------|------|------|------|
| POST | `/api/v1/files/upload` | AUTH (`file` scope) | 파일 업로드 (multipart/form-data). 단일·복수 part 지원 |
| GET | `/api/v1/files/{fileId}` | OWNER (파일 생성자 본인) | 파일 메타 조회 |
| DELETE | `/api/v1/files/{fileId}` | OWNER (파일 생성자 본인) | 파일 삭제 |

**repository 별 추가 scope:**

| repository | 추가 scope | 비고 |
|-----------|-----------|------|
| `GENERAL` | 없음 | 기본값이 아님 — 헬퍼는 `BLOG_POST` 사용 |
| `BLOG_POST` | `blog` | 블로그 본문 첨부용. PAT 은 `file` + `blog` 두 scope 모두 필요 |

**업로드 요청 (multipart/form-data):**

| 파라미터 | 필수 | 비고 |
|---------|------|------|
| `type` | ✓ | `image` \| `thumb` \| `attach`. 그 외 값은 400 `FILE_TYPE_INVALID` |
| `repository` | 선택 | 기본 `GENERAL`. 블로그 본문은 `BLOG_POST` |
| `bindingKey` | 권장 | 자원 PK(= `postId`). `repository=BLOG_POST` 일 때 권장 — `SYS_FILE.BINDING_KEY` 에 매핑되어 포스트 삭제 cascade · 권한 가드 대상. 누락 시 `bindingKey=null` 로 통과(백엔드 warn) |
| `file` | ✓ | 업로드 파일 (part 명은 임의 허용, 단일·복수) |

**사이즈·확장자 정책** (`CoreFileController` 와 동일):

| type | 최대 크기 | 허용 확장자 |
|------|----------|------------|
| image / thumb | 10MB | png, jpg, jpeg, gif, webp |
| attach | 20MB | pdf, doc(x), xls(x), ppt(x), hwp(x), txt, csv, md, json, xml, zip, 7z, tar, gz, png, jpg, jpeg, gif, webp (+ Tika magic-number 검사) |

**절대 차단 확장자 (모든 type 공통)**: `exe, bat, sh, msi, jar, apk, com, cmd, scr, vbs, ps1, dll, jsp, jspx, asp, aspx, php, phtml, py, rb, js, mjs, ts, html, htm, svg`

**응답** (`ApiResponseListVO<SysFileVO>`): `data[]` 의 각 원소가 업로드된 파일 1건.

**응답 필드 (`SysFileVO`):**
`fileId`, `fileName`, `fileExt`, `fileSize`, `mimeType`, `fileType`, `bindingKey`, `repoCd` (내부 경로 `savedFilePath` 는 보안상 null 로 비노출)

**에러 코드**: `FILE_REQUIRED` · `FILE_TOO_LARGE` · `FILE_NAME_INVALID` · `FILE_TYPE_INVALID` · `FILE_TYPE_FORBIDDEN` · `FILE_REPOSITORY_INVALID` · `INSUFFICIENT_SCOPE`(403) · `USER_REQUIRED`(401) · `FILE_UPLOAD_FAILED`(500) · `FILE_NOT_FOUND`(404) · `FILE_FORBIDDEN`(403, 소유자 불일치 / IDOR 차단) · `FILE_DELETE_REJECTED`(400) · `FILE_DELETE_FAILED`(500)

**응답 → 블록 매핑:**
- image 블록: `file.url = /app/file/view/{fileId}`
- attaches 블록: `file = { url:"/app/file/download/{fileId}", name:fileName, size:fileSize, extension:fileExt, fileId }`, `title=fileName`
- thumb: 포스트 썸네일 전용 — 블록과 별개

**헬퍼** (`block_builder.py`): `upload_image(path, post_id=…)` / `upload_attachment(path, post_id=…)` 가 multipart 업로드 후 블록 dict 반환. `get_file(file_id=…)` / `delete_file(file_id=…)` 로 메타 조회·삭제.

---

## HTTP 상태 코드 요약

| Code | 의미 |
|------|------|
| 200 | 조회/수정/삭제 성공 |
| 201 | 생성 성공 (분류·댓글) |
| 400 | 요청 파라미터 오류, 본문 누락, 포스트 있는 분류 삭제 |
| 401 | 토큰 누락/만료 |
| 403 | 권한 부족 (블로그 소유자 / 포스트 작성자 / 편집 권한자 / 댓글 작성자만 가능한데 아닌 경우) |
| 404 | 블로그/포스트/댓글/분류 미존재, DRAFT 포스트 비소유자 접근 |
| 409 | Optimistic Lock 충돌 |
| 500 | 서버 오류 |

---

## 자연어 매핑 힌트

| 자연어 키워드 | 엔드포인트 | 비고 |
|--------------|-----------|------|
| "내 블로그 목록", "내가 만든 블로그", "내 블로그들" | `GET /api/v1/blog` | PAT 필수, 본인 소유 전체 (상태 무관) |
| "공개 블로그 목록", "전체 블로그", "다른 사람 블로그" | `GET /api/v1/blog/public` | 인증 불필요, ACTIVE+PUBLIC만 |
| "블로그 상세", "블로그 정보 보여줘" | `GET /api/v1/blog/{blogId}` | ACTIVE만 |
| "포스트 목록", "내 글 목록" | `GET /api/v1/blog/{blogId}/posts` | PUBLISHED만 |
| "포스트 본문 보여줘", "글 내용" | `GET /api/v1/blog/{blogId}/posts/{postId}` | 블록 JSON 포함 |
| "포스트 만들어", "초안 작성" | `POST /api/v1/blog/{blogId}/posts` | 메타만 |
| "제목 바꿔", "분류 변경" | `PUT /api/v1/blog/{blogId}/posts/{postId}` | 메타만, lockTimestamp 필수. **`postStatus`/`publishFlag` 는 갱신되지 않음** — 발행은 `/publish` 사용 |
| "발행", "게시해줘", "공개로 전환" | `PUT /api/v1/blog/{blogId}/posts/{postId}/publish` body: `{publishFlag:1, lockTimestamp}` | POST_STATUS='PUBLISHED' + PUBLISH_FLAG=1 동시 갱신 |
| "발행 취소", "비공개로", "초안으로 되돌려" | `PUT /api/v1/blog/{blogId}/posts/{postId}/publish` body: `{publishFlag:0, lockTimestamp}` | POST_STATUS='DRAFT' + PUBLISH_FLAG=0 동시 갱신 |
| "본문 채워", "본문 갱신", "내용 바꿔", "글 내용 저장", "블록 저장" | `PUT /api/v1/blog/{blogId}/posts/{postId}/contents` | Editor.js 풀 JSON **일괄 교체**, lockTimestamp 필수, EDITOR 권한 |
| "블록 하나 추가", "문단 끼워넣어", "N번째에 블록 삽입" | `POST /api/v1/blog/{blogId}/posts/{postId}/blocks` body: `{type, index, data?, blockId?}` | **증분** 추가, lockTimestamp 불필요 |
| "이 블록만 고쳐", "특정 블록 내용 수정" | `PUT /api/v1/blog/{blogId}/posts/{postId}/blocks/{blockId}` body: `{type, data, versionNo?}` | **증분** 수정, versionNo 불일치 시 409 |
| "이 블록 지워", "블록 하나 삭제" | `DELETE /api/v1/blog/{blogId}/posts/{postId}/blocks/{blockId}` | **증분** 삭제, body 없음, 이후 인덱스 당김 |
| "블록 순서 바꿔", "위/아래로 이동", "끌어올려" | `PUT /api/v1/blog/{blogId}/posts/{postId}/blocks/{blockId}/move` body: `{fromIndex, toIndex}` | **증분** 이동, lockTimestamp 불필요 |
| "본문 동기화", "스냅샷 갱신", "검색 반영", (증분 편집 마무리) | `POST /api/v1/blog/{blogId}/posts/{postId}/contents/sync` | POST_CONTENTS+POST_SEARCH 플러시, body 없음. **증분 편집 후 필수** |
| "포스트 삭제", "글 지워", "글 버려" | `DELETE /api/v1/blog/{blogId}/posts/{postId}` | **소프트 삭제 → 휴지통 이동**, 복원 가능. 사용자 확인 필수 |
| "휴지통 목록", "삭제된 글 보여줘", "지운 포스트들" | `GET /api/v1/blog/{blogId}/posts/trash` | OWNER=블로그 전체, AUTHOR=본인 글만 |
| "포스트 복원", "되살려", "휴지통에서 꺼내" | `PUT /api/v1/blog/{blogId}/posts/{postId}/restore` | `POST_STATUS='DRAFT'`로 복원, lockTimestamp 필수 |
| "영구 삭제", "완전히 지워", "휴지통 비워", "복구 불가능하게 삭제" | `DELETE /api/v1/blog/{blogId}/posts/{postId}/permanent` | **cascade hard delete — 복구 불가**. 강력한 사용자 재확인 + 휴지통 상태 검증 필수 |
| "좋아요", "좋아요 취소" | `POST /api/v1/blog/{blogId}/posts/{postId}/like` | 토글 |
| "위키 링크 검색", "포스트 자동완성", "[[ 자동완성", "내부 링크 후보" | `GET /api/v1/blog/{blogId}/posts/wiki-search?q=...&limit=8&excludePostId=...` | Editor.js link-autocomplete 호환 데이터를 v1 envelope 로 래핑 |
| "이 포스트를 인용한 글", "역링크", "backlink" | `GET /api/v1/blog/{blogId}/posts/{postId}/backlinks` | 응답 `data[]` 은 `ApiBlogPostLinkVO` |
| "이 포스트가 가리키는 글", "참조하는 포스트", "forward link" | `GET /api/v1/blog/{blogId}/posts/{postId}/forward-links` | 응답 `data[]` 은 `ApiBlogPostLinkVO` |
| "분류 목록", "카테고리", "분류별 포스트 수" | `GET /api/v1/blog/{blogId}/clsf` | 응답에 `postCount`/`publishedCount`/`deletedCount` 포함 |
| "분류별 게시된 글 수", "휴지통에 있는 글 수" | `GET /api/v1/blog/{blogId}/clsf` 응답 활용 | 별도 호출 불필요 — 한 번에 다 옴 |
| "분류 추가", "카테고리 생성" | `POST /api/v1/blog/{blogId}/clsf` | OWNER만 |
| "분류 수정", "분류 이름 바꿔" | `PUT /api/v1/blog/{blogId}/clsf/{clsfId}` | OWNER만, lockTimestamp |
| "분류 삭제" | `DELETE /api/v1/blog/{blogId}/clsf/{clsfId}` | 포스트 있으면 400 |
| "댓글 목록" | `GET /api/v1/blog/{blogId}/posts/{postId}/comments` | |
| "댓글 달아", "댓글 등록" | `POST /api/v1/blog/{blogId}/posts/{postId}/comments` | 본문 필수 |
| "댓글 삭제" | `DELETE /api/v1/blog/{blogId}/posts/{postId}/comments/{cmntId}` | 작성자/블로그 소유자 |
| "본문 만들어", "Editor.js JSON 생성", "블록 JSON" | (스킬 내부 → 이어서 본문 PUT) | [BLOCKS.md](BLOCKS.md) 스펙으로 작성 후 `PUT /posts/{postId}/contents` 호출 |
| "이미지 넣어", "사진 올려", "png 첨부", "이미지 업로드" | `POST /api/v1/files/upload` (type=image) → image 블록 | PAT `file`+`blog` scope. `bindingKey`=postId. `upload_image()` 헬퍼 |
| "파일 첨부", "pdf 올려", "문서 붙여" | `POST /api/v1/files/upload` (type=attach) → attaches 블록 | Tika magic-number 검사. `upload_attachment()` 헬퍼 |
| "업로드한 파일 정보", "파일 메타 조회" | `GET /api/v1/files/{fileId}` | 소유자 본인만. `get_file()` 헬퍼 |
| "그 파일 삭제", "업로드 취소", "파일 지워" | `DELETE /api/v1/files/{fileId}` | 소유자 본인만. `delete_file()` 헬퍼 |

---

## 다단계 흐름 패턴

| 사용자 요청 | 호출 순서 |
|-----------|----------|
| "블로그명만으로 포스트 작성" | (1) `GET /api/v1/blog`(내 블로그)에서 blogId 매칭 → 없으면 `GET /api/v1/blog/public` → (2) `POST /api/v1/blog/{blogId}/posts` |
| "분류명만으로 포스트 분류 변경" | (1) `GET /api/v1/blog/{blogId}/clsf` → clsfId 매칭 → (2) `GET /api/v1/blog/{blogId}/posts/{postId}` lockTimestamp → (3) `PUT` |
| "PUT 전 lockTimestamp" | (1) GET으로 현재 lockTimestamp fetch → (2) body에 포함 → (3) PUT |
| "DELETE 영향 범위 보고" | (1) GET 상세 → (2) cascade(블록·댓글·좋아요) 사용자 보고 → (3) 동의 → (4) DELETE |
| "발행" / "공개" | (1) GET → lockTimestamp → (2) `PUT /publish` body: `{publishFlag:1, lockTimestamp}` — 서버가 POST_STATUS='PUBLISHED' 도 함께 갱신 |
| "비공개로 돌려" / "발행 취소" | (1) GET → lockTimestamp → (2) `PUT /publish` body: `{publishFlag:0, lockTimestamp}` — POST_STATUS='DRAFT' 동시 복원 |
| "발행 + 분류 동시" | 두 번의 PUT 호출. (1) GET → lockTimestamp → (2) PUT 메타 `{clsfId, lockTimestamp}` → (3) PUT 메타 응답 lockTimestamp 로 `PUT /publish` `{publishFlag:1, lockTimestamp}`. 메타와 발행은 별도 채널이므로 한 번에 묶을 수 없다. |
| "본문 갱신" | (1) `GET /posts/{postId}` → lockTimestamp → (2) [BLOCKS.md](BLOCKS.md) 스펙으로 블록 JSON 작성 → (3) `PUT /posts/{postId}/contents` body: `{lockTimestamp, postStatus:"SAVED", postContents:{time,version,blocks}}` |
| "블록 몇 개만 증분 편집" | (1) 필요한 만큼 `POST /blocks`(추가) · `PUT /blocks/{blockId}`(수정) · `DELETE /blocks/{blockId}`(삭제) · `PUT /blocks/{blockId}/move`(이동) — lockTimestamp 불필요 → (2) **마지막에 `POST /contents/sync` 1회** 로 POST_CONTENTS/POST_SEARCH 스냅샷 플러시 |
| "특정 블록만 교체 + 즉시 검색 반영" | (1) `PUT /blocks/{blockId}` body: `{type, data, versionNo?}` → (2) `POST /contents/sync` |
| "본문 갱신 + 발행" | (1) GET → lockTimestamp → (2) 블록 JSON 작성 → (3) `PUT /contents` body: `{lockTimestamp, postContents}` → (4) **본문 PUT 응답 lockTimestamp 로 `PUT /publish` body: `{publishFlag:1, lockTimestamp}`** — 본문 PUT 은 PUBLISH_FLAG 를 갱신하지 않으므로 발행은 항상 `/publish` 호출 필요. 또는 `block_builder.publish_post(...)` 헬퍼 사용. |
| "삭제한 글 복원" | (1) `GET /posts/trash` → postId 매칭 → (2) `GET /posts/{postId}`로 최신 `lockTimestamp` → (3) `PUT /posts/{postId}/restore` body: `{lockTimestamp}` → DRAFT로 복원됨 안내 |
| "휴지통 비우기 — 특정 포스트 영구 삭제" | (1) `GET /posts/trash` 표시 → 사용자 재확인 "복구 불가능, cascade 삭제됩니다" → (2) `GET /posts/{postId}` lockTimestamp → (3) `DELETE /posts/{postId}/permanent` body: `{lockTimestamp}` |
| "삭제 → 영구삭제 일괄" (한 단계로 완전히 지움) | 별도 단축 엔드포인트 없음. (1) `DELETE /posts/{postId}` (휴지통 이동) → 휴지통 상태가 된 직후 (2) 새 lockTimestamp GET → (3) `DELETE /posts/{postId}/permanent`. 사용자 의도가 명확히 "영구 삭제"이고 휴지통 단계를 건너뛰고 싶다면 두 호출을 연달아 실행하되, 사이 단계에서 lockTimestamp 갱신을 잊지 말 것 |
