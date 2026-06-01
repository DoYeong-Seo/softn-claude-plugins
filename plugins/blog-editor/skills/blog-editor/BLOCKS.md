# Editor.js 블록 JSON 스펙

`post_edit.jsp` + `editorjs_custom.js` + 서버 `BlogPostBlockEVO` 분석 결과 기반.
이 문서의 type/data 스키마는 **블록 JSON 생성/검증 시 반드시 일치**해야 한다.

## 1. 상위 Wrapper 구조

GET `/api/v1/blog/{blogId}/posts/{postId}` 응답 `postContents` 또는 사용자에게 제공할 본문 JSON 형식.

```json
{
  "time": 1735689600000,
  "version": "2.28.1",
  "blocks": [
    { "id": "abcDEF1234", "type": "...", "data": { ... } }
  ]
}
```

| 필드 | 타입 | 비고 |
|------|------|------|
| `time` | Long | epoch ms (생성 시 `System.currentTimeMillis()`) |
| `version` | String | 항상 `"2.28.1"` |
| `blocks[]` | Array | 블록 배열 (순서 = 표시 순서) |

## 2. 블록 공통 필드

```json
{
  "id": "<10자리 영숫자>",
  "type": "paragraph|header|list|checklist|code|quote|delimiter|table|image|embed|attaches",
  "data": { ... }
}
```

- `id`: Editor.js가 자동 생성하는 10자리 base62 (`/^[a-zA-Z0-9_-]{10}$/`). 신규 블록 생성 시 이 패턴으로 생성. 기존 블록 갱신 시 원본 ID 유지.
- `type`: 아래 11가지 중 하나만 허용. 그 외는 paragraph로 fallback.
- `data`: type별 스키마. 아래 섹션 참조.

서버 저장 시(`BLOG_POST_BLOCK` 테이블)는 `blockId`, `blockType`, `blockData`(data JSON 문자열), `blockIndex`, `parentBlockId` 등으로 분해된다 — 클라이언트는 wrapper 형식만 다루면 된다.

---

## 3. Type별 data 스키마

### 3.1 paragraph

가장 기본 텍스트 블록. inline HTML(`<b>`, `<i>`, `<u>`, `<a>`, `<mark>`, `<code>`) 허용.

```json
{
  "id": "p1234abcde",
  "type": "paragraph",
  "data": { "text": "본문 텍스트입니다. <b>강조</b> 가능." }
}
```

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `text` | String | ✓ | inline 마크업 허용 |

### 3.2 header

제목 블록 (h1 ~ h6).

```json
{
  "id": "h1234abcde",
  "type": "header",
  "data": { "text": "섹션 제목", "level": 2 }
}
```

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `text` | String | ✓ | |
| `level` | Integer | ✓ | 1-6, 기본 2 |

### 3.3 list

순서/비순서 목록. NestedList(중첩 가능) 또는 List 모두 동일 스키마.

```json
{
  "id": "l1234abcde",
  "type": "list",
  "data": {
    "style": "unordered",
    "items": [
      "첫 번째",
      "두 번째",
      { "content": "중첩 가능", "items": ["하위1", "하위2"] }
    ]
  }
}
```

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `style` | String | ✓ | `"unordered"` 또는 `"ordered"` |
| `items[]` | Array | ✓ | 문자열 또는 `{ content, items? }` 객체 (NestedList 사용 시) |

### 3.4 checklist

체크박스 목록.

```json
{
  "id": "c1234abcde",
  "type": "checklist",
  "data": {
    "items": [
      { "text": "할 일 1", "checked": false },
      { "text": "완료된 일", "checked": true }
    ]
  }
}
```

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `items[].text` | String | ✓ | |
| `items[].checked` | Boolean | ✓ | |

### 3.5 code

코드 블록 (단일 코드 영역, 언어 메타 없음).

```json
{
  "id": "k1234abcde",
  "type": "code",
  "data": { "code": "function hello() {\n  console.log('hi');\n}" }
}
```

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `code` | String | ✓ | 줄바꿈은 `\n` |

### 3.6 quote

인용 블록.

```json
{
  "id": "q1234abcde",
  "type": "quote",
  "data": {
    "text": "인용 본문",
    "caption": "출처/저자",
    "alignment": "left"
  }
}
```

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `text` | String | ✓ | |
| `caption` | String | 선택 | 출처/저자, 빈 문자열 가능 |
| `alignment` | String | 선택 | `"left"` 또는 `"center"`, 기본 left |

### 3.7 delimiter

구분선. data는 빈 객체.

```json
{
  "id": "d1234abcde",
  "type": "delimiter",
  "data": {}
}
```

### 3.8 table

행/열 표.

```json
{
  "id": "t1234abcde",
  "type": "table",
  "data": {
    "withHeadings": true,
    "content": [
      ["이름", "역할",      "비고"],
      ["김철수", "개발자",  "백엔드"],
      ["이영희", "디자이너", "UX"]
    ]
  }
}
```

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `withHeadings` | Boolean | 선택 | true면 첫 행이 `<th>`로 렌더 |
| `content[][]` | String[][] | ✓ | 2차원 셀 배열 |

### 3.9 image

이미지 블록. **`file.url`은 사전 업로드된 URL이어야 한다** (BlogN: `/app/file/uploadImage` 또는 `/app/file/fetchUrl` 응답에서 받은 URL).

```json
{
  "id": "i1234abcde",
  "type": "image",
  "data": {
    "file": { "url": "/uploaded/2026/05/abc.png" },
    "caption": "그림 설명",
    "withBorder": false,
    "withBackground": false,
    "stretched": false,
    "alignLeft": false,
    "alignRight": false,
    "sizeSmall": false,
    "sizeMedium": false
  }
}
```

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `file.url` | String | ✓ | 업로드된 이미지 URL (외부 URL 허용) |
| `caption` | String | 선택 | |
| `withBorder` | Boolean | 선택 | 테두리 |
| `withBackground` | Boolean | 선택 | 배경 박스 |
| `stretched` | Boolean | 선택 | 너비 100% |
| `alignLeft` / `alignRight` | Boolean | 선택 | 정렬 (둘 다 false면 가운데) |
| `sizeSmall` / `sizeMedium` | Boolean | 선택 | 크기 (둘 다 false면 full) |

### 3.10 embed

YouTube · Vimeo 동영상 임베드 블록. `@editorjs/embed` (paste-only) + 커스텀 toolbox(`CustomEmbedTool`).
**서버 CSP `frame-src` 화이트리스트**(`youtube.com` / `youtube-nocookie.com` / `player.vimeo.com`)와 짝이므로
다른 서비스를 임의 추가하면 iframe 이 차단된다 — youtube / vimeo 만 사용한다.

```json
{
  "id": "e1234abcde",
  "type": "embed",
  "data": {
    "service": "youtube",
    "source": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "embed":  "https://www.youtube.com/embed/dQw4w9WgXcQ",
    "width":  580,
    "height": 320,
    "caption": ""
  }
}
```

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `service` | String | ✓ | `"youtube"` 또는 `"vimeo"` (소문자 고정) |
| `source` | String | ✓ | 사용자가 입력한 원본 URL (페이지 URL) |
| `embed` | String | ✓ | 라이브러리가 service 별 `embedUrl` 템플릿으로 생성한 iframe `src` |
| `width` | Integer | 선택 | 기본 580 (라이브러리 기본) |
| `height` | Integer | 선택 | 기본 320 (라이브러리 기본) |
| `caption` | String | 선택 | 임베드 아래 캡션 |

**embedUrl 템플릿 (`@editorjs/embed/dist/embed.mjs` 미러)**:
- youtube: `https://www.youtube.com/embed/<id>`
- vimeo:   `https://player.vimeo.com/video/<id>?title=0&byline=0`

**source → id 추출 정규식**:
- youtube: `(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|v\/))([a-zA-Z0-9_-]+)`
- vimeo:   `vimeo\.com\/(?:video\/)?(\d+)`

`source` 만 알고 `embed` 가 누락된 경우엔 위 두 정규식으로 id 를 추출해 embedUrl 을 직접 조립한 뒤 저장한다 (서버가 보강하지 않음).

### 3.11 attaches

파일 첨부(다운로드 카드) 블록. `@editorjs/attaches` + `createAttachesUploader` (회신서 §6.1).
업로드 직후 `POST /api/v1/files/upload` 응답의 `fileId` 를 그대로 보존하고, **렌더 시 다운로드 URL 은 `/app/file/download/{fileId}`** 로 조립한다.

```json
{
  "id": "a1234abcde",
  "type": "attaches",
  "data": {
    "file": {
      "url":       "/app/file/download/F0001234",
      "name":      "monthly_report_2026_05.pdf",
      "size":      245760,
      "extension": "pdf",
      "fileId":    "F0001234"
    },
    "title": "월간 보고서 (2026-05)"
  }
}
```

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `file.url` | String | ✓ | 다운로드 URL — 일반적으로 `/app/file/download/{fileId}` (Content-Disposition: attachment) |
| `file.name` | String | ✓ | 원본 파일명. 카드에 표시 |
| `file.size` | Integer | ✓ | 바이트 단위 크기 (`SysFileVO.fileSize`) |
| `file.extension` | String | ✓ | 소문자 확장자 (`pdf`, `docx`, …). 카드 아이콘 배지에 표시 |
| `file.fileId` | String | 권장 | 업로드 응답의 `SysFileVO.fileId`. 후속 갱신·삭제·재참조에 사용 |
| `title` | String | 선택 | 카드 상단 편집 가능 표시명. `contenteditable` 으로 사용자가 수정 가능 |

**확장자 정책 (백엔드 `CoreFileController` 미러)**:
- 허용(attach): `pdf, doc, docx, xls, xlsx, ppt, pptx, hwp, hwpx, txt, csv, md, json, xml, zip, 7z, tar, gz, png, jpg, jpeg, gif, webp`
- 절대 차단(모든 type): `exe, bat, sh, msi, jar, apk, com, cmd, scr, vbs, ps1, dll, jsp, jspx, asp, aspx, php, phtml, py, rb, js, mjs, ts, html, htm, svg`
- 사이즈 상한: image=10MB, attach=20MB

> XSS 메모: 라이브러리는 `title` 을 저장 시 `innerHTML` 로 보존하나, 본문 렌더는 `node.textContent` 로 수행한다(라이브러리 v2 dist line 733/834). 따라서 HTML 태그가 그대로 렌더되지는 않는다. 다른 채널(RSS/이메일/공유 카드)에서 `title` 을 출력할 때는 별도 escape 필요.

---

## 4. Inline Markup (모든 텍스트 블록 공통)

paragraph / header / list / checklist / quote 의 텍스트 영역 안에서 사용 가능한 inline HTML:

| 태그 | 의미 | 예 |
|------|------|---|
| `<b>` | 굵게 | `<b>강조</b>` |
| `<i>` | 이탤릭 | `<i>기울임</i>` |
| `<u>` | 밑줄 | `<u>밑줄</u>` |
| `<a href="...">` | 외부/일반 링크 | `<a href="https://...">링크</a>` |
| `<a class="wikilink" …>` | **위키링크(내부 포스트 링크 → 백링크 생성)** | `<a class="wikilink" data-post-id="BP..." data-blog-id="...">대상 글</a>` (아래 §4.1) |
| `<mark class="cdx-marker">` | 형광펜 (Marker tool) | `<mark class="cdx-marker">하이라이트</mark>` |
| `<code class="inline-code">` | 인라인 코드 (InlineCode tool) | `<code class="inline-code">x = 1</code>` |

→ 데이터 저장 시 이스케이프된 사용자 입력은 `<` → `&lt;` 처럼 처리되지 않고 **HTML 그대로 저장**된다 (Editor.js가 contentEditable 결과를 그대로 직렬화).

### 4.1 위키링크 앵커 (백링크 자동 생성)

다른 포스트를 가리키는 **내부 링크**는 일반 `<a href>` 가 아니라 **위키링크 앵커**로 심는다. 본문을 `PUT .../posts/{postId}/contents` 로 저장하면 **백엔드가 본문 HTML의 위키링크 앵커를 자동 파싱해 `BLOG_POST_LINK`(역링크 인덱스)에 동기화**한다. 별도의 링크 등록 API 호출이 필요 없다.

**앵커 형식** — 텍스트 블록(paragraph/header/list/checklist/quote)의 `data.text` 안에 인라인 HTML로 삽입:

```html
<a class="wikilink" data-post-id="{대상 postId}" data-blog-id="{대상 blogId}" href="{href}">표시 텍스트</a>
```

| 속성 | 필수 | 설명 |
|------|------|------|
| `class="wikilink"` | ✅ | 파서가 위키링크를 식별하는 기준. 없으면 일반 링크로 취급되어 백링크가 생성되지 않는다. |
| `data-post-id` | ✅ | 대상 포스트 UUID. 파서가 추출하는 핵심 키. |
| `data-blog-id` | ✅ | 대상 블로그 UUID. |
| `href` | 권장 | 렌더링 시 이동 경로. 보통 `wiki-search` 결과의 `href` 를 그대로 사용. |

**작성 흐름:**

1. **대상 탐색** — `GET /api/v1/blog/{blogId}/posts/wiki-search?q=<검색어>&limit=8` (자동완성). 결과 `data[]` 원소 `{href, name, postId, blogId, ...}` 에서 연결할 포스트를 고른다.
2. **앵커 삽입** — 위 메타로 `<a class="wikilink" data-post-id … data-blog-id … href …>name</a>` 를 블록 `text` 에 끼워 넣는다.
3. **저장** — `PUT .../posts/{postId}/contents` 로 본문 저장. 백엔드가 모든 블록을 `WikiLinkParser` 로 파싱 → 유효 대상만 필터링 → `BLOG_POST_LINK` 에 일괄 동기화(기존 링크는 교체)한다.
4. **역링크 조회** — `GET /api/v1/blog/{blogId}/posts/{postId}/backlinks` 로 이 포스트를 참조하는 글 목록을 읽는다.

**주의:**
- 동기화는 **본문 저장(`/contents`) 시점에 전체 재계산**된다. 앵커를 지우고 저장하면 해당 링크도 인덱스에서 사라진다.
- 존재하지 않거나 접근 불가한 `data-post-id` 는 백엔드 필터링 단계에서 제외된다 (앵커 텍스트는 본문에 남지만 백링크는 생성 안 됨).
- `class="wikilink"`·`data-*` 가 빠진 일반 `<a href>` 는 백링크 대상이 아니다.
- Markdown 변환(`markdown_to_document`)에는 위키링크 토큰이 없다 — 위키링크는 블록 JSON에 직접 앵커 HTML로 작성한다.

---

## 5. 검증 체크리스트

블록 JSON을 생성한 직후 자체 검증:

- [ ] 최상위에 `time`(Long), `version`("2.28.1"), `blocks`(Array)가 모두 있는가?
- [ ] 각 블록에 `id`(10자), `type`(허용된 11개 중 하나), `data`(객체)가 있는가?
- [ ] `type` 별 data 필드가 위 스펙대로 채워졌는가?
  - paragraph/header: `text` 존재
  - header: `level` 1-6
  - list: `style ∈ {unordered, ordered}`, `items` 배열
  - checklist: `items[]` 각 요소에 `text`, `checked`
  - code: `code` 존재
  - quote: `text` 존재
  - table: `content` 2차원 배열, 모든 행 길이 동일
  - image: `file.url` 존재
  - embed: `service ∈ {youtube, vimeo}`, `source`, `embed` 모두 존재. embed URL 이 service 별 템플릿(`/embed/<id>` · `/video/<id>`)과 일치하는가?
  - attaches: `file.url`, `file.name`, `file.size`, `file.extension` 존재. 확장자가 차단 목록(`exe`, `php`, `svg` 등) 에 들어가지 않는가?
- [ ] 블록 ID 중복 없음
- [ ] 표준 외 type 은 사용하지 않음 — 사용 요청 시 사용자에게 paragraph 또는 code 로 대체 가능 안내

---

## 6. Markdown ↔ 블록 JSON 변환 규칙

사용자가 마크다운을 제공하면 본 매핑으로 블록 JSON 으로 변환하고, 역으로 기존 블록 JSON 을 마크다운으로 export 할 때도 같은 매핑을 거꾸로 적용한다. 구현은 `block_builder.py` 의 `markdown_to_document(md)` / `document_to_markdown(doc)` 두 함수.

### 6.1 Markdown → 블록 (parse)

| 마크다운 | type | 비고 |
|----------|------|------|
| `# 제목` ~ `###### 제목` | header | `#` 개수 = `level` (1~6) |
| `- 항목` / `* 항목` 연속 | list | style=unordered |
| `1. 항목` 연속 | list | style=ordered, 시작 번호는 보존하지 않음(Editor.js 가 자동 부여) |
| `- [ ] / - [x] 항목` 연속 | checklist | `[x]` ↔ `checked=true` |
| ```` ```언어 … ``` ```` | code | code 본문만 보존 (Editor.js 스펙상 language 필드 없음) |
| `> 인용` (연속 라인 join) | quote | text=내용, caption="" |
| `---` / `***` / `___` 단독 라인 | delimiter | |
| `\| a \| b \| ⏎ \|---\|---\|` 표 | table | content=2D 배열, `withHeadings=true` (`\|---\|` 구분줄 감지) |
| `![alt](url)` 단독 라인 | image | `file.url=url`, `caption=alt`(alt 가 있을 때만) |
| `[YouTube/Vimeo URL]` 단독 라인 (또는 raw URL) | embed | `service`/`source`/`embed` 자동 도출 (3.10 정규식) |
| `[📎 파일명](URL "size,ext,fileId")` 단독 라인 | attaches | title 부분이 파일명, URL 이 다운로드 링크, optional title 어트리뷰트 `size,ext,fileId` 로 메타 전달 (확장 markdown) |
| 공백 줄 | (블록 분리자, 생성 안 함) | |
| 그 외 텍스트 | paragraph | inline 마크업 변환 후 |

inline 마크업:
- `**굵게**` / `__굵게__` → `<b>`
- `*기울임*` / `_기울임_` → `<i>`
- `==형광펜==` → `<mark class="cdx-marker">`
- `~~취소선~~` → 미지원(취소선 도구 미등록) — 그대로 텍스트 유지
- `` `코드` `` → `<code class="inline-code">`
- `[링크](url)` → `<a href="url">링크</a>`

> 밑줄(`<u>`) 은 표준 markdown 토큰이 없어 parse 단계에서는 만들어지지 않는다 (필요하면 사용자가 직접 HTML 입력). export 단계에서는 `<u>...</u>` 를 그대로 유지한다.

### 6.2 블록 → Markdown (serialize)

위 표의 역방향. 추가 규칙:

| type | 출력 |
|------|------|
| header | `#` × level + ` ` + text |
| paragraph | text (inline HTML → markdown 토큰 역변환) |
| list | 각 항목 앞 `- ` (unordered) 또는 `1. 2. 3. …` (ordered). NestedList items 는 2-space indent 로 들여쓴다 |
| checklist | `- [ ] ` 또는 `- [x] ` + text |
| code | ```` ```\n{code}\n``` ```` |
| quote | 줄마다 `> ` 접두. `caption` 이 있으면 마지막에 `> — {caption}` |
| delimiter | `---` (단독 라인) |
| table | 첫 행은 `\| … \|`, `withHeadings=true` 이면 두 번째 라인에 `\|---\|---\|…` 구분줄, 이후 행도 동일 형식 |
| image | `![{caption}]({file.url})` |
| embed | source URL 을 단독 라인으로 그대로 출력 (YouTube/Vimeo 페이지 URL) |
| attaches | `[📎 {file.name}]({file.url} "{size},{extension},{fileId}")` |

블록 사이는 항상 빈 줄로 분리한다.

> ⚠️ 한계: 블록 ID, image tunes(`alignLeft` 등), embed `width/height`, attaches `title` 은 markdown 토큰에 표현되지 않으므로 round-trip 시 손실된다. **편집 흐름은 가급적 Editor.js JSON 으로 직접 다루고, markdown 은 export/import 용 보조 경로로만 사용한다.**

---

## 7. 블록 ID 생성 (Bash 헬퍼)

```bash
# 10자리 base62 (영숫자) 무작위 ID 생성
gen_block_id() {
  tr -dc 'A-Za-z0-9' </dev/urandom | head -c 10
  echo
}
```

또는 Python:

```python
import secrets, string
def gen_block_id():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(10))
```

---

## 8. 예시: 블로그 글 한 편 통째 JSON

```json
{
  "time": 1735689600000,
  "version": "2.28.1",
  "blocks": [
    { "id": "h0H1aB2cD3", "type": "header",    "data": { "text": "BlogN 정식 출시 안내", "level": 1 } },
    { "id": "p4eF5gH6iJ", "type": "paragraph", "data": { "text": "안녕하세요. <b>BlogN</b> 팀입니다." } },
    { "id": "d7kL8mN9oP", "type": "delimiter", "data": {} },
    { "id": "h0qR1sT2uV", "type": "header",    "data": { "text": "주요 기능", "level": 2 } },
    { "id": "l3wX4yZ5aB", "type": "list",      "data": { "style": "unordered", "items": ["블록 기반 에디터", "실시간 협업", "버전 관리"] } },
    { "id": "k6cD7eF8gH", "type": "code",      "data": { "code": "curl -X GET https://back.softn.kr/api/v1/blog" } },
    { "id": "q9iJ0kL1mN", "type": "quote",     "data": { "text": "쓰기를 시작하면 멈출 수 없다.", "caption": "익명", "alignment": "left" } },
    { "id": "e2oP3qR4sT", "type": "embed",     "data": { "service": "youtube", "source": "https://youtu.be/dQw4w9WgXcQ", "embed": "https://www.youtube.com/embed/dQw4w9WgXcQ", "width": 580, "height": 320, "caption": "데모 영상" } },
    { "id": "a5uV6wX7yZ", "type": "attaches",  "data": { "file": { "url": "/app/file/download/F0001234", "name": "release_notes.pdf", "size": 245760, "extension": "pdf", "fileId": "F0001234" }, "title": "릴리스 노트" } }
  ]
}
```

---

## 9. PUT `.../posts/{postId}/contents` 호출 예

위 wrapper(섹션 1)를 `postContents` 필드에 그대로 실어 본문 PUT을 호출한다.
요청·응답 스펙은 [ENDPOINTS.md](ENDPOINTS.md)의 "본문(블록) PUT" 섹션 참조.

### 9.1 단계 흐름
1. `GET /api/v1/blog/{blogId}/posts/{postId}` → `lockTimestamp` fetch.
2. 블록 JSON 작성 (위 섹션들).
3. `PUT /api/v1/blog/{blogId}/posts/{postId}/contents` 호출.

### 9.2 curl 예 (객체로 보내기 — 권장)

```bash
curl -sS -X PUT "https://back.softn.kr/api/v1/blog/${BLOG_ID}/posts/${POST_ID}/contents" \
  -H "Authorization: Bearer ${BLOGN_PAT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "lockTimestamp": "20260507143012",
    "postStatus": "SAVED",
    "postContents": {
      "time": 1735689600000,
      "version": "2.28.1",
      "blocks": [
        { "id": "h0H1aB2cD3", "type": "header",    "data": { "text": "제목", "level": 1 } },
        { "id": "p4eF5gH6iJ", "type": "paragraph", "data": { "text": "첫 문단입니다." } }
      ]
    }
  }'
```

### 9.3 curl 예 (이미 stringify 된 JSON 문자열로 보내기)

`postContents` 값을 문자열로 감싸도 동일하게 처리된다 (서버가 자동 파싱):

```bash
CONTENTS_JSON='{"time":1735689600000,"version":"2.28.1","blocks":[{"id":"h0H1aB2cD3","type":"header","data":{"text":"제목","level":1}}]}'

curl -sS -X PUT "https://back.softn.kr/api/v1/blog/${BLOG_ID}/posts/${POST_ID}/contents" \
  -H "Authorization: Bearer ${BLOGN_PAT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg ts "20260507143012" --arg c "$CONTENTS_JSON" \
        '{lockTimestamp:$ts, postStatus:"SAVED", postContents:$c}')"
```

### 9.4 응답 처리

성공 시 `data[0]`에 갱신된 포스트 단건이 들어온다 (`postContents`는 서버가 `BLOG_POST_BLOCK`에서 재구성한 Editor.js Map, `lockTimestamp`는 새 값). 다음 PUT 호출 시 이 새 `lockTimestamp`를 사용한다.

| 응답 코드 | 처리 |
|----------|------|
| 200 | `data[0].lockTimestamp` 갱신 보고, 블록 수 요약 |
| 400 | `postContents`/`lockTimestamp` 누락 또는 JSON 파싱 실패 — 입력 보정 |
| 403 | 편집 권한 없음 — 블로그 소유자 또는 편집자 명단 등록 필요 |
| 404 | 포스트 미존재 / blogId 불일치 |
| 409 | `lockTimestamp` 충돌 — GET 다시 → 사용자에게 변경사항 충돌 안내 후 재시도 |

---

## 10. 파일 업로드 (image / attaches)

image · attaches 블록의 URL 은 사전 업로드된 백엔드 파일을 가리켜야 한다 (외부 URL 도 image 블록은 허용). 업로드는 **`POST /api/v1/files/upload`** (`SysFileApiController`, 스킬·MCP 전용) 가 표준 진입점이다 — 응답 `SysFileVO` 의 `fileId` 를 받아 블록 `file.*` 필드를 채운다.

### 10.1 요청

- 메서드/경로: `POST {BASE}/api/v1/files/upload`
- 인증: **PAT Bearer** (`Authorization: Bearer ${BLOGN_PAT_TOKEN}`). `file` scope 가 capability gate, `repository=BLOG_POST` 는 추가로 `blog` scope 필요 → 블로그 본문 업로드용 PAT 은 **`file` + `blog` 두 scope 모두 보유**해야 한다. CSRF prefetch·세션 쿠키 불필요.
- 본문: `multipart/form-data`
  - `file`: 바이너리 (part 명은 임의 허용, 단일·복수)
  - `repository`: 보통 `BLOG_POST` (기본 `GENERAL`)
  - `type`: `image` · `thumb` · `attach` 중 하나 (다른 값은 400 `FILE_TYPE_INVALID`)
  - `bindingKey`: `repository=BLOG_POST` 일 때 권장 — 자원 PK(= `postId`). `SYS_FILE.BINDING_KEY` 에 매핑되어 포스트 삭제 cascade · 권한 가드 대상이 된다. 빈 값이면 백엔드가 warn 로그 남기고 `bindingKey=null` 로 통과. (구 `/core/file/upload` 의 `postId` 파라미터에 대응.)

### 10.2 응답

```json
{
  "success": true,
  "errorCode": null,
  "message": null,
  "data": [
    {
      "fileId": "F0001234",
      "fileName": "report.pdf",
      "fileExt": "pdf",
      "fileSize": 245760,
      "mimeType": "application/pdf",
      "fileType": "attach"
    }
  ]
}
```

`success=false` 시 `errorCode`: `FILE_REQUIRED` · `FILE_TOO_LARGE` · `FILE_NAME_INVALID` · `FILE_TYPE_INVALID` · `FILE_TYPE_FORBIDDEN` · `FILE_REPOSITORY_INVALID` · `INSUFFICIENT_SCOPE`(403, `blog` scope 부족) · `USER_REQUIRED`(401) · `FILE_UPLOAD_FAILED`(500). 조회/삭제는 추가로 `FILE_NOT_FOUND`(404) · `FILE_FORBIDDEN`(403, 소유자 불일치).

### 10.3 사이즈·확장자 정책 (백엔드 미러)

| 타입 | 최대 크기 | 허용 확장자 |
|------|----------|------------|
| image / thumb | 10MB | png, jpg, jpeg, gif, webp |
| attach | 20MB | pdf, doc(x), xls(x), ppt(x), hwp(x), txt, csv, md, json, xml, zip, 7z, tar, gz, png, jpg, jpeg, gif, webp |

**절대 차단 확장자 (모든 type 공통)**: `exe, bat, sh, msi, jar, apk, com, cmd, scr, vbs, ps1, dll, jsp, jspx, asp, aspx, php, phtml, py, rb, js, mjs, ts, html, htm, svg`

### 10.4 응답 → 블록 매핑

- image 블록: `file.url = /app/file/view/{fileId}` (외부 URL 도 허용)
- attaches 블록: `file = { url:"/app/file/download/{fileId}", name:fileName, size:fileSize, extension:fileExt, fileId }`, `title=fileName` (사용자가 카드에서 수정 가능)
- thumb: 포스트 썸네일 전용 — 블록과 별개로 `PostUpsertInput.thumbFileId` 에 저장한다.

### 10.5 헬퍼

`block_builder.py` 의 `upload_image(path, post_id=…)` / `upload_attachment(path, post_id=…)` 호출 시 PAT Bearer multipart POST 를 처리하고 image/attaches 블록 dict 를 반환한다 (`post_id` → `bindingKey` 매핑). 업로드한 파일 메타 조회·삭제는 `get_file(file_id=…)` / `delete_file(file_id=…)` — 둘 다 소유자 본인만 가능.

### 10.6 YouTube / Vimeo 임베드

embed 블록은 **업로드가 필요 없다** — `block_builder.embed(url)` 한 번이면 source/embed/width/height/caption 까지 자동 도출. CSP `frame-src` 화이트리스트(youtube.com · youtube-nocookie.com · player.vimeo.com)와 짝이므로 두 서비스 외 URL 은 거절한다.
