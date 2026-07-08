# CHANGELOG — QuizN-planning-flow (skill)

## v1.0.0 — 2026-06-17
### Added
- SKILL.md: 7개 절대 규칙(증거기반·검증후질의수용·SVG·오류리포팅·대안·버전·프로젝트폴더) +
  디자인 규칙 D1(다크/라이트)·D2(FHD~4K).
- references/ 5종: workflow / evidence-based-planning / logic-verification /
  flowchart-svg / quizn-theming.
- assets/templates: flowchart_svg_template.html(테마·모드 토글, FHD/QHD/4K, PDF),
  plan_document_template.md(버전 헤더·근거표·검증 링크).
- assets/theme: planning-flow.css(다크/라이트 레이어) + colors_and_type.css 번들 +
  HGGGothicssi 폰트 6종.
- assets/scripts/export_flowchart.py: Playwright/rsvg/cairosvg 백엔드 자동 탐지 변환기.
### Notes
- 아이콘 폰트(fontello)는 흐름도/문서 산출에 불필요하여 번들에서 제외.
