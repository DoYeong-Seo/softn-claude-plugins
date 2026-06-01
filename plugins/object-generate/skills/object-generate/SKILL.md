---
name: object-generate
description: MySQL 테이블로부터 기본 Java 객체(VO, EVO, DAO, Service, MyBatis SQL 매핑)를 자동 생성합니다. 테이블 기반 코드 생성, CRUD 보일러플레이트 자동화 시 사용합니다. 전자정부프레임워크(eGov) + MyBatis 구조를 따르며, 베이스 패키지·DB 접속은 프로젝트별 설정 파일에서 읽습니다.
allowed-tools: Read, Bash, Write
---

# Object Generate

MySQL 테이블로부터 기본 Java 객체(VO, EVO, DAO, Service)와 MyBatis SQL 매핑을 자동 생성하는 스킬입니다. `generate_code.py` 스크립트를 실행해 처리합니다.

> 이 스킬은 플러그인으로 배포됩니다. 스크립트(`generate_code.py`)는 설치 시 캐시 경로로 복사되며, `${CLAUDE_PLUGIN_ROOT}/skills/object-generate/` 로 참조합니다. 생성 산출물은 명령을 실행한 **프로젝트 cwd 기준** `temp/`(또는 `--output-dir`)에 만들어집니다.

## 핵심 원칙

1. **베이스 패키지·DB 접속 정보를 스킬/스크립트에 하드코딩하지 않는다.** 프로젝트별 설정 파일(`project.json`)에서 읽어 `--package` 인자와 환경변수로 전달한다.
2. **DB 비밀번호는 환경변수(`MYSQL_PASSWORD`)로만 주입한다.** 설정 파일·코드·로그에 평문으로 남기지 않는다.
3. **출력 디렉토리는 기본적으로 실행 직전 비워진다.** 보존이 필요하면 `--no-clean`.
4. **생성 코드는 기본 템플릿이다.** 비즈니스 로직은 사용자가 검토·수정해야 한다.

## 프로젝트/사용자 설정 — `project.json`

베이스 패키지와 DB 접속(비밀번호 제외)은 **설정 파일**에서 읽는다. **프로젝트마다·사용자마다 다른 패키지/DB**를 쓸 수 있다. 다음 **순서**로 찾아 첫 번째 발견값을 사용한다:

1. `<현재 작업 디렉토리>/.claude/skills/object-generate/project.json` — **프로젝트별 설정** (최우선)
2. `~/.claude/skills/object-generate/project.json` — **사용자 전역 설정** (fallback)

설정 파일은 플러그인에 번들되지 않으며 사용자가 직접 생성한다. 형식·예시는 플러그인의 [`project.example.json`](project.example.json) 참고.

```json
{
  "basePackage": "com.softn.blogn",
  "mysql": {
    "host": "<MySQL 호스트>",
    "user": "<MySQL 사용자>",
    "database": "<데이터베이스명>"
  },
  "outputDir": "temp"
}
```

| 필드 | 필수 | 설명 |
|------|------|------|
| `basePackage` | ✅ | 생성 코드의 베이스 패키지 (예: `com.softn.blogn`). 이 값으로 패키지 전체가 바뀐다. |
| `mysql.host` / `mysql.user` / `mysql.database` | ✅ | DB 접속 정보 (비밀번호 제외) |
| `outputDir` | ⬜ | 출력 디렉토리 (기본 `temp`) |

**비밀번호**는 설정 파일에 넣지 않고 환경변수로 둔다:
```bash
export MYSQL_PASSWORD="********"
```

## 실행 절차

### 1) 의존성 설치 (1회)

```bash
pip3 install -r "${CLAUDE_PLUGIN_ROOT}/skills/object-generate/requirements.txt"
```

### 2) 설정 로드 → 환경변수·인자 구성

`project.json`(프로젝트 → 전역 순)에서 `basePackage`, `mysql.*`, `outputDir`를 읽는다. DB 접속 정보를 환경변수로 전달한다 (비밀번호는 사용자 env에서 그대로 사용):

```bash
export MYSQL_HOST="<project.json mysql.host>"
export MYSQL_USER="<project.json mysql.user>"
export BLOGN_DATABASE="<project.json mysql.database>"
# MYSQL_PASSWORD 는 사용자가 미리 설정한 값을 사용
```
> `project.json`이 없거나 `basePackage`/`mysql`이 비어 있으면 사용자에게 설정 파일 생성을 안내하고 중단한다. (`project.example.json` 복사 안내)

### 3) 스크립트 실행

프로젝트 루트(cwd)에서 실행한다 — 산출물이 해당 프로젝트 `temp/`에 생성된다.

```bash
# 단일 테이블
python3 "${CLAUDE_PLUGIN_ROOT}/skills/object-generate/generate_code.py" quz_show \
  --package "<basePackage>"

# 여러 테이블 (공백 구분)
python3 "${CLAUDE_PLUGIN_ROOT}/skills/object-generate/generate_code.py" quz_show quz_quiz pbd_board \
  --package "<basePackage>"

# 커스텀 출력 디렉토리
python3 "${CLAUDE_PLUGIN_ROOT}/skills/object-generate/generate_code.py" quz_show \
  --package "<basePackage>" --output-dir <outputDir>

# 기존 산출물 보존하며 누적 생성
python3 "${CLAUDE_PLUGIN_ROOT}/skills/object-generate/generate_code.py" quz_show \
  --package "<basePackage>" --no-clean
```
> `--package`를 생략하면 `BLOGN_BASE_PACKAGE` 환경변수, 그것도 없으면 `com.softn.blogn` 기본값이 쓰인다. 설정 파일을 쓰는 경우 항상 `--package`로 명시하는 것을 권장한다.

### 4) 결과 확인 및 리포트

실행 후 성공 여부 / 생성 파일 수 / 출력 위치 / 오류를 사용자에게 보고한다.

```
✓ 3개 테이블 처리 완료 (quz_show, quz_quiz, pbd_board)
✓ 출력 디렉토리: temp/
다음 단계:
1. 생성된 Java 파일을 src/main/java/<basePackage 경로>/ 아래로 복사
2. 생성된 SQL 파일을 src/main/resources/com/sqlmap/mysql/module/ 아래로 복사
3. mybatis-config-snippet.xml 내용을 mybatis-config.xml <mappers> 섹션에 추가
4. mvn clean compile 로 컴파일 확인
```

## 생성되는 파일

각 테이블마다 다음 파일들이 생성된다 (`{module}_{entity}` 형식 테이블명 기준):

```
temp/
├── {module}/service/
│   ├── {Entity}EVO.java              # Extended VO (테이블 컬럼)
│   ├── {Entity}VO.java               # VO (추가 필드용)
│   ├── {Entity}Service.java          # Service 인터페이스
│   └── impl/
│       ├── {Entity}ServiceImpl.java  # Service 구현
│       ├── {Entity}BasicDAO.java     # 기본 CRUD DAO
│       └── {Entity}GeneratedDAO.java # 확장 쿼리 DAO
├── sqlmap/
│   ├── {Entity}BasicDAO_SQL.xml      # CRUD SQL 매핑
│   └── {Entity}GeneratedDAO_SQL.xml  # 목록/카운트 SQL 매핑
└── resources/com/sqlmap/mysql/config/mybatis-config-snippet.xml
```

## 사용 예시 (자동 활성화 트리거)

- "quz_show 테이블로 Java 객체 만들어줘"
- "pbd_board, pbd_board_comment 테이블 코드 생성해줘"
- "object generate 실행해줘 - quz_quiz 테이블"
- "usr_user 테이블의 VO, DAO, Service 만들어줘"

## 옵션 처리 가이드

| 사용자 요청 키워드 | 스크립트 옵션 |
|---|---|
| "다른 패키지로" / 특정 패키지 지정 | `--package <pkg>` (설정값보다 우선) |
| "temp가 아니라 다른 곳에" | `--output-dir <path>` |
| 여러 테이블 나열 | 공백으로 구분 |
| "기존 파일 보존" / "비우지 말고" | `--no-clean` |

## 오류 처리

1. **MySQL 연결 오류**: `MYSQL_HOST/USER/PASSWORD/BLOGN_DATABASE` 환경변수와 네트워크/서버 상태 확인. 설정 파일의 `mysql.*` 값과 비밀번호 env가 맞는지 점검.
2. **`mysql.connector` 미설치**: `pip3 install -r "${CLAUDE_PLUGIN_ROOT}/skills/object-generate/requirements.txt"` 안내.
3. **테이블을 찾을 수 없음**: 테이블명 철자(소문자), `{module}_{entity}` 형식 확인.
4. **권한 오류**: 출력 디렉토리 쓰기 권한 확인.

## 주의사항

1. **출력 디렉토리 자동 정리**: 기본 동작은 실행 직전 출력 디렉토리 내부를 모두 삭제한다. 보존하려면 `--no-clean`.
2. **리뷰 필요**: 생성 코드는 기본 템플릿. 비즈니스 로직에 맞게 수정.
3. **Primary Key**: PK 없는 테이블은 첫 번째 컬럼을 PK로 간주.
4. **전자정부프레임워크 5.0.0** (Spring Boot 3.5 / Spring 6.2 / Jakarta EE 10) + MyBatis 3.5+ 구조. ServiceImpl 의 `@Resource` 는 `jakarta.annotation.Resource`.

## 참고

- [README.md](README.md) — 설치/설정/트러블슈팅
- [generate_code.py](generate_code.py) — 코드 생성 스크립트 (`--package`로 베이스 패키지 지정)
- [requirements.txt](requirements.txt) — 의존성 (`mysql-connector-python`)
