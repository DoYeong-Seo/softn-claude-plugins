# erd-design

Claude Code 플러그인 스킬 — BlogN ERD 설계 도구의 REST API(`https://back.softn.kr/api/v1/erd/...`)를 자연어로 호출합니다. ERD 프로젝트/다이어그램/테이블/컬럼/관계/인덱스 메타데이터를 관리하고, ERD 정의로부터 MySQL DDL 스크립트를 생성합니다.

- **배포**: `softn-tools` 마켓플레이스의 `erd-design` 플러그인 ([softn-claude-plugins](https://github.com/DoYeong-Seo/softn-claude-plugins))
- **인증**: Personal Access Token(PAT, `softn_pat_` 접두사) — `erd` 스코프 필요
- **백엔드**: `https://back.softn.kr` (하드코딩)

> ⚠️ **이 스킬은 실제 MySQL DB 스키마를 변경하지 않습니다.** ERD 메타데이터(`ERD_*` 테이블)와 DDL 텍스트 산출물만 다룹니다. 생성된 DDL은 파일로만 저장되며, 적용은 사용자가 수동으로 처리합니다.

> 이 스킬은 플러그인으로 배포됩니다. 본문·스크립트 파일은 설치 시 캐시 경로로 복사되며, 스킬 내부에서는 `${CLAUDE_PLUGIN_ROOT}` 로 참조합니다.

---

## 사전 요구사항

| 항목 | 요구 |
|------|------|
| Claude Code | 설치 및 정상 동작 |
| 셸 | bash / zsh |
| Python | 3.8+ — `ddl_export.py` DDL 생성 스크립트용 |
| Python 패키지 | `requests>=2.28` — DDL 생성 시 필요 (아래 설정 참고) |
| BlogN 계정 | https://accounts.softn.kr 가입 + PAT 발급 권한 |
| PAT 스코프 | `erd` 포함 필수 (없으면 401/403) |

---

## 설치 — 플러그인 마켓플레이스

```bash
# 1) 마켓플레이스 추가 (1회)
/plugin marketplace add https://github.com/DoYeong-Seo/softn-claude-plugins.git

# 2) erd-design 플러그인 설치
/plugin install erd-design@softn-tools
```

설치 후 스킬은 **네임스페이스가 붙어** 노출됩니다: `/erd-design:erd-design`.

### 온보딩 자동화 (선택)

프로젝트 `.claude/settings.json` 에 등록해 두면 폴더 신뢰 시 자동 설치됩니다.

```json
{
  "extraKnownMarketplaces": {
    "softn-tools": {
      "source": { "source": "git", "url": "https://github.com/DoYeong-Seo/softn-claude-plugins.git" }
    }
  },
  "enabledPlugins": ["erd-design@softn-tools"]
}
```

### 업데이트 / 제거

```bash
/plugin marketplace update softn-tools     # 최신본 받기 (plugin.json version 기준)
/plugin uninstall erd-design@softn-tools   # 제거
```

---

## 설정

### 1) PAT 토큰 환경변수 (필수)

발급: `https://back.softn.kr` → 마이페이지 → PAT 발급 (스코프에 **`erd`** 체크)

```bash
# ~/.bashrc 또는 ~/.profile 에 추가 (export 키워드 필수)
export BLOGN_PAT_TOKEN="softn_pat_xxxxxxxxxxxxxxxxxxxxxxxxx"
```

적용 후 `source ~/.bashrc` 또는 새 터미널.

> `~/.bashrc` 에 두면 비대화형 셸(Claude Code Bash 툴 포함)에서 로드되지 않을 수 있으니, 전파가 필요하면 `~/.profile` 권장.

### 2) 대상 ERD 프로젝트 — `project.json` (프로젝트별 / 사용자별)

대상 ERD 프로젝트(`projectId`)는 **설정 파일**에서 읽습니다. 스킬 본문에 projectId를 하드코딩하지 않으므로, **프로젝트마다·사용자마다 다른 ERD 프로젝트**를 쓸 수 있습니다. 이 파일은 특정 projectId를 담으므로 **플러그인에 번들되지 않으며 사용자가 직접 생성**합니다. 스킬은 다음 **순서**로 찾아 첫 번째 발견값을 사용합니다:

1. `<현재 작업 디렉토리>/.claude/skills/erd-design/project.json` — **프로젝트별 설정** (해당 프로젝트에서만, 최우선)
2. `~/.claude/skills/erd-design/project.json` — **사용자 전역 설정** (프로젝트 설정이 없을 때 fallback)

형식 (`projectId`만 필수 — 번들된 [`project.example.json`](project.example.json) 참고):

| 필드 | 필수 | 설명 |
|------|------|------|
| `projectId` | ✅ | 대상 ERD 프로젝트 UUID |
| `projectName` | ⬜ | 표시명 (안내 메시지용) |
| `targetDbms` | ⬜ | DDL 생성 기본 엔진 (미지정 시 MySQL) |

```bash
# 프로젝트 로컬 설정 — 예시 템플릿을 복사해 값만 채우기
mkdir -p .claude/skills/erd-design
cp "${CLAUDE_PLUGIN_ROOT}/skills/erd-design/project.example.json" \
   .claude/skills/erd-design/project.json
# 또는 직접 작성
cat > .claude/skills/erd-design/project.json <<'EOF'
{
  "projectId": "16f77e95-47f6-42e8-908a-50dc342aacdd",
  "projectName": "소프트앤 BLOGN",
  "targetDbms": "MySQL"
}
EOF
```

> 사용자 전역 기본 프로젝트가 필요하면 같은 파일을 `~/.claude/skills/erd-design/project.json` 에 둡니다. 프로젝트 설정이 있으면 항상 그쪽이 우선합니다.

`projectId`를 모르면 토큰 설정 후 프로젝트 목록을 확인:
```bash
curl -sS "https://back.softn.kr/api/v1/erd/project/list" \
  -H "Authorization: Bearer ${BLOGN_PAT_TOKEN}" | jq '.data[] | {projectId, projectName}'
```

### 3) DDL 생성 의존성 (DDL export 사용 시에만)

`ddl_export.py` 는 `requests` 패키지가 필요합니다.

```bash
pip3 install -r "${CLAUDE_PLUGIN_ROOT}/skills/erd-design/requirements.txt"
```

DDL은 명령을 실행한 **프로젝트 cwd 기준** `temp/erd-export/<id>/ddl.sql` 로 저장되며, **DB에 자동 실행되지 않습니다.** 자세한 옵션은 [DDL_EXPORT.md](DDL_EXPORT.md) 참고.

---

## 동작 확인

설치 후 Claude Code를 새 세션으로 시작하고 입력합니다:

```
/erd-design:erd-design
```

또는 자연어로:
```
내 ERD 프로젝트 목록 보여줘
```

기대 동작:
- 기본 프로젝트가 설정돼 있으면 "기본 프로젝트 `<projectName>`을 사용합니다." 안내 후 GET 호출
- 미설정 시 `GET /api/v1/erd/project/list`로 후보를 좁히거나 사용자 확인 요청

플러그인 설치/활성화 확인:
```bash
/plugin    # 등록 상태 확인 (erd-design:erd-design 노출)
```

---

## 구성 파일

플러그인 패키지(`plugins/erd-design/skills/erd-design/`)에 포함되는 파일:

```
skills/erd-design/
├── SKILL.md             # 스킬 진입점 (메타데이터 frontmatter + 동작 규칙)
├── NAMING.md            # 테이블·컬럼 명명 워크플로우 (용어사전·도메인) — 생성·수정 시 필수
├── CONVENTIONS.md       # ERD 도메인 컨벤션 (논리명 마커, 감사 컬럼 예외, i18n 키)
├── ENDPOINTS.md         # 전체 REST API 엔드포인트 카탈로그 + 자연어 매핑
├── DDL_EXPORT.md        # DDL 추출 절차·옵션
├── EXAMPLES.md          # 자연어 입력별 처리 흐름 예시
├── README.md            # 본 문서
├── ddl_export.py        # DDL 생성 스크립트
├── requirements.txt     # ddl_export.py 의존성 (requests)
└── project.example.json # 대상 ERD 프로젝트 설정 템플릿 (복사해서 project.json 으로 사용)
```

| 항목 | 위치 | 머신/프로젝트마다 다름 |
|------|------|------------------------|
| 본문·스크립트 파일 | 플러그인 캐시 (`${CLAUDE_PLUGIN_ROOT}/skills/erd-design/`) | ❌ 마켓플레이스가 관리 |
| `BLOGN_PAT_TOKEN` | 환경변수 | ✅ 사용자별 |
| `project.json` | 프로젝트/홈 `.claude/skills/erd-design/` | ✅ 사용자별, 플러그인 미번들 |

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 스킬이 목록에 안 보임 | 마켓플레이스 미추가 / 플러그인 미설치 / 세션이 설치 전 시작됨 | `/plugin` 으로 설치 상태 확인 후 세션 재시작 |
| `BLOGN_PAT_TOKEN 환경변수가 설정되지 않았습니다` | `export` 안 됨 / 셸 재로드 안 됨 | `source ~/.profile` 또는 새 터미널 |
| HTTP 401 | 토큰 만료/오타 | https://back.softn.kr 마이페이지에서 재발급 |
| HTTP 403 | PAT 스코프에 `erd` 없음 / 역할 권한(VIEWER/EDITOR/ADMIN) 부족 | 스코프 확인 후 재발급, 또는 프로젝트 역할 확인 |
| HTTP 409 | Optimistic Lock 충돌 (`lockTimestamp` 불일치) | 최신 GET으로 lockTimestamp 다시 받아 재시도 (스킬이 자동 처리) |
| `ModuleNotFoundError: No module named 'requests'` | DDL 의존성 미설치 | `pip3 install -r "${CLAUDE_PLUGIN_ROOT}/skills/erd-design/requirements.txt"` |
| 잘못된 ERD 프로젝트가 기본으로 잡힘 | 전역/프로젝트 `project.json` 우선순위 충돌 | 프로젝트 `project.json`이 전역보다 우선 — 의도와 다르면 프로젝트 파일 수정/삭제 |
| 응답 없이 멈춤 | 백엔드(`back.softn.kr`) 네트워크 차단 | 사내 방화벽/프록시 점검 |

---

## 보안 주의사항

- **실제 DB 스키마를 변경하지 않습니다.** `CREATE/ALTER/DROP/TRUNCATE/RENAME` 을 DB에 실행하지 않으며, ERD 메타데이터 조작은 REST API로만 수행합니다. DDL은 파일로만 저장됩니다.
- **PAT 토큰을 코드/리포지토리에 커밋하지 마세요.** `BLOGN_PAT_TOKEN`은 `~/.profile`/`~/.bashrc` 등 셸 초기화 파일에만 두세요.
- **`project.json`은 `projectId` 등만 담습니다 — 토큰을 절대 넣지 마세요.** 팀과 같은 ERD 프로젝트를 공유하지 않으면 `.gitignore`에 추가하세요.
- DELETE 호출은 스킬이 항상 cascade 영향 범위를 알리고 사용자 확인을 먼저 받습니다.

---

## 참고

- [SKILL.md](SKILL.md) — 스킬 진입점, 동작 규칙, 안전 체크리스트
- [NAMING.md](NAMING.md) — 테이블·컬럼 명명 워크플로우 (생성·수정 시 필수)
- [CONVENTIONS.md](CONVENTIONS.md) — ERD 도메인 컨벤션
- [ENDPOINTS.md](ENDPOINTS.md) — 전체 엔드포인트 카탈로그
- [DDL_EXPORT.md](DDL_EXPORT.md) — DDL 추출 절차·옵션
- [EXAMPLES.md](EXAMPLES.md) — 자연어 입력별 처리 흐름 예시
