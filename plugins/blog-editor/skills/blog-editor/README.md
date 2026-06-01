# blog-editor

Claude Code용 사용자 레벨 스킬 — BlogN 블로그/포스트 관리 REST API(`https://back.softn.kr/api/v1/blog/...`)를 자연어로 호출합니다. 포스트 CRUD, 본문 블록(Editor.js JSON) 일괄 저장, 분류/댓글/좋아요까지 처리합니다.

- **인증**: Personal Access Token(PAT, `softn_pat_` 접두사) — `blog` 스코프 필요
- **백엔드**: `https://back.softn.kr` (하드코딩)
- **사용 대상**: BlogN 백엔드와 통신해야 하는 모든 프로젝트(또는 프로젝트 외부)에서 동일하게 동작

스킬 본문(SKILL.md/BLOCKS.md/ENDPOINTS.md)은 사용자 레벨(`~/.claude/skills/blog-editor/`)에 한 번 설치하면 모든 프로젝트에서 자동으로 노출됩니다. 프로젝트별 기본 블로그(`project.json`)만 선택적으로 따로 둡니다.

---

## 사전 요구사항

| 항목 | 요구 |
|------|------|
| Claude Code | 설치 및 정상 동작 |
| 셸 | bash / zsh |
| Python | 3.8+ — `block_builder.py` 빌더/HTTP 헬퍼용. 표준 라이브러리만 사용하므로 별도 패키지 설치 불필요 |
| BlogN 계정 | https://accounts.softn.kr 가입 + PAT 발급 권한 |
| PAT 스코프 | `blog` 포함 필수 (없으면 401/403) |

---

## 설치 — 사용자 레벨 (1회)

### 옵션 A. 수동 복사 (권장 — 외부 의존성 없음)

다른 머신/계정에 배포할 때는 다음 **5개 파일** 을 `~/.claude/skills/blog-editor/`로 복사하면 끝납니다.

```bash
# 1) 디렉터리 생성
mkdir -p ~/.claude/skills/blog-editor

# 2) 스킬 본문 5개 파일 복사 (배포 패키지에서 가져오기)
cp SKILL.md BLOCKS.md ENDPOINTS.md README.md block_builder.py \
   ~/.claude/skills/blog-editor/

# 3) (선택) 전역 기본 블로그를 쓸 거면 project.json 생성 — 아래 "설정" 섹션 참고
```

### 옵션 B. 압축 패키지로 배포

배포자가 압축 파일을 만들어 두면 수신자는 한 줄로 설치합니다.

**배포 측** (스킬 디렉터리에서):
```bash
tar -czf blog-editor-skill.tar.gz -C ~/.claude/skills blog-editor
```

**설치 측**:
```bash
mkdir -p ~/.claude/skills && tar -xzf blog-editor-skill.tar.gz -C ~/.claude/skills
```

### 옵션 C. 사내 Git 저장소에서 설치

```bash
git clone <internal-repo-url>/blog-editor-skill.git ~/.claude/skills/blog-editor
```

업데이트:
```bash
cd ~/.claude/skills/blog-editor && git pull
```

---

## 설정

### 1) PAT 토큰 환경변수 (필수 — 변경 호출 시)

발급: `https://back.softn.kr` → 마이페이지 → PAT 발급 (스코프에 **`blog`** 체크)

```bash
# ~/.bashrc 또는 ~/.zshrc 에 추가
export BLOGN_PAT_TOKEN="softn_pat_xxxxxxxxxxxxxxxxxxxxxxxxx"
```

적용 후:
```bash
source ~/.bashrc  # 또는 ~/.zshrc
```

> 토큰이 없거나 만료된 상태에서 변경(POST/PUT/DELETE) 호출 시 401이 반환되며, 스킬은 자동으로 작업을 중단하고 재발급을 안내합니다. 인증이 불필요한 일부 GET(공개 블로그 조회 등)은 토큰 없이도 동작합니다.

### 2) 기본 블로그 — `project.json` (선택)

자연어에 `blogId`나 블로그명을 매번 명시하지 않으려면 미리 기본값을 설정합니다.

스킬은 다음 **순서**로 찾아 첫 번째 발견된 값을 사용합니다:

1. `<현재 작업 디렉토리>/.claude/skills/blog-editor/project.json` — 프로젝트별 우선
2. `~/.claude/skills/blog-editor/project.json` — 전역 fallback

#### 전역 기본값 설정

```bash
cat > ~/.claude/skills/blog-editor/project.json <<'EOF'
{
  "blogId": "550e8400-e29b-41d4-a716-446655440000",
  "blogName": "내 메인 블로그"
}
EOF
```

#### 프로젝트별 override (전역과 다른 블로그를 쓸 때만)

```bash
mkdir -p .claude/skills/blog-editor
cat > .claude/skills/blog-editor/project.json <<'EOF'
{
  "blogId": "<해당-프로젝트-전용-blogId>",
  "blogName": "프로젝트 전용 블로그"
}
EOF
```

> **주의**: 프로젝트별 `project.json`을 만들 때 **`SKILL.md` 등 본문 파일은 복제하지 않습니다.** 사용자 레벨 본문 + 프로젝트 레벨 `project.json` 조합으로 충분합니다.

`blogId`를 모르면 토큰 설정 후 다음을 호출하여 본인의 블로그 목록을 확인:
```bash
curl -sS "https://back.softn.kr/api/v1/blog" \
  -H "Authorization: Bearer ${BLOGN_PAT_TOKEN}" | jq '.data[] | {blogId, blogName}'
```

---

## 동작 확인

설치 후 Claude Code를 새 세션으로 시작하고 다음을 입력합니다:

```
/blog-editor
```

또는 자연어로:
```
내 블로그 포스트 목록 보여줘
```

기대 동작:
- 기본 블로그가 설정되어 있으면 "기본 블로그 `<blogName>`을 사용합니다." 안내 후 GET 호출
- 미설정 시 `GET /api/v1/blog`로 후보를 좁히거나 사용자 확인 요청

스킬이 등록되었는지 빠르게 확인하려면:
```bash
ls ~/.claude/skills/blog-editor/
# SKILL.md  BLOCKS.md  ENDPOINTS.md  README.md  block_builder.py  [project.json]
```

빌더 모듈이 정상 임포트되는지 (Python 3.8+ 확인 겸):
```bash
python3 -c "
import sys; sys.path.insert(0, '$HOME/.claude/skills/blog-editor')
from block_builder import header, document
print(document([header('OK')]))"
```
`{"time": ..., "version": "2.28.1", "blocks": [{"id": "...", "type": "header", ...}]}` 형태 JSON 이 출력되면 빌더 정상.

---

## 파일 구조

```
~/.claude/skills/blog-editor/
├── SKILL.md           # 스킬 진입점 (메타데이터 frontmatter + 동작 규칙)
├── BLOCKS.md          # Editor.js 블록 JSON 스펙 (paragraph/header/list/...)
├── ENDPOINTS.md       # 전체 REST API 엔드포인트 카탈로그 + 자연어 매핑
├── README.md          # 본 문서 (설치/배포 안내)
├── block_builder.py   # 공용 블록 빌더 + HTTP 헬퍼 (긴 본문 작성 시 사용)
└── project.json       # (선택) 전역 기본 블로그
```

| 파일 | 배포 시 포함? | 머신/계정마다 달라짐? |
|------|---------------|-----------------------|
| `SKILL.md` | ✅ 필수 | ❌ 동일 |
| `BLOCKS.md` | ✅ 필수 | ❌ 동일 |
| `ENDPOINTS.md` | ✅ 필수 | ❌ 동일 |
| `README.md` | ✅ 권장 | ❌ 동일 |
| `block_builder.py` | ✅ 필수 | ❌ 동일 |
| `project.json` | ❌ 미포함 | ✅ 사용자별로 작성 |

---

## 업데이트 / 제거

### 업데이트

옵션 A 사용 시: 새 버전 패키지에서 본문 5개 파일을 덮어쓰기.
```bash
cp SKILL.md BLOCKS.md ENDPOINTS.md README.md block_builder.py \
   ~/.claude/skills/blog-editor/
```

> `project.json`은 덮어쓰지 마세요 — 사용자 설정이므로 보존됩니다.
> `block_builder.py` 는 한 번 import 한 Python 프로세스에서 캐싱될 수 있습니다. 빌더를 갱신한 직후에는 새 Python 호출(또는 Claude Code 새 세션) 에서 다시 import 해야 변경이 반영됩니다.

### 제거

```bash
rm -rf ~/.claude/skills/blog-editor
unset BLOGN_PAT_TOKEN  # 또는 ~/.bashrc 에서 export 라인 삭제
```

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 스킬이 목록에 안 보임 | Claude Code 세션이 설치 전에 시작됨 | 세션 재시작 |
| `BLOGN_PAT_TOKEN 환경변수가 설정되지 않았습니다` | `export` 안 됨 / 셸 재로드 안 됨 | `source ~/.bashrc` 또는 새 터미널 |
| HTTP 401 | 토큰 만료/오타 | https://back.softn.kr 마이페이지에서 재발급 |
| HTTP 403 | PAT 스코프에 `blog` 없음 / 편집 권한 없는 포스트 | 스코프 확인 후 재발급, 또는 블로그 소유자/편집권한 확인 |
| HTTP 409 | Optimistic Lock 충돌 (`lockTimestamp` 불일치) | 최신 GET으로 lockTimestamp 다시 받아 재시도 (스킬이 자동 처리) |
| 잘못된 블로그가 기본으로 잡힘 | 전역/프로젝트 `project.json` 우선순위 충돌 | 프로젝트 `project.json`이 전역보다 우선 — 의도와 다르면 프로젝트 파일 수정/삭제 |
| 응답 없이 멈춤 | 백엔드(`back.softn.kr`) 네트워크 차단 | 사내 방화벽/프록시 점검 |
| `ModuleNotFoundError: No module named 'block_builder'` | `sys.path` 에 스킬 디렉터리가 없음 | 빌더 사용 코드 첫 줄에 `import sys; sys.path.insert(0, os.path.expanduser('~/.claude/skills/blog-editor'))` 추가 |
| `BlognApiError: PAT 토큰을 찾을 수 없습니다` (빌더 호출 시) | `BLOGN_PAT_TOKEN` 환경변수가 Python 프로세스에 안 보임 | 현재 셸에서 `echo $BLOGN_PAT_TOKEN` 확인 → 비어있으면 `source ~/.bashrc` 또는 새 터미널. 또는 호출 시 `token=` 인자로 전달 |
| 빌더는 정상이지만 PUT/POST 가 401 | 토큰 만료 | 마이페이지에서 재발급 후 `BLOGN_PAT_TOKEN` 갱신 |

---

## 보안 주의사항

- **PAT 토큰을 코드/리포지토리에 커밋하지 마세요.** `BLOGN_PAT_TOKEN`은 `~/.bashrc` 등 셸 초기화 파일에만 두세요.
- **`project.json`은 `blogId`/`blogName`만 담습니다 — 토큰을 절대 넣지 마세요.** 프로젝트 리포에 커밋해도 무방하지만, 팀원과 같은 블로그를 공유하지 않는다면 `.gitignore`에 추가하세요.
- DELETE 호출은 스킬이 항상 사용자 확인을 먼저 받습니다 (포스트 삭제 시 블록·댓글·좋아요 cascade 안내 포함).

---

## 참고

- [SKILL.md](SKILL.md) — 스킬 진입점, 동작 규칙, 안전 체크리스트
- [BLOCKS.md](BLOCKS.md) — Editor.js 블록 JSON 스펙
- [ENDPOINTS.md](ENDPOINTS.md) — 전체 엔드포인트 카탈로그
- [block_builder.py](block_builder.py) — 공용 블록 빌더 + HTTP 헬퍼 (긴 본문 작성 시 권장. SKILL.md "권장 — block_builder.py 공용 헬퍼" 절 참고)
