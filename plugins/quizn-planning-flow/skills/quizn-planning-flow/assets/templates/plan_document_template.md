<!-- 기획서/PRD 템플릿 · QuizN-planning-flow
     파일명에 버전 포함: plan_v{버전}.md (예: plan_v0.1.0.md) -->

> **버전 / Version:** v0.1.0
> **상태 / Status:** Draft  (Draft → In-Review → Accepted → Released)
> **대상 서비스 / Service:** SHOW  (show | board | video | class)
> **모드 / Mode:** light + dark 동시 지원
> **오너·요청자 / Owner:** {{이름}}
> **최종 수정 / Updated:** {{YYYY-MM-DD}}
> **변경 요약 / Change:** 최초 작성
> **이전 버전 / Prev:** —

# {{기획 제목}} — 기획서 / PRD

## 1. 배경 & 문제 (Background & Problem)
- 무엇이 문제인가? 누구의 문제인가?
- (근거: EV-01, EV-02 …) ← 근거표 ID 인용. 근거 없으면 `[가정]` 표시.

## 2. 목표 & 비목표 (Goals / Non-goals)
- **목표:** 측정 가능한 형태로. (예: 첫 라이브 진입 이탈 40%→25%)
- **비목표:** 이번 범위에서 다루지 않는 것.

## 3. 대상 사용자 & 시나리오 (Users & Scenarios)
- 페르소나 / 핵심 시나리오 / 진입 경로.

## 4. 요구사항 (Requirements)
| ID | 요구사항 | 우선순위 | 근거(EV-ID) | 비고 |
|---|---|---|---|---|
| R-01 | … | P0 | EV-01 | |
| R-02 | … | P1 | [가정] AS-01 | 검증 필요 |

## 5. 흐름 (Flow)
- 관련 흐름도: `03_flowcharts/src/flow_{name}_v0.1.0.html`
- 핵심 분기·예외 경로 요약.

## 6. 정책 & 예외 (Policy & Edge cases)
- 권한/결제/개인정보/약관 등 정책 요건.
- 실패·타임아웃·취소·경계값 처리.

## 7. 성공 지표 (Success Metrics)
- 선행지표 / 후행지표 / 측정 방법(데이터 출처).

## 8. 논리 검증 결과 (Verification) — 필수 링크
- 리포트: `04_verification/verify_v0.1.0.md`
- 요약: 오류 N건(Critical/Major/Minor), 채택 대안, 요청자 질의 결과.

## 9. 의사결정 기록 (Decisions)
- `05_decisions/{date}.md` 의 질의-수용 요약.

---

## CHANGELOG (요약 — 전체는 CHANGELOG.md)
- v0.1.0 (Draft, {{날짜}}) — 최초 작성.

<!--
  주의(절대 규칙):
  1) 모든 주장에 근거(EV-ID) 또는 [가정] 표시.
  2) 흐름도는 SVG로, 검증→질의→수용 후에만 확정.
  4) 논리 오류는 0건이어도 검증 리포트에 명시.
  5) 오류마다 대안 ≥1.
  6) 변경 시 반드시 버전 bump + 이 헤더/파일명/CHANGELOG 동기화.
  7) 본 문서는 프로젝트 폴더(02_requirements/) 안에 위치.
-->
