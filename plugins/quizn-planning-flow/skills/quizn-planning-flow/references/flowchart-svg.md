# Flowchart (SVG) — 작성·해상도·내보내기 (절대 규칙 3 + 디자인 D2)

흐름도는 **SVG로 작성**한다. 요청 시 이미지(PNG)·문서(PDF)로 내려받을 수 있게 제공하며,
해상도는 **FHD(1920×1080) 최소 ~ 4K(3840×2160) 최대**를 충족한다.

기반 패턴은 flowchart-creator의 `references/svg_library.md`를 따르되, **색·폰트는 절대
하드코딩하지 않고** QuizN 토큰(`planning-flow.css`)만 참조한다.

---

## 1. 왜 SVG인가

- 벡터 → 어떤 해상도(FHD~4K)로도 깨짐 없이 확대.
- 텍스트가 선택·검색 가능, 접근성 우수.
- CSS 변수로 다크/라이트·서비스 테마를 즉시 전환.
- PNG/PDF로 정확히 래스터화·인쇄 가능.

---

## 2. SVG 좌표계와 해상도 매핑 (디자인 D2)

`viewBox`는 16:9 비율을 기본으로 한다. 한 장에 담기면 `1920×1080` 논리좌표를 권장.

```
viewBox="0 0 1920 1080"   → FHD 기준 1:1 매핑 (최소 보장)
export PNG @1x  = 1920×1080  (FHD, 최소)
export PNG @2x  = 3840×2160  (4K, 최대)
export PNG @1.33x = 2560×1440 (QHD, 중간 옵션)
```

세로로 긴 흐름은 `viewBox="0 0 1920 H"`(H>1080)로 늘리고, 내보낼 때 폭 1920(FHD)~3840(4K)
기준으로 비율 유지 스케일한다. **가로 폭이 항상 FHD 이상**이 되도록 한다.

> 규칙: 어떤 내보내기도 **짧은 변이 1080px 미만이면 안 된다**(FHD 최소). 최대는 4K(2160px).

---

## 3. 노드 규약 (QuizN 토큰 사용)

flowchart-creator의 형태를 따르되 색은 토큰으로 바꾼다. (예시는 light/dark 공통 동작)

| 노드 | 형태 | 채움(fill) | 비고 |
|---|---|---|---|
| 시작/종료 | 둥근 사각/원 | `var(--node-terminal)` | 시작=메인색, 종료=뉴트럴 |
| 처리(Process) | 사각 rx=8 | `var(--node-process)` | |
| 결정(Decision) | 다이아몬드 | `var(--node-decision)` | 분기 라벨 필수 |
| 입출력(I/O) | 평행사변형 | `var(--node-io)` | |
| 에러/예외 | 사각 점선 | `var(--node-error)` | L6 예외 경로 |
| 스윔레인 | 영역 박스 | `var(--lane-bg)` | 역할/시스템 구분 |

화살표 마커·텍스트 색도 `var(--edge)`, `var(--node-fg)` 등 토큰을 쓴다. (정의는 템플릿에 포함)

### 좋은 예 / 나쁜 예

```xml
<!-- ✅ 토큰 사용: 테마·모드 전환에 자동 반응 -->
<rect x="100" y="100" width="280" height="90" rx="8"
      fill="var(--node-process)" stroke="var(--node-stroke)" stroke-width="2"/>
<text x="240" y="150" text-anchor="middle" fill="var(--node-fg)"
      font-family="var(--font-kr)" font-size="22">방 코드 입력</text>

<!-- ❌ 하드코딩: 다크모드/테마에서 깨짐 -->
<rect ... fill="#4299e1"/>
<text ... fill="#ffffff">...</text>
```

---

## 4. 흐름도 작성 절차

1. `assets/templates/flowchart_svg_template.html`을 복사해 시작.
2. `<head>`에서 `planning-flow.css`(+`colors_and_type.css`)를 링크.
3. `<body data-theme="show|board|video|class" data-mode="light|dark">` 설정.
4. `viewBox="0 0 1920 1080"`(또는 세로 확장) 안에 노드·엣지를 토큰 색으로 배치.
5. 우하단 `#version-badge`에 현재 버전 표기(절대 규칙 6).
6. 작성 직후 → `references/logic-verification.md`로 **검증** → 요청자 질의 → 수용.

---

## 5. 내보내기 (PNG·PDF, FHD~4K)

두 가지 경로를 제공한다. 둘 다 FHD~4K를 만족한다.

### 5.1 브라우저 내장 버튼 (템플릿에 포함)
`flowchart_svg_template.html`은 상단 툴바에 버튼을 갖는다.
- **SVG 저장** — 현재 SVG를 `.svg`로 다운로드 (무한 해상도).
- **PNG FHD (1920)** / **PNG QHD (2560)** / **PNG 4K (3840)** — canvas 래스터화 다운로드.
- **PDF (인쇄)** — `window.print()` (A3 가로 권장). 또는 아래 스크립트로 벡터 PDF 생성.
- **모드 토글** — Light ⇄ Dark, **테마 토글** — SHOW/BOARD/VIDEO/CLASS.

### 5.2 스크립트 (배치·고품질) — `assets/scripts/export_flowchart.py`
헤드리스 환경에서 일괄 변환. 사용 가능한 백엔드를 자동 탐지(playwright > rsvg > cairosvg).

```bash
# 단일 HTML/SVG → FHD·4K PNG + PDF 일괄
python assets/scripts/export_flowchart.py 03_flowcharts/src/flow_login_v0.3.1.html \
       --out 03_flowcharts/exports --fhd --4k --pdf --mode both --theme show
```

- `--fhd` 1920×1080(최소) / `--4k` 3840×2160(최대) / `--qhd` 2560×1440(옵션)
- `--pdf` 벡터 PDF / `--mode light|dark|both` / `--theme show|board|video|class`
- 출력: `exports/png-fhd/`, `exports/png-4k/`, `exports/pdf/` 에 모드·테마별 파일.

> 어떤 경로로 내보내든 **파일명에 버전을 포함**한다: `flow_login_v0.3.1_4k_dark.png`.
