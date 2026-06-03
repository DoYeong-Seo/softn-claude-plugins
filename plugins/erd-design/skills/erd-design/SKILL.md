---
name: erd-design
description: BlogN ERD 설계 도구의 REST API를 자연어로 호출하여 ERD 프로젝트/다이어그램/테이블/컬럼/관계/인덱스 등의 메타데이터를 관리하고, ERD 정의로부터 MySQL DDL 스크립트를 생성합니다. PAT(Personal Access Token) 인증 사용. 실제 MySQL DB 스키마는 절대 변경하지 않으며, ERD 메타데이터(`ERD_*` 테이블)와 DDL 텍스트 산출물만 다룹니다.
allowed-tools: Read, Bash, Write, Grep, AskUserQuestion
---

# ERD Design

BlogN ERD 백엔드(`api.v1.controller.erd.*`)를 자연어 명령으로 조작하는 스킬. 세부 절차는 참조 문서로 위임한다.

## 핵심 원칙 — 절대 위반 금지

1. **실제 MySQL DB 스키마를 변경하지 않는다.** `mcp__mysql__mysql_query`, `mvn`, `mysql -e ...` 등으로 `CREATE/ALTER/DROP/TRUNCATE/RENAME TABLE` 절대 실행 금지. 생성된 DDL은 파일로만 저장, 실행은 사용자가 수동 처리.
2. **ERD 메타데이터(`ERD_*` 테이블)는 반드시 REST API를 통해서만 조작한다.** 직접 SQL UPDATE/INSERT/DELETE 금지.
3. **삭제(DELETE) 호출은 반드시 사용자 확인 후 실행한다.** "삭제"·"제거"·"지워"가 포함되면 cascade 영향 범위를 먼저 알리고 동의 후 호출.
4. **수정(PUT) 호출은 변경 요약을 먼저 보여주고 진행한다.** 단순 좌표 이동(`tableCoordinates`)·이름 변경 등 자명한 경우는 즉시 실행 가능.
5. **테이블·컬럼의 생성·수정은 [NAMING.md](NAMING.md) 워크플로우를 반드시 따른다** — 용어사전·도메인 사용자 확인 필수.

## 환경 설정

| 항목 | 값 |
|------|-----|
| Base URL | `https://back.softn.kr` (하드코딩) |
| 인증 헤더 | `Authorization: Bearer ${BLOGN_PAT_TOKEN}` |
| 토큰 prefix | `softn_pat_` |
| 필수 scope | `erd` |

토큰은 `BLOGN_PAT_TOKEN` 환경변수에서 읽는다. 없으면 다음을 안내 후 작업 중단:

```
BLOGN_PAT_TOKEN 환경변수가 설정되지 않았습니다.
- 토큰 발급: https://back.softn.kr → 마이페이지 → PAT 발급 (scope에 'erd' 포함)
- 설정: export BLOGN_PAT_TOKEN="softn_pat_xxxxxxxx..."
```

## 기본 ERD 프로젝트

대상 ERD 프로젝트(`projectId`)는 **설정 파일**에서 읽는다. 스킬 본문에 projectId를 하드코딩하지 않으므로, **프로젝트마다·사용자마다 다른 ERD 프로젝트**를 쓸 수 있다. 입력에 프로젝트가 명시되지 않으면 다음 **순서대로** 설정 파일을 찾아 첫 번째로 발견된 값을 기본 대상으로 사용한다.

1. `<현재 작업 디렉토리>/.claude/skills/erd-design/project.json` — **프로젝트별 설정** (해당 프로젝트에서만 적용, 최우선)
2. `~/.claude/skills/erd-design/project.json` — **사용자 전역 설정** (프로젝트 설정이 없을 때 fallback)

설정 파일은 특정 projectId를 담으므로 플러그인에 번들되지 않으며, 사용자가 직접 생성한다. 형식·예시는 플러그인의 [`project.example.json`](project.example.json) 참고.

```json
{
  "projectId": "<UUID — 필수>",
  "projectName": "<프로젝트 표시명 — 선택, 안내 메시지용>",
  "targetDbms": "MySQL"
}
```

적용 규칙:
- `projectId`만 필수. `projectName`은 안내용, `targetDbms`는 DDL 생성 기본 엔진(미지정 시 MySQL).
- **프로젝트 설정(1)이 있으면 전역 설정(2)보다 항상 우선**한다. (같은 머신에서 프로젝트마다 다른 ERD, 사용자마다 다른 전역 기본값 공존 가능.)
- 입력에 다른 프로젝트가 명시되면(이름·ID 매칭) 설정 파일보다 입력값 우선.
- 첫 호출 직전 "기본 프로젝트 `<projectName 또는 projectId>`을 사용합니다." 1회 안내.
- 두 파일 모두 없거나 `projectId`가 비어 있으면 아래 [프로젝트 설정 부트스트랩](#프로젝트-설정-부트스트랩--파일이-없을-때-생성-유도)으로 진입한다.
- "프로젝트 목록", "내 ERD 전부" 처럼 명확히 전체를 가리키면 기본값 비적용.

### 프로젝트 설정 부트스트랩 — 파일이 없을 때 생성 유도

프로젝트별 설정(`<현재 작업 디렉토리>/.claude/skills/erd-design/project.json`)이 없으면, **이 프로젝트 폴더에 설정 파일을 만들도록 1회 유도**한다. 같은 머신의 다른 프로젝트와 ERD가 섞이지 않게 하기 위함이다.

**언제 유도하는가 (트리거 시점):**
- **projectId가 필요한 첫 작업 직전에만** 유도한다 — 테이블/컬럼/관계/인덱스/다이어그램 조회·생성·수정·삭제, DDL 생성 등 특정 프로젝트를 대상으로 하는 작업.
- 자연어 입력에 프로젝트(이름·ID)가 명시돼 있으면 그 입력을 우선 적용하되, 작업 종료 후 "이 프로젝트를 설정으로 저장해 둘까요?"를 가볍게 덧붙일 수 있다.
- **세션당 1회**. 사용자가 한 번 거절하면 이 대화에서는 다시 묻지 않고, 전역 설정(2) 또는 목록 선택으로 계속 진행한다.

**유도 절차:**
1. **안내 한 줄** — "이 프로젝트에는 erd-design 설정(`./.claude/skills/erd-design/project.json`)이 없습니다. 기본 ERD 프로젝트를 정해 두면 이후 호출이 간편합니다. 지금 만들까요?"
2. **동의하면 대상 프로젝트 확정** — `GET /api/v1/erd/project/list`(PAT 필수)로 ERD 프로젝트 목록을 받아 후보를 제시하고, 모호하면 사용자에게 하나를 고르게 한다. (자연어에 이미 프로젝트가 지정됐으면 그것으로 확정.)
3. **`Write` 도구로 파일 생성** — 경로 `<현재 작업 디렉토리>/.claude/skills/erd-design/project.json`. 상위 디렉토리가 없으면 함께 만든다. 내용은 확정한 `projectId`(필수)와 선택 필드(`projectName`/`targetDbms`)만 채운다. `targetDbms`는 사용자가 말하지 않으면 `MySQL`로 둔다.
   ```json
   {
     "projectId": "<확정한 UUID>",
     "projectName": "<선택>",
     "targetDbms": "MySQL"
   }
   ```
4. **생성 보고** — "프로젝트 설정을 저장했습니다: `./.claude/skills/erd-design/project.json` (`<projectName 또는 projectId>`)." 안내 후 원래 요청한 작업을 이어서 진행한다.
5. **거절 시** — 파일을 만들지 않고, 전역 설정(`~/.claude/skills/erd-design/project.json`)이 있으면 그것을, 없으면 목록에서 고른 projectId를 **이번 작업에만** 적용한다. (다음 호출에서 다시 묻지 않음.)

> 형식·예시 필드는 플러그인의 [`project.example.json`](project.example.json) 참고. 이 파일은 특정 projectId를 담으므로 커밋 대상에서 제외하거나 `.gitignore`에 추가하도록 안내할 수 있다.

## 프로젝트 컨벤션

ERD 설계 검토·DDL 생성 시 **반드시 [CONVENTIONS.md](CONVENTIONS.md) 우선 참조**. 일반 DBA 권고와 충돌하면 컨벤션이 우선.

요지(자세한 내용은 CONVENTIONS.md):
- 논리명의 `[...]`(업무영역)·끝의 `]`(약어) 는 의도된 마커 — 오타 아님.
- 종속 테이블(`LABS_POLL_OPTION` 등)의 감사 컬럼 생략 허용 케이스 있음.
- `*_NAME_KEY` 는 i18n 메시지 키 — UNIQUE 강제 금지.

## 명명 워크플로우 — 용어사전·도메인 통합

테이블·컬럼의 **생성·수정 의도가 감지되면 무조건** [NAMING.md](NAMING.md) 절차를 따른다. 모델이 임의로 `physicalName`을 만들거나 도메인을 선택하지 않는다.

핵심 3원칙 (상세는 NAMING.md):
1. `physicalName`은 용어사전(Glossary) 매핑으로만 조립 — 임의 축약·번역 금지.
2. 사전에 없는 용어는 `AskUserQuestion` 으로 **사용자 동의 후에만** 등록.
3. 컬럼은 `domainId` 필수 — 후보 추천 후 **사용자가 직접 선택** (없음 선택지 포함).

절차 요약: ① 논리명 분해 → ② 사전 조회·누락 등록 동의 → ③ 물리명 조립 → ④ 도메인 후보 사용자 선택 → ⑤ 최종 요약 후 API 호출.

## 작동 방식

### 자연어 → 의도 분류

| 의도 | 동작 |
|------|------|
| **조회(read)** | GET 호출 → 정리해서 답변 |
| **생성(create)** | 테이블/컬럼이면 **NAMING.md 필수** → POST |
| **수정(update)** | 명명 변경/추가 포함이면 **NAMING.md 필수** → 요약 → PUT/POST |
| **삭제(delete)** | cascade 영향 보고 → 사용자 확인 → DELETE |
| **DDL export** | [DDL_EXPORT.md](DDL_EXPORT.md) 참조 |

엔드포인트 카탈로그·자연어 매핑 힌트는 [ENDPOINTS.md](ENDPOINTS.md) 참조.

### HTTP 호출 패턴

```bash
curl -sS -X GET "https://back.softn.kr/api/v1/erd/project/list" \
  -H "Authorization: Bearer ${BLOGN_PAT_TOKEN}" \
  -H "Accept: application/json"
```

응답은 항상 다음 래핑:
```json
{ "success": true|false, "message": "...", "data": ..., "errorCode": "..." }
```

`success=false` 또는 HTTP 4xx/5xx → 에러 처리 표 참조.

## 안전 규칙 체크리스트

매 호출 직전 확인:

- [ ] `BLOGN_PAT_TOKEN` 설정?
- [ ] 호출 대상이 ERD 메타데이터 API(`/api/v1/erd/...`)인가?
- [ ] DELETE 호출이면 사용자 확인 받았는가?
- [ ] 테이블·컬럼 명명 변경이면 NAMING.md 워크플로우 완료했는가?
- [ ] 응답 `success=true`인가? 실패면 메시지·errorCode 그대로 전달?
- [ ] (DDL export) 생성 파일이 `temp/` 하위이며 자동 실행되지 않았는가?

## 에러 처리

| HTTP | 의미 | 대응 |
|------|------|------|
| 401 | 토큰 만료/잘못됨 | PAT 재발급 안내 |
| 403 | 권한 부족 | 필요한 역할(VIEWER/EDITOR/ADMIN) 안내 |
| 404 | 리소스 없음 | ID/이름 재확인 요청 |
| 409 | Optimistic Lock 충돌 (`lockTimestamp` 불일치) | 최신 GET → lockTimestamp 갱신 후 재시도 |
| 5xx | 서버 오류 | `errorCode`/`message` 그대로 전달, 재시도 1회 |

## 누락 정보 처리

- **projectId/diagramId/tableId 누락**: 최근 조회 결과 또는 list API로 좁힌 뒤, 모호하면 사용자 확인.
- **lockTimestamp 필요 PUT/DELETE**: 호출 직전 GET으로 최신값 fetch → body에 포함.
- **컬럼 `displayOrder` 미명시**: 기존 컬럼 수 + 1부터 자동 부여.

## 자연어 처리 흐름 예시

구체적 흐름(테이블 추가, FK 연결, DDL 추출, 삭제 등 6가지)은 [EXAMPLES.md](EXAMPLES.md) 참조.

## 참고 파일

- [CONVENTIONS.md](CONVENTIONS.md) — ERD 도메인 컨벤션 (논리명 마커, 감사 컬럼 예외, i18n 키) — **검토 시 우선 참조**
- [NAMING.md](NAMING.md) — 테이블·컬럼 명명 워크플로우 (용어사전·도메인) — **생성·수정 시 필수**
- [ENDPOINTS.md](ENDPOINTS.md) — 전체 엔드포인트 카탈로그 + 자연어 매핑 힌트
- [DDL_EXPORT.md](DDL_EXPORT.md) — DDL 추출 절차·옵션
- [EXAMPLES.md](EXAMPLES.md) — 자연어 입력별 처리 흐름 예시
- [ddl_export.py](ddl_export.py) — DDL 생성 스크립트
- 컨트롤러 원본: `src/main/java/com/softn/blogn/api/v1/controller/erd/`
