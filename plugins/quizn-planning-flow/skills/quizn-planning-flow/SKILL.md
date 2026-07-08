---
name: quizn-planning-flow
description: |
  SoftN/QuizN 서비스 기획 및 기획 전반을 수행하는 스킬입니다. 증거 기반(evidence-based)으로
  요구사항을 정리하고, 흐름도(Flowchart)를 SVG로 작성한 뒤 반드시 논리 검증·오류 리포팅·대안 제시를
  거쳐 요청자에게 질의하고 수용합니다. 모든 산출물은 프로젝트 단위 폴더로 관리되며 버전을 필수로
  표기합니다. 디자인은 quizn-design-system 토큰을 사용하되 다크/라이트 모드를 모두 지원하고,
  흐름도·다운로드는 FHD(1920×1080) 최소 ~ 4K(3840×2160) 해상도를 충족합니다.
  사용자가 "서비스 기획" "기획서/PRD 작성" "흐름도/플로우차트/프로세스 다이어그램" "기획 검토"
  "유저 플로우" "정책 흐름도" "QuizN 기획" 등을 요청하거나, SHOW·BOARD·VIDEO·CLASS 서비스의
  화면/정책/프로세스 설계를 의뢰할 때 사용합니다.
  EN: Use this skill for QuizN service planning and product planning end-to-end —
  evidence-based requirements, SVG flowcharts with mandatory logic verification,
  error reporting, alternatives, requester confirmation, project-scoped folders, and
  version stamping. Design uses the QuizN design system with both dark and light modes,
  flowcharts/exports at FHD minimum up to 4K.
---

# quizn-planning-flow

SoftN의 QuizN 서비스(**SHOW · BOARD · VIDEO · CLASS**) 기획 전반을 수행하는 스킬입니다.
요구사항 정리 → 흐름도(SVG) 작성 → **논리 검증·오류 리포팅·대안 제시** → 요청자 질의·수용 →
버전 확정의 순환을 강제하며, 모든 작업은 **프로젝트 단위 폴더**에서 진행됩니다.

> This skill drives QuizN service/product planning end-to-end. It **enforces** an
> evidence-first loop: gather evidence → draft an SVG flowchart → run logic verification
> (report errors + propose alternatives) → ask the requester → only then accept and
> version-stamp. Everything lives inside a per-project folder.

---

## 0. 절대 규칙 (Non-negotiable Rules)

이 7가지는 어떤 경우에도 생략하지 않는다. (Never skip these.)

1. **증거 기반 (Evidence-based)** — 모든 기획 주장·결정은 출처/근거를 명시한다. 근거 없는
   추정은 `[가정]`으로 표시하고 검증 대상으로 분류한다. → `references/evidence-based-planning.md`
2. **흐름도는 검증 후 질의·수용** — 흐름도를 그린 직후 반드시 논리 검증을 수행하고, 그 결과를
   요청자에게 **질의**한 뒤에만 확정(수용)한다. 검증·질의 없이 확정 금지.
3. **흐름도는 SVG로 작성** — 흐름도는 SVG로 그린다. 요청 시 이미지(PNG)·문서(PDF)로도 내려받을 수
   있게 제공한다. → `references/flowchart-svg.md`
4. **논리 오류는 반드시 리포팅** — 논리 구조 검증 시 발견된 오류를 누락 없이 리포트한다.
   (오류 0건이어도 "검증 완료, 오류 없음"을 명시한다.) → `references/logic-verification.md`
5. **대안 반드시 제시** — 논리 검증 시 발견 오류마다 1개 이상의 대안을 함께 제시한다.
6. **버전 필수 표기** — 모든 진행/확정 산출물에 버전을 표기한다. 수정·변경 시 버전을 반드시
   올린다(bump). → `references/workflow.md`
7. **프로젝트 단위 진행** — 모든 작업은 프로젝트 폴더에서 진행한다. 시작 시 폴더 생성 요건을
   반드시 안내·생성한다. → `references/workflow.md` §프로젝트 폴더

추가 — **디자인 규칙 (Design Rules)**

- D1. quizn-design-system 토큰을 사용하되 **다크/라이트 모드를 모두 지원**한다(`data-mode`).
  → `references/quizn-theming.md`
- D2. 흐름도·다운로드는 **FHD(1920×1080) 최소, 4K(3840×2160) 최대** 해상도를 충족한다.

---

## 1. 표준 워크플로우 (Standard Workflow)

기획 요청을 받으면 아래 순서를 따른다. 각 단계는 `references/workflow.md`에 상세히 정의되어 있다.

```
[P0] 프로젝트 초기화      →  프로젝트 폴더 생성 + v0.1.0 (Draft) 부여
[P1] 증거 수집·요구 정리   →  근거표(Evidence Table) 작성, [가정] 표시
[P2] 흐름도 SVG 작성       →  flowchart_svg_template.html 기반, 다크/라이트, FHD~4K
[P3] 논리 검증            →  오류 리포트 + 대안 제시 (필수)
[P4] 요청자 질의·수용      →  질의 → 답변 반영 → 수용 결정
[P5] 버전 확정·기록        →  버전 bump + CHANGELOG 기록
[P6] 내보내기            →  SVG / PNG(FHD·4K) / PDF 다운로드 제공
```

확정(수용) 없이 P2→P5로 건너뛰지 않는다. 검증·질의는 의무 게이트(gate)다.

---

## 2. 시작 시 동작 순서 (On Invocation)

1. **프로젝트 확인** — 기존 프로젝트인지 신규인지 묻는다. 신규면 폴더 요건을 안내하고 생성한다
   (`references/workflow.md` §프로젝트 폴더). 기존이면 최신 버전과 CHANGELOG를 먼저 읽는다.
2. **서비스/모드 확인** — 대상 서비스(SHOW/BOARD/VIDEO/CLASS, 미지정 시 SHOW)와 화면 종류를
   확인한다. 다크/라이트는 기본 둘 다 지원(`data-mode` 토글).
3. **증거 수집** — `references/evidence-based-planning.md`에 따라 근거표를 채운다.
4. **흐름도 작성** — `assets/templates/flowchart_svg_template.html`로 SVG를 그린다.
   디자인 토큰은 `assets/theme/planning-flow.css`만 참조한다.
5. **논리 검증 → 질의 → 수용** — `references/logic-verification.md`의 체크리스트로 검증하고,
   오류 리포트·대안을 만든 뒤 요청자에게 질의한다. 답변을 반영해 수용한다.
6. **버전·내보내기** — 버전을 확정/bump하고, 필요 시 `assets/scripts/export_flowchart.py`로
   PNG(FHD·4K)·PDF를 생성한다.

---

## 3. 참조 파일 가이드 (Reference Files)

| 작업 / Task | 읽을 파일 / Read |
|---|---|
| 워크플로우·버전 규칙·프로젝트 폴더 요건 | `references/workflow.md` |
| 증거 기반 기획·근거표·요구사항 정리 | `references/evidence-based-planning.md` |
| 논리 검증 체크리스트·오류 리포트·대안 양식 | `references/logic-verification.md` |
| SVG 흐름도 작성·노드 규약·FHD/4K·내보내기 | `references/flowchart-svg.md` |
| QuizN 토큰 + 다크/라이트 모드 적용 | `references/quizn-theming.md` |

## 4. 에셋 가이드 (Assets)

| 에셋 / Asset | 용도 / Purpose |
|---|---|
| `assets/templates/flowchart_svg_template.html` | SVG 흐름도 골격 (다크/라이트 토글, 서비스 테마, FHD/2K/4K 내보내기 버튼) |
| `assets/templates/plan_document_template.md` | 기획서/PRD 템플릿 (버전 헤더·근거표·검증 리포트·CHANGELOG 포함) |
| `assets/theme/planning-flow.css` | quizn-design-system 토큰 + 다크/라이트 레이어 (이 스킬 전용 진입 CSS) |
| `assets/scripts/export_flowchart.py` | HTML/SVG → PNG(FHD·4K)·PDF 변환 스크립트 |

> 산출물 폴더에는 `planning-flow.css`와 함께 quizn-design-system의 `colors_and_type.css` 및
> `fonts/` 폴더를 같이 복사해야 폰트·브랜드 토큰이 동작한다. 자세한 내용은 `references/quizn-theming.md`.

---

## 5. 의존 스킬 (Dependencies)

- **flowchart-creator** — SVG 노드/마커/레이아웃 패턴의 참조 모델. 본 스킬의 SVG 작성은 이
  스킬의 패턴을 따르되, 색·폰트는 QuizN 토큰으로 대체한다.
- **quizn-design-system** — 브랜드 토큰·폰트·아이콘의 원천. 본 스킬은 그 위에 다크/라이트
  레이어를 더해 사용한다.
