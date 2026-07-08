---
name: quizn-architecture-diagram-creator
description: QuizN(SoftN) 브랜드를 입힌 HTML 아키텍처 다이어그램을 생성합니다. 개요·핵심지표, 서비스 구조(SHOW/BOARD/VIDEO/CLASS), 데이터 플로·파이프라인, 시스템 아키텍처 계층의 4개 섹션으로 구성됩니다. 사용자가 시스템 아키텍처, 프로젝트 문서, 하이레벨 개요, 데이터 플로 다이어그램, 기술 사양 시각화를 요청할 때 사용합니다.
---

# Architecture Diagram Creator (QuizN Edition)

QuizN 디자인 시스템 토큰으로 스타일링된, 단일 HTML 아키텍처 다이어그램을 만든다.
산출물은 외부 의존성 없이 열리는 **자기완결형 HTML 1개 파일**이다.

## When to Use

- "[프로젝트] 아키텍처 다이어그램 만들어줘"
- "시스템 하이레벨 개요 / 기술 사양 문서화"
- "데이터 플로·처리 파이프라인 보여줘"
- "서비스 구조도 그려줘"

## 산출물 구조 — 4개 섹션 (고정)

1. **개요 · 핵심지표** — 타이틀/서브타이틀 + KPI 메트릭 카드(사용자 수·처리량·가동률 등)
2. **서비스 구조** — SHOW · BOARD · VIDEO · CLASS 4개 서비스 맵과 상호관계
3. **데이터 플로 · 파이프라인** — 소스 → 처리 → 출력 SVG + 단계별 파이프라인
4. **시스템 아키텍처 계층** — 데이터 / 처리 / 서비스 / 출력 계층형 SVG

섹션을 빼거나 추가하지 말 것. 내용이 없으면 플레이스홀더를 채워 4섹션 형태를 유지한다.

## 작업 순서

1. 프로젝트를 분석한다(README, 코드 구조, 사용자 설명에서 목적·데이터 소스·처리·기술스택·출력 추출).
2. `assets/templates/base_template.html`을 골격으로 복사한다. 이 파일에는 QuizN 토큰이 인라인된 `:root`와 4섹션 플레이스홀더가 들어 있다 — **토큰을 재정의하지 말 것.**
3. SVG 다이어그램은 `assets/templates/svg_components.html`의 부품(데이터소스/처리/출력/계층/파이프라인/화살표)을 가져와 좌표·라벨만 바꿔 조립한다.
4. 막힐 때는 `references/example_architecture.html`(완성본)을 구조 참고로 본다.
5. `[project]-architecture.html`로 저장한다.

## 핵심 규약 (QuizN 디자인 시스템 준수)

1. **색 하드코딩 금지** — 항상 토큰 변수 사용. base_template의 `:root`에 모든 값이 정의돼 있다.
   - 테마 강조: `--main-color` / `--sub-color` / `--btn-hover-color` / `--bg-light-color`
   - 서비스 식별색: `--brand-show`(orange) / `--brand-board`(mint) / `--brand-video`(purple) / `--brand-class`(blue), 각 `-light` 틴트 포함
   - 텍스트: `--fg1`(본문) / `--fg2`(보조) / `--fg3`(음소거)
2. **테마 전환은 `<body data-theme="show|board|video|class">` 한 줄.** 미지정 기본값은 SHOW(orange).
3. **폰트 변수만** — 국문 `var(--font-kr)`, 영문/디스플레이 `var(--font-en)`, 코드 `var(--font-mono)`.
4. **라디우스 6종** — `--r-sm`(4) / `--r-md`(8, 카드) / `--r-lg`(28, 패널) / `--r-pill`(50, CTA) / `--r-tab` / `--r-circle`.
5. **스페이싱 4px 9단** — `--space-1`(4) ~ `--space-9`(96). 임의값 금지.
6. **그림자 6종** — `--shadow-card / -pop / -hover / -modal / -toast / -inset`.

## 서비스 ↔ 컬러 매핑 (서비스 구조 섹션에서 사용)

| 서비스 | data-theme | 시그니처 변수 | 컨셉 |
|---|---|---|---|
| **SHOW** 실시간 퀴즈쇼 | `show` | `--brand-show` `#ff6800` orange | 주력·라이브 |
| **BOARD** 학습 보드 | `board` | `--brand-board` `#02d7c5` mint | 협업·학습 |
| **VIDEO** 비디오 퀴즈 | `video` | `--brand-video` `#9359e1` purple | 미디어·창작 |
| **CLASS** 클래스 관리 | `class` | `--brand-class` `#44a2ff` blue | 운영·신뢰 |

## SVG 컬러 규칙 (의미 기반)

- **데이터/입력** → `--brand-class`(blue) 계열
- **처리/변환** → `--brand-show`(orange) 계열
- **AI/분석** → `--brand-video`(purple) 계열
- **출력/성공** → `--brand-board`(mint) 계열
- **화살표/커넥터** → `--fg2`(`#555`), 강조 경로는 해당 단계 색

다이어그램은 명료하게, 스타일은 일관되게, 실제 프로젝트 디테일을 채워 넣는다.
