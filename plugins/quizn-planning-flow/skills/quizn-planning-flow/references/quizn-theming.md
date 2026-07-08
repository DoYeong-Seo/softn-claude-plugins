# QuizN Theming — 토큰 + 다크/라이트 모드 (디자인 D1)

quizn-design-system 토큰을 사용하되 **다크/라이트 모드를 모두 지원**한다. quizn-design-system은
기본적으로 라이트 톤만 정의하므로, 본 스킬은 그 위에 **다크 레이어**(`planning-flow.css`)를 얹는다.

핵심: **브랜드 4토큰**(`--main-color` 등)은 서비스 테마(`data-theme`)로,
**뉴트럴/표면/텍스트**는 모드(`data-mode`)로 전환한다. 두 축은 독립적이다.

```
data-theme = show | board | video | class   (브랜드 색)
data-mode  = light | dark                    (배경/표면/텍스트)
```

---

## 1. 두 축 (Two Axes)

| 축 | 속성 | 전환 대상 | 정의 위치 |
|---|---|---|---|
| 서비스 테마 | `body[data-theme]` | `--main-color` `--sub-color` `--btn-hover-color` `--bg-light-color` `--theme-deep` | colors_and_type.css |
| 명암 모드 | `body[data-mode]` | `--bg` `--surface` `--fg` `--border` 및 노드 색 | planning-flow.css (이 스킬) |

예: `<body data-theme="board" data-mode="dark">` → 민트 브랜드 + 다크 배경.

---

## 2. planning-flow.css 가 더하는 것

`planning-flow.css`는 `colors_and_type.css`를 `@import`한 뒤, 다음을 추가 정의한다.

1. **라이트 모드 기본값**(`:root` / `[data-mode="light"]`) — 표면/노드 토큰을 quizn 뉴트럴에 매핑.
2. **다크 모드 오버라이드**(`[data-mode="dark"]`) — 배경/표면/텍스트/보더/노드 색을 어둡게 재정의.
3. **시스템 선호 연동** — `@media (prefers-color-scheme: dark)`로 `data-mode` 미지정 시 자동.
4. **흐름도 전용 토큰** — `--node-process`, `--node-decision`, `--node-error`, `--edge`,
   `--node-fg`, `--node-stroke`, `--lane-bg`, `--canvas-bg` 등. 모두 모드에 따라 값이 바뀐다.

> 컴포넌트·SVG는 위 토큰만 참조한다. 절대 `#hex`를 직접 쓰지 않는다(테마/모드 깨짐 방지).

### 흐름도 토큰 ↔ 모드 매핑 (요약)

| 토큰 | light | dark |
|---|---|---|
| `--canvas-bg` | `#ffffff` | `#16181d` |
| `--surface` | `#f7f7f7` | `#22262e` |
| `--node-fg` | `#282828` | `#f2f3f5` |
| `--node-process` | `var(--bg-light-color)` | `#2a2f3a` |
| `--node-decision` | `var(--sub-color)` | `var(--main-color)` |
| `--node-error` | `#fff0f0` | `#3a2530` |
| `--edge` | `#777` | `#9aa0aa` |
| `--node-terminal` | `var(--main-color)` | `var(--main-color)` |

(전체 값은 `assets/theme/planning-flow.css` 참조. 브랜드색은 모드와 무관하게 테마를 따른다.)

---

## 3. 사용 패턴

### 3.1 페이지 골격
```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="./assets/planning-flow.css">
</head>
<body data-theme="show" data-mode="light">
  <!-- 흐름도 / 기획 화면 -->
</body>
</html>
```

### 3.2 모드 토글 (JS)
```js
function toggleMode(){
  const b = document.body;
  b.dataset.mode = b.dataset.mode === 'dark' ? 'light' : 'dark';
}
```

### 3.3 테마 토글 (JS)
```js
function setTheme(t){ document.body.dataset.theme = t; } // show|board|video|class
```

---

## 4. 에셋 배치 (필수)

산출물 폴더(`프로젝트/assets/`)에 다음을 함께 둔다.

```
assets/
├── planning-flow.css        # 이 스킬 진입 CSS (colors_and_type.css를 import)
├── colors_and_type.css      # quizn-design-system에서 복사
└── fonts/                   # quizn-design-system의 fonts/ 폴더 전체 복사
    ├── HGGGothicssi_*.ttf
    └── fontello/...
```

`planning-flow.css`의 `@import url('./colors_and_type.css');`가 같은 폴더의 CSS를 찾는다.
폰트가 빠지면 브랜드 폰트가 적용되지 않으니 `fonts/`를 반드시 함께 복사한다.

---

## 5. 자주 하는 실수

- ❌ `data-mode`만 만들고 노드 색을 하드코딩 → 다크에서 글자가 안 보임.
- ❌ `--main-color`를 인라인으로 덮어쓰기 → 전체 테마 붕괴.
- ❌ 라이트만 만들고 다크 미지원 → **디자인 규칙 D1 위반**.
- ✅ 모든 색을 토큰으로, 두 축(`data-theme`·`data-mode`)을 독립적으로 전환.
