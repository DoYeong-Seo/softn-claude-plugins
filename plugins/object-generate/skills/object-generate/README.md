# object-generate

Claude Code 플러그인 스킬 — MySQL 테이블로부터 기본 Java 객체(VO, EVO, DAO, Service)와 MyBatis SQL 매핑을 자동 생성합니다. 전자정부프레임워크(eGov 5.0.0 / Spring Boot 3.5 / Jakarta EE 10) + MyBatis 구조를 따릅니다.

- **배포**: `softn-tools` 마켓플레이스의 `object-generate` 플러그인 ([softn-claude-plugins](https://github.com/DoYeong-Seo/softn-claude-plugins))
- **베이스 패키지·DB 접속**: 프로젝트별 설정 파일(`project.json`)에서 읽음 — 하드코딩 없음

> 이 스킬은 플러그인으로 배포됩니다. 스크립트는 설치 시 캐시 경로로 복사되며 `${CLAUDE_PLUGIN_ROOT}/skills/object-generate/` 로 참조합니다. 산출물은 명령을 실행한 프로젝트 cwd 의 `temp/`(또는 `--output-dir`)에 생성됩니다.

---

## 사전 요구사항

| 항목 | 요구 |
|------|------|
| Claude Code | 설치 및 정상 동작 |
| Python | 3.8+ |
| Python 패키지 | `mysql-connector-python>=8.0.0` (아래 설정 참고) |
| MySQL 접속 | 대상 DB 호스트/사용자/비밀번호/DB명 |

---

## 설치 — 플러그인 마켓플레이스

```bash
# 1) 마켓플레이스 추가 (1회)
/plugin marketplace add https://github.com/DoYeong-Seo/softn-claude-plugins.git

# 2) object-generate 플러그인 설치
/plugin install object-generate@softn-tools
```

설치 후 스킬은 **네임스페이스가 붙어** 노출됩니다: `/object-generate:object-generate`.

### 온보딩 자동화 (선택)

```json
{
  "extraKnownMarketplaces": {
    "softn-tools": {
      "source": { "source": "git", "url": "https://github.com/DoYeong-Seo/softn-claude-plugins.git" }
    }
  },
  "enabledPlugins": ["object-generate@softn-tools"]
}
```

### 업데이트 / 제거

```bash
/plugin marketplace update softn-tools          # 최신본 받기
/plugin uninstall object-generate@softn-tools   # 제거
```

---

## 설정

### 1) DB 비밀번호 환경변수 (필수)

비밀번호는 **설정 파일에 넣지 않고 환경변수로만** 둡니다.

```bash
# ~/.bashrc 또는 ~/.profile (export 키워드 필수)
export MYSQL_PASSWORD="********"
```

### 2) 베이스 패키지 · DB 접속 — `project.json` (프로젝트별 / 사용자별)

베이스 패키지(`basePackage`)와 DB 접속(비밀번호 제외)은 **설정 파일**에서 읽습니다. 스크립트에 하드코딩하지 않으므로 **프로젝트마다·사용자마다 다른 패키지/DB**를 쓸 수 있습니다. 이 파일은 플러그인에 번들되지 않으며 사용자가 직접 생성합니다. 스킬은 다음 **순서**로 찾습니다:

1. `<현재 작업 디렉토리>/.claude/skills/object-generate/project.json` — **프로젝트별** (최우선)
2. `~/.claude/skills/object-generate/project.json` — **사용자 전역** (fallback)

형식 (번들된 [`project.example.json`](project.example.json) 참고):

| 필드 | 필수 | 설명 |
|------|------|------|
| `basePackage` | ✅ | 생성 코드의 베이스 패키지 (예: `com.softn.blogn`). 이 값으로 패키지 전체가 바뀝니다. |
| `mysql.host` / `mysql.user` / `mysql.database` | ✅ | DB 접속 (비밀번호 제외) |
| `outputDir` | ⬜ | 출력 디렉토리 (기본 `temp`) |

```bash
# 프로젝트 로컬 설정 — 예시 템플릿 복사 후 값 채우기
mkdir -p .claude/skills/object-generate
cp "${CLAUDE_PLUGIN_ROOT}/skills/object-generate/project.example.json" \
   .claude/skills/object-generate/project.json
# 또는 직접 작성
cat > .claude/skills/object-generate/project.json <<'EOF'
{
  "basePackage": "com.softn.blogn",
  "mysql": {
    "host": "your-mysql-host",
    "user": "your-db-user",
    "database": "your_database"
  },
  "outputDir": "temp"
}
EOF
```

> 사용자 전역 기본값이 필요하면 같은 파일을 `~/.claude/skills/object-generate/project.json` 에 둡니다. 프로젝트 설정이 항상 우선합니다.

### 3) 의존성 설치 (1회)

```bash
pip3 install -r "${CLAUDE_PLUGIN_ROOT}/skills/object-generate/requirements.txt"
```

---

## 사용

설치 후 자연어로 요청하면 스킬이 활성화됩니다:

```
quz_show 테이블로 Java 객체 만들어줘
pbd_board, pbd_board_comment 테이블 코드 생성해줘
```

스킬이 `project.json`에서 `basePackage`·`mysql.*`을 읽어 다음과 동등하게 실행합니다 (프로젝트 cwd 기준):

```bash
export MYSQL_HOST=... MYSQL_USER=... BLOGN_DATABASE=...   # project.json 에서
python3 "${CLAUDE_PLUGIN_ROOT}/skills/object-generate/generate_code.py" \
  quz_show quz_quiz --package "com.softn.blogn"
```

옵션:

| 옵션 | 설명 |
|------|------|
| `--package <pkg>` | 베이스 패키지 (설정값보다 우선; 생략 시 `BLOGN_BASE_PACKAGE` env → `com.softn.blogn`) |
| `--output-dir <path>` | 출력 디렉토리 (기본 `temp`) |
| `--no-clean` | 출력 디렉토리를 비우지 않고 누적 생성 |

생성 결과는 `temp/`에 만들어지며, 다음 단계(소스 트리로 복사 → mybatis-config 등록 → 컴파일)는 사용자가 진행합니다.

---

## 구성 파일

```
skills/object-generate/
├── SKILL.md             # 스킬 진입점 (동작 규칙)
├── README.md            # 본 문서
├── generate_code.py     # 코드 생성 스크립트 (--package 로 베이스 패키지 지정)
├── requirements.txt     # 의존성 (mysql-connector-python)
└── project.example.json # 베이스 패키지·DB 설정 템플릿 (복사해서 project.json 으로 사용)
```

| 항목 | 위치 | 머신/프로젝트마다 다름 |
|------|------|------------------------|
| 스크립트·본문 | 플러그인 캐시 (`${CLAUDE_PLUGIN_ROOT}/skills/object-generate/`) | ❌ 마켓플레이스가 관리 |
| `MYSQL_PASSWORD` | 환경변수 | ✅ 사용자별 (비밀, 절대 커밋 금지) |
| `project.json` | 프로젝트/홈 `.claude/skills/object-generate/` | ✅ 사용자별, 플러그인 미번들 |

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 스킬이 목록에 안 보임 | 마켓플레이스 미추가 / 미설치 / 세션이 설치 전 시작 | `/plugin` 확인 후 세션 재시작 |
| `ModuleNotFoundError: mysql.connector` | 의존성 미설치 | `pip3 install -r "${CLAUDE_PLUGIN_ROOT}/skills/object-generate/requirements.txt"` |
| MySQL 연결 실패 | `MYSQL_HOST/USER/PASSWORD/BLOGN_DATABASE` 미설정/오류 | `project.json` mysql 값 + `MYSQL_PASSWORD` env 확인, 네트워크/서버 점검 |
| 잘못된 패키지로 생성됨 | `--package`/`basePackage` 미지정 → 기본값(`com.softn.blogn`) 사용 | `project.json` 의 `basePackage` 확인, 또는 `--package` 명시 |
| 테이블을 찾을 수 없음 | 철자/형식 오류 | 소문자, `{module}_{entity}` 형식(예 `quz_show`) 확인 |
| 출력이 안 보임 | cwd 가 프로젝트 루트가 아님 | 프로젝트 루트에서 실행 (산출물은 cwd 의 `temp/`) |

---

## 보안 주의사항

- **DB 비밀번호를 설정 파일·코드·리포지토리에 넣지 마세요.** `MYSQL_PASSWORD` 환경변수로만 주입합니다. (스크립트는 접속 정보 기본값을 비워 두며, env 가 없으면 연결 실패합니다.)
- **`project.json` 에는 호스트/사용자/DB명만** 두고, 팀과 공유하지 않는다면 `.gitignore` 에 추가하세요. (마켓플레이스 레포 기준 `project.json` 은 기본 ignore)
- 생성 코드는 기본 템플릿입니다. 적용 전 비즈니스 로직·보안 관점에서 검토하세요.

---

## 참고

- [SKILL.md](SKILL.md) — 스킬 진입점, 실행 절차, 옵션
- [generate_code.py](generate_code.py) — 코드 생성 스크립트
- 생성 코드는 BlogN 전자정부프레임워크 구조를 따릅니다. 대상 프로젝트의 `CLAUDE.md` "아키텍처" 섹션도 참고하세요.
