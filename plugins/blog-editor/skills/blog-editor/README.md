# blog-editor

Claude Code 플러그인 스킬 — BlogN 블로그/포스트 관리 REST API(`https://back.softn.kr/api/v1/blog/...`)를 자연어로 호출합니다. 포스트 CRUD, 본문 블록(Editor.js JSON) 일괄 저장, 이미지·첨부 업로드, YouTube/Vimeo 임베드, Markdown 양방향 변환, 분류/댓글/좋아요까지 처리합니다.

- **배포**: `softn-tools` 마켓플레이스의 `blog-editor` 플러그인 ([softn-claude-plugins](https://github.com/DoYeong-Seo/softn-claude-plugins))
- **인증**: Personal Access Token(PAT, `softn_pat_` 접두사) — `blog` 스코프 필요 (파일 업로드 시 `file` 추가)
- **백엔드**: `https://back.softn.kr` (하드코딩)

> 이 스킬은 플러그인으로 배포됩니다. 본문 파일(SKILL.md/BLOCKS.md/ENDPOINTS.md/block_builder.py)은 플러그인 설치 시 캐시 경로로 복사되며, 스킬 내부에서는 `${CLAUDE_PLUGIN_ROOT}` 로 참조합니다. 사용자가 직접 `~/.claude/skills/` 로 복사할 필요가 없습니다.

---

## 사전 요구사항

| 항목 | 요구 |
|------|------|
| Claude Code | 설치 및 정상 동작 |
| 셸 | bash / zsh |
| Python | 3.8+ — `block_builder.py` 빌더/HTTP 헬퍼용. 표준 라이브러리만 사용하므로 별도 패키지 설치 불필요 |
| BlogN 계정 | https://accounts.softn.kr 가입 + PAT 발급 권한 |
| PAT 스코프 | `blog` 포함 필수 (없으면 401/403). 이미지·첨부 업로드도 쓰려면 `file` 추가 |

---

## 설치 — 플러그인 마켓플레이스

```bash
# 1) 마켓플레이스 추가 (1회)
/plugin marketplace add https://github.com/DoYeong-Seo/softn-claude-plugins.git

# 2) blog-editor 플러그인 설치
/plugin install blog-editor@softn-tools
```

설치 후 스킬은 **네임스페이스가 붙어** 노출됩니다: `/blog-editor:blog-editor`.

### 온보딩 자동화 (선택)

프로젝트 `.claude/settings.json` 에 등록해 두면 폴더 신뢰 시 자동 설치됩니다.

```json
{
  "extraKnownMarketplaces": {
    "softn-tools": {
      "source": { "source": "git", "url": "https://github.com/DoYeong-Seo/softn-claude-plugins.git" }
    }
  },
  "enabledPlugins": ["blog-editor@softn-tools"]
}
```

### 업데이트 / 제거

```bash
# 업데이트 — 마켓플레이스 최신본 받기 (plugin.json version 기준)
/plugin marketplace update softn-tools

# 제거
/plugin uninstall blog-editor@softn-tools
```

> 플러그인 본문은 마켓플레이스가 관리하므로 사용자가 파일을 직접 덮어쓰거나 지우지 않습니다. `BLOGN_PAT_TOKEN` 환경변수와 프로젝트별 `project.json` 만 사용자가 관리합니다.

---

## 설정

### 1) PAT 토큰 환경변수 (필수 — 변경 호출 시)

발급: `https://back.softn.kr` → 마이페이지 → PAT 발급 (스코프에 **`blog`** 체크, 파일 업로드도 쓸 거면 **`file`** 함께 체크)

```bash
# ~/.bashrc 또는 ~/.profile 에 추가 (export 키워드 필수)
export BLOGN_PAT_TOKEN="softn_pat_xxxxxxxxxxxxxxxxxxxxxxxxx"
```

적용 후 `source ~/.bashrc` 또는 새 터미널.

> 토큰이 없거나 만료된 상태에서 변경(POST/PUT/DELETE) 호출 시 401이 반환되며, 스킬은 자동으로 작업을 중단하고 재발급을 안내합니다. 인증이 불필요한 일부 GET(공개 블로그 조회 등)은 토큰 없이도 동작합니다.

### 2) 대상 블로그 — `project.json` (프로젝트별 / 사용자별)

대상 블로그(`blogId`)와 선택적 기본값은 **설정 파일**에서 읽습니다. 스킬 본문에 blogId를 하드코딩하지 않으므로, **프로젝트마다·사용자마다 다른 블로그**를 쓸 수 있습니다. 이 파일은 특정 blogId를 담으므로 **플러그인에 번들되지 않으며 사용자가 직접 생성**합니다. 스킬은 다음 **순서**로 찾아 첫 번째 발견값을 사용합니다:

1. `<현재 작업 디렉토리>/.claude/skills/blog-editor/project.json` — **프로젝트별 설정** (해당 프로젝트에서만, 최우선)
2. `~/.claude/skills/blog-editor/project.json` — **사용자 전역 설정** (프로젝트 설정이 없을 때 fallback)

형식 (`blogId`만 필수, 나머지는 선택 — 번들된 [`project.example.json`](project.example.json) 참고):

| 필드 | 필수 | 설명 |
|------|------|------|
| `blogId` | ✅ | 대상 블로그 UUID |
| `blogName` | ⬜ | 표시명 (안내 메시지용) |
| `defaultClsfId` / `defaultClsfName` | ⬜ | 신규 포스트 기본 분류 (미명시 시 적용, 강제 아님) |
| `defaultPostTag` | ⬜ | 신규 포스트 기본 태그 (쉼표 구분) |

```bash
# 프로젝트 로컬 설정 — 예시 템플릿을 복사해 값만 채우기
mkdir -p .claude/skills/blog-editor
cp "${CLAUDE_PLUGIN_ROOT}/skills/blog-editor/project.example.json" \
   .claude/skills/blog-editor/project.json
# 또는 직접 작성
cat > .claude/skills/blog-editor/project.json <<'EOF'
{
  "blogId": "550e8400-e29b-41d4-a716-446655440000",
  "blogName": "내 메인 블로그",
  "defaultClsfName": "리서치",
  "defaultPostTag": "개발,기록"
}
EOF
```

> 사용자 전역 기본 블로그가 필요하면 같은 파일을 `~/.claude/skills/blog-editor/project.json` 에 둡니다. 프로젝트 설정이 있으면 항상 그쪽이 우선합니다.

`blogId`를 모르면 토큰 설정 후 본인 블로그 목록을 확인:
```bash
curl -sS "https://back.softn.kr/api/v1/blog" \
  -H "Authorization: Bearer ${BLOGN_PAT_TOKEN}" | jq '.data[] | {blogId, blogName}'
```

---

## 동작 확인

설치 후 Claude Code를 새 세션으로 시작하고 입력합니다:

```
/blog-editor:blog-editor
```

또는 자연어로:
```
내 블로그 포스트 목록 보여줘
```

기대 동작:
- 기본 블로그가 설정되어 있으면 "기본 블로그 `<blogName>`을 사용합니다." 안내 후 GET 호출
- 미설정 시 `GET /api/v1/blog`로 후보를 좁히거나 사용자 확인 요청

플러그인이 설치/활성화됐는지 확인:
```bash
/plugin
# 또는
/help   # 등록된 스킬 목록에 blog-editor:blog-editor 노출 확인
```

---

## 구성 파일

플러그인 패키지(`plugins/blog-editor/skills/blog-editor/`)에 포함되는 파일:

```
skills/blog-editor/
├── SKILL.md           # 스킬 진입점 (메타데이터 frontmatter + 동작 규칙)
├── BLOCKS.md          # Editor.js 블록 JSON 스펙 (paragraph/header/list/...)
├── ENDPOINTS.md       # 전체 REST API 엔드포인트 카탈로그 + 자연어 매핑
├── README.md          # 본 문서
├── block_builder.py   # 공용 블록 빌더 + HTTP 헬퍼 (긴 본문 작성 시 사용)
└── project.example.json  # 대상 블로그 설정 템플릿 (복사해서 project.json 으로 사용)
```

| 항목 | 위치 | 머신/프로젝트마다 다름 |
|------|------|------------------------|
| 본문 5개 파일 | 플러그인 캐시 (`${CLAUDE_PLUGIN_ROOT}/skills/blog-editor/`) | ❌ 마켓플레이스가 관리 |
| `BLOGN_PAT_TOKEN` | 환경변수 | ✅ 사용자별 |
| `project.json` | 프로젝트/홈 `.claude/skills/blog-editor/` | ✅ 사용자별, 플러그인 미번들 |

> 스킬 내부에서 `block_builder.py` 를 임포트할 때는 캐시 경로를 사용합니다:
> ```python
> import os, sys
> sys.path.insert(0, os.environ["CLAUDE_PLUGIN_ROOT"] + "/skills/blog-editor")
> from block_builder import header, document
> ```
> `${CLAUDE_PLUGIN_ROOT}` 는 플러그인 스킬 실행 시 Claude Code가 주입하는 환경변수입니다.

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 스킬이 목록에 안 보임 | 마켓플레이스 미추가 / 플러그인 미설치 / 세션이 설치 전 시작됨 | `/plugin` 으로 설치 상태 확인 후 세션 재시작 |
| `BLOGN_PAT_TOKEN 환경변수가 설정되지 않았습니다` | `export` 안 됨 / 셸 재로드 안 됨 | `source ~/.bashrc` 또는 새 터미널 |
| HTTP 401 | 토큰 만료/오타 | https://back.softn.kr 마이페이지에서 재발급 |
| HTTP 403 | PAT 스코프에 `blog`(또는 업로드 시 `file`) 없음 / 편집 권한 없는 포스트 | 스코프 확인 후 재발급, 또는 블로그 소유자/편집권한 확인 |
| HTTP 409 | Optimistic Lock 충돌 (`lockTimestamp` 불일치) | 최신 GET으로 lockTimestamp 다시 받아 재시도 (스킬이 자동 처리) |
| 잘못된 블로그가 기본으로 잡힘 | 전역/프로젝트 `project.json` 우선순위 충돌 | 프로젝트 `project.json`이 전역보다 우선 — 의도와 다르면 프로젝트 파일 수정/삭제 |
| 응답 없이 멈춤 | 백엔드(`back.softn.kr`) 네트워크 차단 | 사내 방화벽/프록시 점검 |
| `ModuleNotFoundError: No module named 'block_builder'` | `sys.path` 에 플러그인 스킬 경로 없음 | 빌더 사용 코드 첫 줄에 `import os, sys; sys.path.insert(0, os.environ["CLAUDE_PLUGIN_ROOT"] + "/skills/blog-editor")` 추가 |
| `BlognApiError: PAT 토큰을 찾을 수 없습니다` (빌더 호출 시) | `BLOGN_PAT_TOKEN` 이 Python 프로세스에 안 보임 | `echo $BLOGN_PAT_TOKEN` 확인 → 비어있으면 `source ~/.bashrc` 또는 새 터미널. 또는 호출 시 `token=` 인자로 전달 |
| 빌더는 정상이지만 PUT/POST 가 401 | 토큰 만료 | 마이페이지에서 재발급 후 `BLOGN_PAT_TOKEN` 갱신 |

---

## 보안 주의사항

- **PAT 토큰을 코드/리포지토리에 커밋하지 마세요.** `BLOGN_PAT_TOKEN`은 `~/.bashrc`/`~/.profile` 등 셸 초기화 파일에만 두세요.
- **`project.json`은 `blogId`/`blogName`만 담습니다 — 토큰을 절대 넣지 마세요.** 프로젝트 리포에 커밋해도 무방하지만, 팀원과 같은 블로그를 공유하지 않는다면 `.gitignore`에 추가하세요.
- DELETE 호출은 스킬이 항상 사용자 확인을 먼저 받습니다 (포스트 삭제 시 블록·댓글·좋아요 cascade 안내 포함).

---

## 참고

- [SKILL.md](SKILL.md) — 스킬 진입점, 동작 규칙, 안전 체크리스트
- [BLOCKS.md](BLOCKS.md) — Editor.js 블록 JSON 스펙
- [ENDPOINTS.md](ENDPOINTS.md) — 전체 엔드포인트 카탈로그
- [block_builder.py](block_builder.py) — 공용 블록 빌더 + HTTP 헬퍼 (긴 본문 작성 시 권장. SKILL.md "권장 — block_builder.py 공용 헬퍼" 절 참고)
