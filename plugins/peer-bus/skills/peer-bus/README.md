# peer-bus 배포판 — 개발자 PC별 자체완결 설치 (mac / linux / WSL2)

원본 peer-bus(허브 + 노드 + 협업 프로토콜)에 **"개발자 한 명 = PC 한 대 안에 백엔드 세션 + 프론트
세션 공존"** 토폴로지에 맞춘 배포 레이어를 얹은 묶음이다. 모든 트래픽이 한 PC의 `127.0.0.1`
안에서만 돌기 때문에 **네트워크 노출이 없고, 팀 공유 시크릿 배포가 필요 없다**(토큰은 PC마다 자동 생성).

```
  [개발자 PC 1대 = 프로젝트마다 독립된 버스 (PROJECT 에서 포트 파생)]

   프로젝트 blogn ── hub :8991        프로젝트 erd ── hub :8924
        ↑          ↑                      ↑          ↑
   backend CC   front:blogn CC        backend CC   front:erd CC
   PROJECT=blogn  PROJECT=blogn        PROJECT=erd   PROJECT=erd
        └ 한 버스(같은 PROJECT) ┘            └ 다른 포트로 구조적 격리 ┘
        └────── 계약 본문은 공유 BlogN(back.softn.kr), 버스는 refPostId 트리거만 ──────┘
```

같은 프로젝트의 backend·front 는 **같은 `PROJECT`** 값을 공유해 한 버스(포트)에 모이고, 다른
프로젝트는 다른 포트의 허브로 갈려 **핀 인덱스·broadcast 가 구조적으로 격리**된다. PC 재부팅 없이
하루에도 여러 번 프로젝트를 갈아끼워도 이전 프로젝트의 계약 포인터가 새지 않는다.

## 구성
```
peer-bus/
├─ bin/
│  ├─ peer-bus-hub.ts    # 허브(원본 + 토큰 파일 폴백 + /drain·/pins)
│  ├─ peer-bus-node.ts   # 노드(원본 push + poll 모드 + read_messages 도구)
│  └─ peer-bus-node      # 실행 진입점(bash): 토큰 확보 + 허브 자동 보장 + bun 실행
├─ install.sh            # ~/.peer-bus 로 설치 + 토큰 생성 + SDK + 스니펫 출력
├─ snippets/             # 레포별 .mcp.json (backend / front)
├─ CLAUDE.protocol.md    # 각 레포 CLAUDE.md 에 붙일 협업 규칙(+ §6 폴링 루프)
└─ .claude-plugin/plugin.json
```

## 설치 (개발자 각자 자기 PC에서 1회)
```bash
bash install.sh
```
- `bun`·`curl`·`openssl` 필요. `~/.peer-bus/` 에 런타임을 materialize 하고 PC별 토큰을 생성한다.
- 출력된 `.mcp.json` 스니펫을 **백엔드 레포 / 프론트 레포** 루트에 각각 추가한다(`NAME`만 다름).
- `CLAUDE.protocol.md` 내용을 두 레포의 `CLAUDE.md` 에 붙여넣는다.

## 동작 원리 (배포 관점 핵심 4가지)
1. **프로젝트 = 버스 단위(포트 분리)** — wrapper 가 `.mcp.json` 의 `PROJECT` 값에서 허브 포트를
   결정론적으로 파생한다(`default`=`:8900` 하위 호환, 그 외 `:8901`–`:8999`). 같은 `PROJECT` 면 같은
   포트라 같은 버스에서 만나고, 다른 `PROJECT` 면 다른 허브로 갈려 핀·broadcast 가 구조적으로 격리된다.
   서로 다른 프로젝트가 같은 포트로 충돌하면 env 에 `HUB_PORT` 를 명시해 직접 박는다(명시값이 항상 우선).
2. **허브 자동 보장** — wrapper 가 세션 시작 때 그 포트의 `/peers` 를 probe하고, 죽어 있으면
   `( nohup bun hub.ts & )` 서브셸로 detached 기동한다. 부모 세션이 죽어도 허브는 생존.
   같은 포트에 두 세션이 동시에 떠도 포트 바인딩이 mutex라 진 쪽은 `EADDRINUSE` 로 즉시 종료된다(별도 락 불필요).
3. **토큰 = PC 로컬 자동 생성** — `~/.peer-bus/token`(권한 600). 팀끼리 토큰을 주고받지 않는다.
   환경변수 `BUS_TOKEN` 이 있으면 그쪽이 우선.
4. **NAME = 레포별** — `.mcp.json` env 로 백엔드 레포=`backend`, 프론트 레포=`front:blogn`. NAME 은
   프로젝트(버스) 안에서만 유니크하면 되므로, 다른 프로젝트의 `backend` 와는 애초에 만날 일이 없다.
   교체형 프론트는 그 레포의 NAME만 `front:erd` 등으로 바꾼다.

## 모드
| 모드 | 개발 플래그 | 수신 방식 | 용도 |
|------|-------------|-----------|------|
| `poll` (기본) | 불필요 | `read_messages` 도구 호출 | 파일럿 권장 |
| `push` | `--dangerously-load-development-channels` | `<channel>` 자동 PUSH | 안정화 후 승격 |

`.mcp.json` 의 `PEER_BUS_MODE` 로 전환한다.

## WSL2 주의
- 백엔드 CC · 프론트 CC · 허브가 **모두 같은 WSL2 distro 안에서** 돌아야 `localhost` 가 일치한다.
  Windows-native CC 가 WSL 안 허브에 붙는 구성은 금지(포트 경계가 쪼개짐).
- `~/.peer-bus/` 는 distro 내부 홈에 둔다(`/mnt/c/...` 금지 — 권한·성능 문제).
- distro 종료 시 허브도 종료되지만, 다음 세션이 자동 재기동한다(in-memory 큐만 유실, 핀은 재등록 replay 복구).

## 롤아웃 순서
1. 각 개발자 `bash install.sh`
2. 백엔드/프론트 레포에 `.mcp.json` + `CLAUDE.md` 프로토콜 추가
3. BlogN 에 `agent-contracts` / `agent-responses` 분류 + 개발자별 네임스페이스(태그 `@id` 등) 세팅
4. 한 PC에서 backend ↔ front:blogn 계약 1회 왕복 검증
5. 안정화 후 → `push` 승격 + 인젝션 방어 계층 (Redis 영속화는 단일 PC라 후순위)
