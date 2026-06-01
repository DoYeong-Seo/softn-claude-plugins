# softn-claude-plugins

소프트앤 사내 Claude Code 플러그인 마켓플레이스입니다.
레포 하나에 여러 플러그인을 담고, 팀원이 필요한 것만 골라 설치/업데이트합니다.

계층: **마켓플레이스(이 레포) → 플러그인(여러 개) → 스킬(여러 개)**

## 수록 플러그인

| 플러그인 | 버전 | 설명 |
|----------|------|------|
| `blog-editor` | 1.0.0 | BlogN 블로그/포스트 관리 REST API를 자연어로 호출 — 포스트 CRUD, Editor.js 블록 본문 작성·저장, 파일 업로드, Markdown 양방향 변환 |
| `erd-design` | 1.0.0 | BlogN ERD 설계 도구 REST API를 자연어로 호출 — ERD 프로젝트/다이어그램/테이블/컬럼/관계 메타데이터 관리 및 MySQL DDL 생성 |

## 디렉토리 구조

```
softn-claude-plugins/
├── .claude-plugin/
│   └── marketplace.json          # 플러그인 카탈로그 (진입점)
├── plugins/
│   ├── blog-editor/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/blog-editor/   # SKILL.md, BLOCKS.md, ENDPOINTS.md, block_builder.py, README.md
│   └── erd-design/
│       ├── .claude-plugin/plugin.json
│       └── skills/erd-design/    # SKILL.md, NAMING.md, CONVENTIONS.md, ENDPOINTS.md, DDL_EXPORT.md, EXAMPLES.md, ddl_export.py, requirements.txt
└── README.md
```

## 설치 (팀원용)

```bash
# 1) 마켓플레이스 추가 (사내 GitLab git URL 사용)
/plugin marketplace add https://gitlab.softn.kr/dev/claude-plugins.git
# 또는 SSH
/plugin marketplace add ssh://git@gitlab.softn.kr/dev/claude-plugins.git

# 2) 필요한 플러그인만 골라 설치
/plugin install blog-editor@softn-tools
/plugin install erd-design@softn-tools
```

설치된 스킬은 네임스페이스가 붙습니다: `/blog-editor:blog-editor`, `/erd-design:erd-design`.

### 온보딩 자동화 (선택)

프로젝트 `.claude/settings.json`에 등록하면 폴더 신뢰 시 자동 설치됩니다.

```json
{
  "extraKnownMarketplaces": {
    "softn-tools": {
      "source": { "source": "git", "url": "https://gitlab.softn.kr/dev/claude-plugins.git" }
    }
  },
  "enabledPlugins": ["blog-editor@softn-tools", "erd-design@softn-tools"]
}
```

## 개발 / 기여

```bash
# 단일 플러그인을 로컬 경로로 직접 로드해 테스트
claude --plugin-dir ./plugins/blog-editor

# 마켓플레이스 전체를 로컬 경로로 등록
/plugin marketplace add ./softn-claude-plugins

# 구조/스키마 유효성 검사 (push 전 필수)
claude plugin validate .
```

새 스킬 추가 시:
1. `plugins/<name>/.claude-plugin/plugin.json` 작성 (`version` 관리 필수)
2. `plugins/<name>/skills/<skill>/SKILL.md` 작성 (frontmatter `description`이 트리거)
3. 플러그인 내부 파일 참조는 `${CLAUDE_PLUGIN_ROOT}` 변수 사용 (설치 시 캐시 경로로 복사됨)
4. `.claude-plugin/marketplace.json`의 `plugins[]`에 상대 경로로 등록
5. `claude plugin validate .` 통과 후 GitLab push

## 업데이트 운영

스킬 개선 시 해당 `plugin.json`의 `version`을 올리고 push합니다. 팀원은 다음으로 최신본을 받습니다.

```bash
/plugin marketplace update softn-tools
```

## 프로젝트별 설정값

스킬은 배포 순간 모든 프로젝트의 공유 자산이 됩니다. 프로젝트마다 다른 값(토큰, 기본 블로그/프로젝트 등)은 스킬에 하드코딩하지 말고 프로젝트 로컬에 두고 런타임에 읽습니다.

- **PAT 토큰**: `BLOGN_PAT_TOKEN` 환경변수 (`blog-editor`는 `blog`/`file`, `erd-design`은 `erd` scope 필요). 플러그인에 번들하지 않습니다.
- **기본 블로그**: `blog-editor`는 프로젝트 `.claude/skills/blog-editor/project.json`.
- **기본 ERD 프로젝트**: `erd-design`은 프로젝트 `.claude/skills/erd-design/project.json` (`projectId`/`projectName`/`targetDbms`). 특정 프로젝트 ID가 들어가므로 플러그인에 번들하지 않습니다.
- **플러그인 내부 파일 참조**: `ddl_export.py` 등은 `${CLAUDE_PLUGIN_ROOT}/skills/erd-design/...` 로 참조하고, DDL 산출물(`temp/erd-export/`)은 명령을 실행한 프로젝트 cwd에 생성됩니다.
