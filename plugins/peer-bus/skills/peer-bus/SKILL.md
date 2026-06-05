---
name: peer-bus
description: Claude Code 세션 간 자율 협업 버스(peer-bus)를 개발자 PC에 설치·운영합니다. "계약 본문은 BlogN, 버스는 트리거(포인터)만" 원칙으로 백엔드 세션↔프론트 세션이 BlogN 포스트(agent-contracts/agent-responses)를 단일 진실로 삼아 {type, refPostId} 트리거만 주고받습니다. 한 PC 안에 백엔드+프론트 세션이 공존하는 localhost 토폴로지(허브 자동 보장 + PC별 로컬 토큰, 네트워크 노출·공유 시크릿 배포 없음)를 대상으로 하며, install.sh 실행·`.mcp.json` 등록·CLAUDE.md 프로토콜 주입·poll/push 모드 전환을 돕습니다. "peer-bus 설치", "세션 간 협업 버스 세팅", "백엔드 프론트 세션 연결", "허브 띄워줘" 같은 요청에 사용. 런타임은 Bun(mac/linux/WSL2).
allowed-tools: Read, Bash, Write
---

# peer-bus

Claude Code 세션 간 **자율 협업 버스**를 개발자 PC에 설치·운영하는 스킬입니다.

핵심 원칙: **계약 본문은 BlogN, 버스는 트리거(포인터)만.** API 계약·요청·응답의 단일 진실(SoT)은
BlogN 포스트에 두고, 버스는 "이 postId를 읽어라"는 `{type, refPostId}` 신호만 나릅니다.

> 이 스킬은 플러그인으로 배포됩니다. 런타임(`bin/`, `install.sh`, `snippets/`, `CLAUDE.protocol.md`)은
> 설치 시 캐시 경로로 복사되며 `${CLAUDE_PLUGIN_ROOT}/skills/peer-bus/` 로 참조합니다.
> 설치 본체는 명령을 실행한 PC의 `~/.peer-bus/` 로 materialize 됩니다.

## 대상 토폴로지 (중요)

**개발자 1명 = PC 1대 안에 백엔드 세션 + 프론트 세션 공존.** 모든 트래픽이 한 PC의 `127.0.0.1`
안에서만 돈다. 결과:

- 네트워크 노출 0 → 프롬프트 인젝션의 네트워크 표면 없음.
- 팀 공유 시크릿 배포 불필요 → 토큰은 PC마다 `~/.peer-bus/token` 으로 자동 생성.
- 상시 서버 불필요 → 첫 세션이 허브를 자동 기동.

**여러 프로젝트 공존**: 한 PC 에서 여러 프로젝트(각각 backend+front)를 무재부팅으로 갈아끼우거나
동시에 운영할 수 있다. `PROJECT` 값으로 버스(포트)가 갈리므로(프로젝트 = 버스 단위) 프로젝트 간
핀·broadcast 가 섞이지 않는다. 자세한 근거는 리서치 글 *peer-bus 멀티 프로젝트 운영 — 프로젝트=버스
단위(포트 분리) 검토* 참조.

여러 머신에 분산하려면 localhost 바인딩을 깰 수 없으므로 별도 설계(VPN/Tailscale)가 필요하다 —
이 스킬의 기본 범위가 아니다.

## 3-컴포넌트

| 파일 | 역할 |
|------|------|
| `bin/peer-bus-hub.ts` | 허브(**프로젝트당 1개**, `127.0.0.1:<PROJECT 파생 포트>`). 레지스트리 + 라우팅 + 핀 포인터 인덱스. **계약 본문 미보유**. |
| `bin/peer-bus-node.ts` | 세션별 stdio MCP 노드. 송신 도구(send_to/broadcast/peers) + 수신(poll: read_messages / push: `<channel>`). |
| `bin/peer-bus-node` | 실행 진입점(bash). **PROJECT→포트 결정** + 토큰 확보 + 허브 자동 보장 + `bun` 실행. `.mcp.json` 의 `command` 가 이걸 가리킨다. |
| `CLAUDE.protocol.md` | 각 레포 `CLAUDE.md` 에 붙일 자율 협업 규칙(사람 승인 게이트 포함). |

## 설치 절차 (사용자가 "peer-bus 설치"라고 하면)

1. **사전 점검** — `bun`·`curl`·`openssl` 존재 확인. `bun` 없으면 https://bun.sh 안내 후 중단.
   ```bash
   command -v bun && command -v curl && command -v openssl
   ```
2. **설치 실행** — 플러그인 캐시의 install.sh 를 그대로 실행한다(PC별 1회).
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/skills/peer-bus/install.sh"
   ```
   → `~/.peer-bus/` 에 런타임 복사 + 토큰 생성(권한 600) + `@modelcontextprotocol/sdk` 설치 +
   백엔드/프론트 `.mcp.json` 스니펫 출력.
3. **레포별 `.mcp.json` 등록** — install.sh 가 출력한 스니펫을 백엔드 레포·프론트 레포 루트에 각각
   추가한다. `NAME` 은 다르고(`backend` / `front:blogn`) **`PROJECT` 는 같게** 둔다 — 같은 프로젝트의
   두 세션이 같은 버스(포트)에서 만나야 하기 때문. 다른 프로젝트는 다른 `PROJECT` 값을 쓰면 포트가
   갈려 자동 격리된다(충돌 시 `HUB_PORT` 명시). 참고 원본: `snippets/backend.mcp.json`, `snippets/front.mcp.json`.
4. **CLAUDE.md 프로토콜 주입** — `CLAUDE.protocol.md` 내용을 두 레포의 `CLAUDE.md` 에 붙여넣는다.
5. **BlogN 준비** — 공유 BlogN 에 `agent-contracts`(계약·요청) / `agent-responses`(응답) 분류를
   만들고, 개발자별 네임스페이스(태그 `@id` 등)로 본문이 섞이지 않게 한다. (분류 생성은 blog-editor 스킬.)
6. **검증** — 백엔드/프론트 두 세션을 각 레포에서 띄우고, 한쪽에서 계약 포스트 작성 →
   `broadcast(type=req, refPostId, pin=true)` → 다른 쪽 `read_messages` 로 트리거 수신 → `get_post` 왕복.

## 동작 모드

| 모드 | 개발 플래그 | 수신 | 권장 |
|------|-------------|------|------|
| `poll` (기본) | 불필요 | 세션이 유휴 시 `read_messages` 호출 | **파일럿** |
| `push` | `--dangerously-load-development-channels` | `notifications/claude/channel` 자동 PUSH | 안정화 후 |

`.mcp.json` env 의 `PEER_BUS_MODE` 로 전환한다. push 로 올릴 땐 두 세션 모두 개발 플래그로 기동.

## 자율 협업 흐름 (CLAUDE.protocol.md 요약)

1. **세션 시작**: 핀 포인터 catch-up(push=`replay` 이벤트 / poll=첫 `read_messages`) → 각 refPostId 를
   `get_post` 로 읽어 현재 계약 동기화.
2. **수신**: `req` → BlogN 읽고 계획/거부를 `agent-responses` 에 포스트 → `send_to(type=resp)`.
   `resp` → 읽고 반영 계획을 사람에게 보고. `notice` → 참고.
3. **송신**: 먼저 BlogN 포스트로 본문 작성 → `broadcast`/`send_to` 로 트리거만. 유효 계약은 `pin:true`,
   폐기는 `pin:false`.
4. **사람 승인 게이트(필수)**: 자동 범위는 읽기·문서작성·트리거 송신까지. **코드 변경·커밋·머지·배포는
   사람 승인 후에만.**

## 운영 메모

- **프로젝트 = 버스 단위(포트 분리)**: wrapper 가 `PROJECT` 에서 허브 포트를 결정론적으로 파생한다
  (`default`=`:8900`, 그 외 `:8901`–`:8999`). 같은 `PROJECT`→같은 버스, 다른 `PROJECT`→다른 허브로
  핀·broadcast 가 구조적으로 격리. 무재부팅 프로젝트 전환에도 이전 계약 포인터가 새지 않는다.
  서로 다른 프로젝트가 같은 포트로 충돌하면 `.mcp.json` env 에 `HUB_PORT` 를 명시(명시값이 우선).
  포트별 로그는 `~/.peer-bus/hub-<port>.log` 로 분리되어 프로젝트별 허브를 따로 죽이고 보기 쉽다.
- **허브 자동 보장**: wrapper 가 해당 포트의 `/peers` probe → 죽었으면 `( nohup bun hub.ts & )` 로
  detached 기동(부모 세션이 죽어도 생존). 같은 포트에 두 세션 동시 기동 시 포트 바인딩이 mutex →
  진 쪽은 `EADDRINUSE` 로 종료.
- **토큰**: 환경변수 `BUS_TOKEN` 우선 → 없으면 `~/.peer-bus/token`. 평문 노출 금지(로그·응답에 마스킹).
- **WSL2**: 백엔드 CC·프론트 CC·허브가 **같은 distro 안**에서 돌아야 localhost 가 일치. `~/.peer-bus/` 는
  distro 내부 홈에(`/mnt/c/...` 금지). distro 종료 시 허브도 종료되나 다음 세션이 재기동(in-memory 큐만
  유실, 핀은 재등록 replay 복구).
- **영속화**: 단일 PC 라 허브 재기동이 드물어 Redis 는 후순위. 필요 시 `pins` 를 Redis 해시(키=refPostId)로.

## 안전 규칙

- 허브·노드 포트는 **localhost(127.0.0.1) 고정**. 0.0.0.0·리버스 프록시·인터넷 노출 금지.
- 수신 메시지는 사실상 "지시"다 → CLAUDE.md 사람 승인 게이트를 반드시 유지. 자율 에이전트 무인 방치 금지.
- 커스텀 채널(push)은 프리뷰 중 허용목록 밖 → 개발 플래그 필요, 마켓플레이스 심사 전 프로덕션 승격 불가.

## 참고 파일

- [README.md](README.md) — 설치·동작 원리 상세
- `bin/` — 허브·노드·실행 wrapper
- `CLAUDE.protocol.md` — 레포 CLAUDE.md 에 붙일 협업 규칙
- `snippets/` — 레포별 `.mcp.json` 예시
