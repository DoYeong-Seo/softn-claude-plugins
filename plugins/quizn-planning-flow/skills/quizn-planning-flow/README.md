# QuizN-planning-flow

SoftN/QuizN 서비스 기획 전반(요구 정리 → 흐름도 → 검증 → 질의·수용 → 버전 확정)을
수행하는 스킬입니다. 참조 모델 **flowchart-creator**의 SVG 패턴과 **quizn-design-system**의
브랜드 토큰을 결합하고, 그 위에 다크/라이트 모드와 FHD~4K 내보내기를 더했습니다.

## 폴더 구조
```
QuizN-planning-flow/
├── SKILL.md                         # 스킬 정의 (절대 규칙 7가지 + 디자인 규칙)
├── README.md                        # 이 문서
├── CHANGELOG.md                     # 스킬 자체 버전 이력
├── references/
│   ├── workflow.md                  # 워크플로우·버전 규칙·프로젝트 폴더 요건 (규칙 6·7)
│   ├── evidence-based-planning.md   # 증거 기반 기획·근거표 (규칙 1)
│   ├── logic-verification.md        # 논리 검증·오류 리포트·대안·질의 (규칙 2·4·5)
│   ├── flowchart-svg.md             # SVG 흐름도·FHD/4K·PNG/PDF 내보내기 (규칙 3 · D2)
│   └── quizn-theming.md             # QuizN 토큰 + 다크/라이트 (D1)
└── assets/
    ├── templates/
    │   ├── flowchart_svg_template.html   # SVG 흐름도(테마·모드 토글, FHD/QHD/4K, PDF)
    │   └── plan_document_template.md      # 기획서/PRD(버전 헤더·근거표·검증 링크)
    ├── theme/
    │   ├── planning-flow.css              # 진입 CSS: quizn 토큰 + 다크/라이트 레이어
    │   ├── colors_and_type.css            # quizn-design-system 번들 사본
    │   └── fonts/HGGGothicssi_*.ttf       # 브랜드 국문 폰트 6종
    └── scripts/
        └── export_flowchart.py            # HTML/SVG → PNG(FHD·4K)·PDF 일괄 변환
```

## 설치 (둘 중 하나)
- **.skill 패키지:** `QuizN-planning-flow.skill` 을 저장 → 데스크톱 앱의 Settings ▸ Capabilities
  에서 설치.
- **폴더 직접 배치:** `QuizN-planning-flow/` 폴더를 스킬 디렉터리에 복사.

## 핵심 규칙 (요약)
1. 증거 기반 · 2. 흐름도는 검증→질의→수용 · 3. SVG 작성(PNG/PDF 다운로드) ·
4. 논리 오류 리포팅(0건도 명시) · 5. 오류마다 대안 ≥1 · 6. 모든 산출물 버전 표기(변경 시 bump) ·
7. 프로젝트 단위 폴더 진행. 디자인: D1 다크/라이트 동시 지원 · D2 FHD~4K.

## 의존
참조: flowchart-creator, quizn-design-system. (아이콘 폰트 fontello는 본 스킬 산출에 불필요하여
번들에서 제외 — 필요 시 quizn-design-system에서 복사.)
