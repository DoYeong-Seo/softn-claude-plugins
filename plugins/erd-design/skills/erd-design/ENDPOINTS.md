# ERD API Endpoints

전체 ERD REST API 카탈로그. 모든 엔드포인트는 `Authorization: Bearer ${BLOGN_PAT_TOKEN}` 헤더 필수, scope `erd` 필요.

## 권한 등급

| 등급 | 의미 |
|------|------|
| AUTH | 인증된 사용자(자기 데이터만) |
| VIEWER | 프로젝트 멤버(VIEWER/EDITOR/ADMIN) — 조회 가능 |
| EDITOR | EDITOR/ADMIN — 변경 가능 |
| ADMIN | ADMIN만 |

응답 공통 포맷:
```json
{ "success": true|false, "message": "...", "data": ..., "errorCode": "..." }
```

---

## 1. Project (프로젝트)

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/erd/project/list` | AUTH | 내가 참여한 프로젝트 목록 |
| GET | `/api/v1/erd/project/{projectId}` | VIEWER | 프로젝트 상세 |
| POST | `/api/v1/erd/project` | AUTH | 프로젝트 생성 (생성자 자동 ADMIN) |
| PUT | `/api/v1/erd/project/{projectId}` | ADMIN | 프로젝트 수정 |
| DELETE | `/api/v1/erd/project/{projectId}` | ADMIN | 프로젝트 삭제 (body: `{lockTimestamp}`) |
| GET | `/api/v1/erd/project/{projectId}/config` | VIEWER | 프로젝트 환경설정 조회 |
| PUT | `/api/v1/erd/project/{projectId}/config` | ADMIN | 프로젝트 환경설정 수정 |

**POST body 예:**
```json
{ "projectName": "게시판 ERD", "dbmsType": "mysql", "description": "" }
```
서버 자동 설정: `projectId` (UUID), `userId`, `useStatus="Y"`.

---

## 2. Diagram (다이어그램)

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/erd/project/{projectId}/diagram/list` | VIEWER | 프로젝트의 다이어그램 목록 |
| GET | `/api/v1/erd/diagram/{diagramId}` | VIEWER | 다이어그램 상세 |
| POST | `/api/v1/erd/project/{projectId}/diagram` | EDITOR | 다이어그램 생성 |
| PUT | `/api/v1/erd/diagram/{diagramId}` | EDITOR | 다이어그램 수정 |
| DELETE | `/api/v1/erd/diagram/{diagramId}` | EDITOR | 다이어그램 삭제 |

---

## 3. Table & Column (테이블/컬럼)

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/erd/diagram/{diagramId}/table/list` | VIEWER | 다이어그램의 테이블+컬럼 목록 (한 방에 fetch) |
| GET | `/api/v1/erd/diagram/{diagramId}/table/list/without-columns` | VIEWER | 테이블만 (가벼운 조회) |
| GET | `/api/v1/erd/project/{projectId}/table/list` | VIEWER | 프로젝트 전체 테이블+컬럼 (cross-diagram FK source 검색용, `diagramId`/`diagramName` 포함) |
| POST | `/api/v1/erd/diagram/{diagramId}/table` | EDITOR | 테이블+컬럼 일괄 생성 |
| PUT | `/api/v1/erd/table/{tableId}` | EDITOR | 테이블+컬럼 일괄 수정 (diff 기반) |
| DELETE | `/api/v1/erd/table/{tableId}` | EDITOR | 테이블 cascade 삭제 |
| GET | `/api/v1/erd/table/{tableId}/column/list` | VIEWER | 단일 테이블의 컬럼 목록 |
| POST | `/api/v1/erd/table/{tableId}/column` | EDITOR | 단일 컬럼 추가 |
| PUT | `/api/v1/erd/table/{tableId}/column` | EDITOR | 단일 컬럼 수정 (body의 columnId 기준) |
| DELETE | `/api/v1/erd/table/{tableId}/column/{columnId}` | EDITOR | 단일 컬럼 삭제 |

**Table POST body 예 (columns 포함):**
```json
{
  "logicalName": "공지사항",
  "physicalName": "BBS_NOTICE",
  "tableCoordinates": "{\"x\":100,\"y\":100}",
  "columns": [
    {"columnId":"NOTICE_ID","columnName":"공지사항 아이디","dataType":"BIGINT","primarykeyFlag":1,"notnullFlag":1,"autoIncreaseFlag":1,"displayOrder":1},
    {"columnId":"NOTICE_TITLE","columnName":"공지사항 제목","dataType":"VARCHAR(200)","notnullFlag":1,"displayOrder":2},
    {"columnId":"NOTICE_CONTENT","columnName":"공지사항 내용","dataType":"TEXT","displayOrder":3},
    {"columnId":"REG_DATETIME","columnName":"등록 일시","dataType":"DATETIME","notnullFlag":1,"displayOrder":4}
  ]
}
```

**Column 필드:** (`columnId`/`columnName` 규칙은 [CONVENTIONS.md §4](CONVENTIONS.md) 참조)
- `columnId` (String) — **물리명**(영문 대문자, 예: `NOTICE_ID`). 곧 DB 물리 컬럼명이자 테이블 내 컬럼 식별자. **UUID 금지.**
- `columnName` (String) — **한글 논리명**(용어사전 기반, 예: `공지사항 아이디`).
- `dataType` (String) — 예: `VARCHAR(50)`, `BIGINT`, `DATETIME`, `TEXT`
- `domainId` (String, optional)
- `displayOrder` (Integer)
- `defaultValue` (String, optional)
- `primarykeyFlag` / `foreignkeyFlag` / `notnullFlag` / `autoIncreaseFlag` (Integer 0/1)

**PK 자동 인덱스:** `primarykeyFlag=1` 컬럼이 있으면 PRIMARY 인덱스가 서비스 계층에서 자동 생성됨.

**lockTimestamp 필수 (PUT/DELETE):** 사전 GET으로 최신값 fetch.

---

## 3.1 Table Memo (테이블 메모)

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/erd/table/{tableId}/memo/list` | VIEWER | 테이블 메모 목록 (memoFixFlag DESC, displayOrder ASC) |
| POST | `/api/v1/erd/table/{tableId}/memo` | EDITOR | 메모 추가 (memoId 자동 발급) |
| PUT | `/api/v1/erd/table/{tableId}/memo/{memoId}` | EDITOR | 메모 수정 (lockTimestamp 필수, 부분 갱신 지원) |
| DELETE | `/api/v1/erd/table/{tableId}/memo/{memoId}` | EDITOR | 메모 삭제 (lockTimestamp 필수) |

**Body 필드 (`ErdTableMemoVO`)**:
- `memoContents` (String, POST 필수) — 메모 본문
- `memoFixFlag` (Integer, optional) — 1=고정 메모, 0=일반 (POST 미지정 시 0)
- `displayOrder` (Integer, optional) — 표시 순서 (POST 미지정 시 현재 메모 수로 자동)
- `lockTimestamp` (String, PUT/DELETE 필수) — Optimistic Lock

---

## 4. Relation (테이블 관계) — **폐기됨 (2026-05-07)**

`ErdTableRelation` 은 폐기되었으며 `ErdTableIndex(indexType=FOREIGN)` 가 FK 단일 진실원이 되었습니다. 관련 엔드포인트는 모두 제거됨 (404). FK 생성/수정/삭제는 **5. Index** 의 `indexType=FOREIGN` 인덱스로 처리하세요.

- 부모 테이블 ID: `ErdTableIndex.sourceTableId`
- 부모 컬럼 매핑: `ErdTableIndexColumn.sourceColumnId → columnId`
- FK 액션: `onDeleteAction` / `onUpdateAction` (인덱스 메타)
- 식별 여부: 자식 PRIMARY 인덱스 컬럼 집합 ⊇ FK 컬럼 집합 으로 도출
- 카디널리티: FK 컬럼의 `notnullFlag` + UNIQUE 인덱스 존재 여부로 도출

(폐기된 옛 엔드포인트: `GET/POST/PUT/DELETE /api/v1/erd/.../relation/...`)

---

## 5. Index (인덱스)

### 5.1 기본 CRUD

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/erd/table/{tableId}/index/list` | VIEWER | 인덱스 + indexColumns[] 목록 |
| POST | `/api/v1/erd/table/{tableId}/index` | EDITOR | 인덱스 생성 |
| PUT | `/api/v1/erd/table/{tableId}/index/{indexId}` | EDITOR | 인덱스 수정 |
| DELETE | `/api/v1/erd/table/{tableId}/index/{indexId}` | EDITOR | 인덱스 삭제 |

### 5.2 FK Atomic 전용

| Method | Path | Role | 용도 |
|--------|------|------|------|
| PUT | `/api/v1/erd/table/{tableId}/foreign-index/{indexId}/cardinality` | EDITOR | 카디널리티 atomic 변경 |
| PUT | `/api/v1/erd/table/{tableId}/foreign-index/{indexId}/identifying` | EDITOR | 식별/비식별 atomic 토글 |

**Cardinality body:** `{ "targetCardinality": "one" \| "zero_or_one" \| "zero_or_more" \| "more" }`
- `one` → notnull=1 + UNIQUE 보장 / `zero_or_one` → notnull=0 + UNIQUE 보장
- `more` → notnull=1 + UNIQUE 제거 / `zero_or_more` → notnull=0 + UNIQUE 제거

**Identifying body:** `{ "identifying": true | false }`
- `true` → 자식 PRIMARY 인덱스에 FK 컬럼 추가 + `primarykeyFlag=1` + `notnullFlag=1`
- `false` → PRIMARY 에서 FK 컬럼 제거 + `primarykeyFlag=0` (PK 컬럼 0건이면 PRIMARY 인덱스 자체 삭제)

### 5.3 Index 필드

| 필드 | 비고 |
|---|---|
| `tableId` | 자식 테이블 (복합 PK) |
| `indexId` | **UUID** (전역 unique). 생성 시 새 UUID 를 부여하되 **하이픈(`-`) 제거 후 32자**로 만든다 (예: `550e8400e29b41d4a716446655440000`) — 물리명 기반 조립 금지 |
| `indexName` | 명명 규칙: `{접두}_{TABLE_PHYSICAL}_{연번}` (예: `PK_USER_1`, `FK_ORDER_2`, `UK_USER_3`, `IDX_USER_4`) — [5.6](#56-인덱스-명명-규칙) 참조 |
| `indexType` | `PRIMARY` / `UNIQUE` / `NORMAL` / `FULLTEXT` / `FOREIGN` |
| `sourceTableId` | FK 한정. 부모(참조 대상) 테이블 ID. **cross-diagram 허용**, **cross-project 거부** |
| `onUpdateAction` / `onDeleteAction` | FK 한정. `CASCADE` / `RESTRICT` / `SET_NULL` / `NO_ACTION` |
| `sourcePhysicalName` | 응답 전용. JOIN 산출 |
| `sourceDiagramId` / `sourceDiagramName` | 응답 전용. cross-diagram FK 표시용 |
| `indexColumns[]` | 컬럼 목록 |

### 5.4 IndexColumn 필드

| 필드 | 비고 |
|---|---|
| `tableId`, `indexId`, `columnId` | 복합 PK |
| `sortType` | `ASC` / `DESC` |
| `displayOrder` | 정렬 |
| `sourceColumnId` | FK 한정. 부모 PK 컬럼 ID (export 시 매핑 산출 근거) |

### 5.5 식별 키

`(tableId, indexId)` 복합 PK 입니다. `indexId` 는 하이픈 제거 32자 UUID 라 전역 unique 하지만, 조회 시에는 `(tableId, indexId)` 쌍으로 다룬다.

### 5.6 인덱스 명명 규칙

인덱스를 **생성(POST)** 할 때 `indexId` 와 `indexName` 은 아래 규칙으로 만든다. 임의 작명 금지.

```
indexId    = UUID 하이픈 제거 32자             (예: 550e8400e29b41d4a716446655440000)
indexName  = {접두}_{TABLE_PHYSICAL}_{연번}     (예: PK_USER_1, FK_ORDER_2, UK_USER_3, IDX_USER_4)
```

- **`indexId`** — 새 UUID 를 생성하고 하이픈(`-`)을 제거해 32자로 만든다. 물리명·연번 기반 조립 금지. (예: `uuidgen | tr -d '-' | tr 'A-Z' 'a-z'`)
- **`indexName`** — 아래 `{접두}`·`{연번}` 규칙으로 조립한다.
- `{TABLE_PHYSICAL}` — 대상 테이블의 `physicalName` 그대로.
- `{접두}` — `indexType` 에 따른 약어.

| `indexType` | 접두 | 의미 |
|---|---|---|
| `PRIMARY` | `PK` | 기본키 |
| `FOREIGN` | `FK` | 외래키 |
| `UNIQUE` | `UK` | 유니크 |
| `NORMAL` | `IDX` | 일반 인덱스 |
| `FULLTEXT` | `FT` | 전문 검색 |

**`{연번}` 규칙 — `indexName` 에만 적용, 테이블별로 부여:**

1. **PK(`PRIMARY`)는 항상 `1`.** 테이블 내 PK 인덱스는 하나뿐이며 연번은 무조건 1을 차지한다.
2. **그 외 인덱스(`FOREIGN`/`UNIQUE`/`NORMAL`/`FULLTEXT`)는 테이블 내 인덱스 생성 순서대로 `2, 3, 4 …`** 를 부여한다. 즉 새 인덱스의 연번 = `해당 테이블의 기존 인덱스 최대 연번 + 1`(PK가 차지한 1 포함).
3. 연번은 **타입과 무관하게 테이블 단위로 단조 증가**한다 (FK·UK·IDX 가 같은 연번 시퀀스를 공유). 접두만 타입별로 다르다.
4. 연번은 **재사용·재정렬하지 않는다.** 중간 인덱스를 삭제해도 남은 인덱스의 연번은 그대로 두고, 새 인덱스는 항상 최대 연번 + 1 을 받는다 (빈 번호 재활용 금지).

**부여 절차:** 생성 직전 `GET /api/v1/erd/table/{tableId}/index/list` 로 기존 인덱스를 조회 → 기존 `indexName` 들의 연번 중 PK 면 1, 아니면 최댓값 + 1 산정 → `indexName` 조립, `indexId` 는 새 UUID(하이픈 제거 32자) → POST.

> **예시** — `USER` 테이블에 PK → FK → UNIQUE → NORMAL 순으로 생성하면 `indexName` 은:
> `PK_USER_1` → `FK_USER_2` → `UK_USER_3` → `IDX_USER_4`. (각 `indexId` 는 별개의 32자 UUID.)

---

## 6. Domain (도메인)

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/erd/project/{projectId}/domain/list` | VIEWER | 도메인 목록 |
| POST | `/api/v1/erd/project/{projectId}/domain` | EDITOR | 도메인 생성 |
| PUT | `/api/v1/erd/domain/{domainId}` | EDITOR | 도메인 수정 |
| DELETE | `/api/v1/erd/domain/{domainId}` | EDITOR | 도메인 삭제 |

---

## 7. Column Group (컬럼 그룹)

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/erd/project/{projectId}/column-group/list` | VIEWER | 컬럼 그룹 목록 |
| GET | `/api/v1/erd/column-group/{groupId}` | VIEWER | 컬럼 그룹 상세 |
| POST | `/api/v1/erd/project/{projectId}/column-group` | EDITOR | 컬럼 그룹 생성 |
| PUT | `/api/v1/erd/column-group/{groupId}` | EDITOR | 컬럼 그룹 수정 |
| DELETE | `/api/v1/erd/column-group/{groupId}` | EDITOR | 컬럼 그룹 삭제 |
| GET | `/api/v1/erd/column-group/{groupId}/column/list` | VIEWER | 그룹의 컬럼 목록 |
| POST | `/api/v1/erd/column-group/{groupId}/column` | EDITOR | 그룹에 컬럼 추가 |
| PUT | `/api/v1/erd/column-group/{groupId}/column/{columnId}` | EDITOR | 그룹 내 컬럼 수정 |
| DELETE | `/api/v1/erd/column-group/{groupId}/column/{columnId}` | EDITOR | 그룹에서 컬럼 제거 |
| PUT | `/api/v1/erd/column-group/{groupId}/columns` | EDITOR | 그룹 컬럼 일괄 갱신 |
| POST | `/api/v1/erd/table/{tableId}/apply-column-group` | EDITOR | 테이블에 컬럼 그룹 적용 |

---

## 8. Glossary / Glossary Dictionary (용어 사전)

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/erd/glossary/dictionary/list` | AUTH | 사전 목록 |
| PUT | `/api/v1/erd/glossary/dictionary/{dictionaryId}` | EDITOR | 사전 수정 |
| DELETE | `/api/v1/erd/glossary/dictionary/{dictionaryId}` | ADMIN | 사전 삭제 |
| GET | `/api/v1/erd/glossary/{dictionaryId}/list` | AUTH | 사전 내 용어 목록 |
| POST | `/api/v1/erd/glossary/{dictionaryId}` | EDITOR | 용어 생성 |
| PUT | `/api/v1/erd/glossary/{glossaryId}` | EDITOR | 용어 수정 |
| DELETE | `/api/v1/erd/glossary/{glossaryId}` | EDITOR | 용어 삭제 |

---

## 9. Project Member (프로젝트 멤버)

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/erd/project/{projectId}/member/list` | VIEWER | 멤버 목록 |
| PUT | `/api/v1/erd/project/{projectId}/member/{userId}` | ADMIN | 멤버 역할 변경/초대 |
| DELETE | `/api/v1/erd/project/{projectId}/member/{userId}` | ADMIN | 멤버 제거 |

역할: `ADMIN` / `EDITOR` / `VIEWER`.

---

## 10. Import / Export

| Method | Path | Role | 용도 |
|--------|------|------|------|
| POST | `/api/v1/erd/import/parse` | AUTH | 외부 ERD 파일 파싱 |
| GET | `/api/v1/erd/export/excel` | VIEWER | Excel export |

---

## 11. Activity Log

| Method | Path | Role | 용도 |
|--------|------|------|------|
| GET | `/api/v1/erd/project/{projectId}/activity/list` | VIEWER | 프로젝트 활동 이력 |

---

## 자연어 매핑 힌트

자연어 표현 → 엔드포인트 빠른 매핑:

| 자연어 키워드 | 엔드포인트 | 비고 |
|--------------|-----------|------|
| "내 프로젝트", "프로젝트 목록" | `GET /api/v1/erd/project/list` | |
| "프로젝트 만들어", "ERD 시작" | `POST /api/v1/erd/project` | 생성자 자동 ADMIN |
| "프로젝트 정보", "프로젝트 상세" | `GET /api/v1/erd/project/{projectId}` | |
| "다이어그램 목록", "이 프로젝트 ERD들" | `GET /api/v1/erd/project/{projectId}/diagram/list` | |
| "다이어그램 추가", "ERD 캔버스 새로" | `POST /api/v1/erd/project/{projectId}/diagram` | |
| "테이블 목록", "이 다이어그램의 엔티티" | `GET /api/v1/erd/diagram/{diagramId}/table/list` | 컬럼까지 한 번에 |
| "프로젝트 전체 테이블", "타 다이어그램 포함 검색" | `GET /api/v1/erd/project/{projectId}/table/list` | cross-diagram FK source 검색용 |
| "테이블 추가", "엔티티 만들어" | `POST /api/v1/erd/diagram/{diagramId}/table` | columns[] 함께 |
| "테이블 삭제" | `DELETE /api/v1/erd/table/{tableId}` | **사용자 확인 필수** |
| "컬럼 추가" | `POST /api/v1/erd/table/{tableId}/column` | 단일 |
| "컬럼들 한번에 변경" | `PUT /api/v1/erd/table/{tableId}` | 테이블 통째 diff |
| "관계 만들어", "FK 연결" | `POST /api/v1/erd/table/{tableId}/index` | `indexType: "FOREIGN"` + `sourceTableId` + `indexColumns[]`, `indexId`/`indexName` 은 [5.6](#56-인덱스-명명-규칙) 규칙 |
| "FK 카디널리티 변경" | `PUT /api/v1/erd/table/{tableId}/foreign-index/{indexId}/cardinality` | atomic |
| "FK 식별/비식별 토글" | `PUT /api/v1/erd/table/{tableId}/foreign-index/{indexId}/identifying` | atomic |
| "인덱스 추가", "유니크 제약" | `POST /api/v1/erd/table/{tableId}/index` | `indexType: "UNIQUE"`/`NORMAL`, `indexId`/`indexName` 은 [5.6](#56-인덱스-명명-규칙) 규칙 |
| "도메인", "공통 데이터타입" | `/api/v1/erd/project/{projectId}/domain` | |
| "컬럼 그룹", "공통 컬럼 세트" | `/api/v1/erd/project/{projectId}/column-group` | createdBy/updatedBy 등 묶음 |
| "용어 사전", "용어 등록" | `/api/v1/erd/glossary/...` | |
| "멤버 초대", "권한 변경" | `/api/v1/erd/project/{projectId}/member/{userId}` | ADMIN만 |
| "DDL 추출", "SQL 만들어줘", "스키마 뽑아" | `ddl_export.py` 스크립트 | DB에 실행 안 됨 |
| "Excel로 추출" | `GET /api/v1/erd/export/excel` | |
| "최근 변경 이력" | `GET /api/v1/erd/project/{projectId}/activity/list` | |
| "테이블 메모", "메모 추가/삭제" | `/api/v1/erd/table/{tableId}/memo` | GET list / POST 추가 / PUT 수정 / DELETE 삭제 |

## 다단계 흐름 패턴

| 사용자 요청 | 호출 순서 |
|-----------|----------|
| "프로젝트명만으로 테이블 추가" | (1) project/list로 projectId 찾기 → (2) diagram/list로 diagramId 결정 → (3) POST table |
| "테이블명만으로 컬럼 추가" | (1) 가능한 다이어그램들에서 table/list 조회 → (2) 매칭 tableId 확정 → (3) POST column |
| "PUT 전 lockTimestamp" | (1) GET으로 현재 lockTimestamp fetch → (2) body에 포함 → (3) PUT |
| "DELETE 영향 범위 보고" | (1) GET 상세 → (2) cascade 대상 사용자 보고 → (3) 동의 받기 → (4) DELETE |
