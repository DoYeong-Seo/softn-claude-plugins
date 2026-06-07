# ERD Skill — 자연어 입력 예시 → 처리 흐름

[SKILL.md](SKILL.md)에서 트리거 룰을 적용한 뒤, 실제 처리 흐름은 본 문서의 예시를 참고한다.

## 단순 호출

### 예 1: "내 ERD 프로젝트 보여줘"
- `GET /api/v1/erd/project/list` → 표 형태로 출력 (projectId, projectName, myRole)

### 예 2: "게시판 ERD 만들어줘 — MySQL 대상"
- 사용자에게 projectName/description 확인 (없으면 "게시판 ERD" / "" 사용)
- `POST /api/v1/erd/project` (body: `{projectName:"게시판 ERD",dbmsType:"mysql"}`)

## 명명 워크플로우 포함 (테이블·컬럼 생성·수정)

상세 절차는 [NAMING.md](NAMING.md) 참조.

### 예 3 (단일 테이블 추가): "프로젝트 abc123의 메인 다이어그램에 공지사항 테이블 추가 — 공지사항ID PK, 제목, 등록일시"
- `GET /api/v1/erd/project/abc123/diagram/list` → 다이어그램 1개면 자동, 여러 개면 사용자 확인
- **명명 워크플로우 진입**: `dictionaryId` 획득 → glossary/domain 목록 fetch
- 누락 용어(예: `공지사항`, `제목`, `등록`, `일시`) 중 사전에 없는 것은 `AskUserQuestion` 으로 등록 동의 → `POST /glossary`
- 사전 매핑으로 컬럼 물리명(→`columnId`)과 한글 논리명(→`columnName`) 동시 조립 (예: `DOC_ID`/`문서 아이디`, `NOTICE_TITLE`/`공지사항 제목`, `REG_DATETIME`/`등록 일시`)
- 각 컬럼별 도메인 후보 제시 → `AskUserQuestion` 으로 `domainId` 선택 (또는 "없음")
- columns 배열 구성 (`columnId`=물리명, `columnName`=한글 논리명, [CONVENTIONS.md §4](CONVENTIONS.md)): `[{columnId:"NOTICE_ID", columnName:"공지사항 아이디", domainId:"<선택값>", primarykeyFlag:1, notnullFlag:1, displayOrder:1}, ...]`
- 최종 요약 동의 후 `POST /api/v1/erd/diagram/{diagramId}/table` 호출 → 생성된 tableId 보고

### 다단계: "게시판 ERD 프로젝트에 공지사항 테이블 추가해줘 — 공지사항ID, 제목, 내용, 등록일시"
1. `GET /api/v1/erd/project/list` → "게시판 ERD" 매칭되는 `projectId` 찾기 (없으면 사용자에게 확인)
2. `GET /api/v1/erd/project/{projectId}/diagram/list` → 대상 다이어그램 결정 (1개면 자동 선택, 여러 개면 사용자 확인)
3. **명명 워크플로우** (필수, [NAMING.md](NAMING.md)):
   - `GET /api/v1/erd/project/{projectId}` → `dictionaryId` 획득
   - `GET /api/v1/erd/glossary/{dictionaryId}/list` + `GET /api/v1/erd/project/{projectId}/domain/list`
   - 논리명 토큰(`공지사항`, `제목`, `내용`, `등록`, `일시`) 사전 조회 → 누락분은 `AskUserQuestion` 으로 사용자 승인 후 `POST /glossary` 등록
   - 사전 매핑으로 컬럼별 물리명(→`columnId`)·한글 논리명(→`columnName`) 동시 조립: `NOTICE`/`공지사항`, `NOTICE_TITLE`/`공지사항 제목`, `NOTICE_CONTENT`/`공지사항 내용`, `NOTICE_REG_DATETIME`/`공지사항 등록 일시` 등
   - 각 컬럼별 도메인 후보 추천 → `AskUserQuestion` 으로 사용자가 `domainId` 선택
4. 최종 요약 → 사용자 동의 → `POST /api/v1/erd/diagram/{diagramId}/table` (body: tableInfo + columns 배열, 각 컬럼에 `columnId`(물리명)·`columnName`(한글 논리명)·`domainId` 포함)
5. 결과 요약 응답

## FK 관계 (명명 워크플로우 비대상이지만 컬럼 추가는 적용)

### 예 4: "프로젝트 abc123의 USER와 POST를 1:N 관계로 연결" (FK = `ErdTableIndex(indexType=FOREIGN)` 단일 진실원, 2026-05-07~)
- 두 테이블의 ID·PK 컬럼 식별 (`GET /api/v1/erd/diagram/{diagramId}/table/list`)
- 자식 테이블 (POST) 에 FK 컬럼 (`USER_ID`) 추가: `POST /api/v1/erd/table/{postTableId}/column`
  - 이 컬럼 추가는 명명 워크플로우 대상. 다만 부모 PK 컬럼의 물리명을 그대로 차용하는 경우(`USER_ID`) glossary 매핑은 이미 부모 컬럼에서 검증됨. 컬럼 body 는 `{"columnId":"USER_ID","columnName":"사용자 아이디", ...}` 형태(물리명→`columnId`, 한글 논리명→`columnName`).
- `indexColumns[].columnId` / `sourceColumnId` 는 각각 **자식·부모 컬럼의 물리명**(=`columnId`)이다. `POST /api/v1/erd/table/{postTableId}/index` body 예:
  ```json
  {
    "indexType": "FOREIGN",
    "sourceTableId": "{userTableId}",
    "indexName": "FK_POST_1",
    "onDeleteAction": "CASCADE",
    "onUpdateAction": "NO_ACTION",
    "indexColumns": [
      {"columnId": "USER_ID", "sourceColumnId": "USER_ID", "sortType": "ASC", "displayOrder": 1}
    ]
  }
  ```
- 카디널리티 / 식별 변경 시: `PUT /api/v1/erd/table/{postTableId}/foreign-index/{indexId}/cardinality` 또는 `.../identifying` (atomic)

## 테이블 메모 (Table Memo)

`ERD_TABLE_MEMO` 는 테이블별로 자유 텍스트 메모를 부착하는 보조 엔티티다. `memoFixFlag=1` 인 메모가 상단에 고정되어 먼저 표시된다. 메모 본문(`memoContents`)은 명명 워크플로우 비대상 — 자유 텍스트.

### 예 M1: "USER 테이블 메모 보여줘"
- `GET /api/v1/erd/diagram/{diagramId}/table/list/without-columns` 또는 캐시된 결과로 `USER` 의 `tableId` 확정
- `GET /api/v1/erd/table/{tableId}/memo/list` → `memoFixFlag DESC, displayOrder ASC` 순으로 목록 출력
- 표 형태: memoId / memoContents / memoFixFlag / displayOrder

### 예 M2: "USER 테이블에 '관리자만 직접 INSERT 가능' 메모 추가, 고정으로"
- tableId 확정 (위와 동일)
- `POST /api/v1/erd/table/{tableId}/memo` body:
  ```json
  { "memoContents": "관리자만 직접 INSERT 가능", "memoFixFlag": 1 }
  ```
- `memoId`는 서버 자동(UUID), `displayOrder`는 미지정 시 현재 메모 개수로 자동.
- 응답 `data.memoId` 보고. 201 Created.

### 예 M3: "방금 추가한 메모 본문만 수정"
- 메모 본문 부분 갱신은 **부분 갱신 지원**: 보낼 필드만 전달하면 됨 (`memoFixFlag`/`displayOrder` 그대로 유지).
- `GET /api/v1/erd/table/{tableId}/memo/list` → 최신 `lockTimestamp` 확보
- `PUT /api/v1/erd/table/{tableId}/memo/{memoId}` body:
  ```json
  { "memoContents": "수정된 본문", "lockTimestamp": "2026-05-19 16:42:10" }
  ```
- 409 `ERD_TABLE_MEMO_CONFLICT` 시 GET 재호출 → 새 `lockTimestamp` 로 재시도.

### 예 M4: "메모 고정 토글 / 순서 변경"
- 고정/해제: `PUT .../memo/{memoId}` body `{ "memoFixFlag": 1, "lockTimestamp": "..." }` (혹은 0)
- 순서 변경: 동일 PUT 에 `displayOrder` 만 다른 값으로.
- 본문은 그대로 유지하고 싶으면 보내지 않으면 됨.

### 예 M5: "메모 삭제"
- 사용자 확인 후 `DELETE /api/v1/erd/table/{tableId}/memo/{memoId}` body `{ "lockTimestamp": "..." }`
- 200 OK, "메모가 삭제되었습니다." 안내.

## DDL & 삭제

### 예 5: "프로젝트 abc123의 ERD에서 DDL 뽑아줘"
- `python3 "${CLAUDE_PLUGIN_ROOT}/skills/erd-design/ddl_export.py" --project-id abc123` ([DDL_EXPORT.md](DDL_EXPORT.md))
- 결과 파일 경로 안내

### 예 6: "이 테이블 삭제해줘 — tableId xyz789"
- `GET /api/v1/erd/table/{xyz789}` 등으로 영향 범위 확인 후 사용자에게 cascade 대상(컬럼/인덱스/관계) 보고
- 사용자 확인 후 `DELETE /api/v1/erd/table/{xyz789}` (body에 lockTimestamp 포함)
