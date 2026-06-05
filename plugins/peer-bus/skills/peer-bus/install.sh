#!/usr/bin/env bash
# install.sh — peer-bus 를 개발자 PC 한 대에 설치 (mac / linux / WSL2 공통)
#
#   · 런타임을 ~/.peer-bus/ 에 self-contained 로 materialize
#   · PC별 로컬 토큰 생성 (팀 공유 시크릿 배포 불필요)
#   · @modelcontextprotocol/sdk 설치
#   · 백엔드/프론트 레포에 붙여넣을 .mcp.json 스니펫 출력
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PEER_BUS_HOME="${PEER_BUS_HOME:-$HOME/.peer-bus}"

echo "▶ peer-bus 설치 → $PEER_BUS_HOME"

command -v bun  >/dev/null 2>&1 || { echo "✗ bun 이 필요합니다. https://bun.sh 설치 후 다시 실행."; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "✗ curl 이 필요합니다."; exit 1; }

mkdir -p "$PEER_BUS_HOME/bin"
cp "$SRC/bin/peer-bus-hub.ts"  "$PEER_BUS_HOME/bin/"
cp "$SRC/bin/peer-bus-node.ts" "$PEER_BUS_HOME/bin/"
cp "$SRC/bin/peer-bus-node"    "$PEER_BUS_HOME/bin/"
chmod +x "$PEER_BUS_HOME/bin/peer-bus-node"

# PC별 로컬 토큰 (이미 있으면 보존)
if [ ! -s "$PEER_BUS_HOME/token" ]; then
  ( umask 077; openssl rand -hex 32 > "$PEER_BUS_HOME/token" )
  echo "✓ 로컬 토큰 생성 (~/.peer-bus/token, 권한 600)"
else
  echo "✓ 기존 로컬 토큰 유지"
fi

# SDK 설치 (bin/ 상위에서 node_modules 해석)
( cd "$PEER_BUS_HOME" && [ -f package.json ] || bun init -y >/dev/null 2>&1 || true )
( cd "$PEER_BUS_HOME" && bun add @modelcontextprotocol/sdk >/dev/null 2>&1 ) && echo "✓ @modelcontextprotocol/sdk 설치"

WRAPPER="$PEER_BUS_HOME/bin/peer-bus-node"
cat <<EOF

✅ 설치 완료.

──────────────────────────────────────────────────────────────
다음 .mcp.json 스니펫을 각 레포 루트에 추가하세요.
같은 프로젝트의 backend·front 는 NAME 만 다르고 PROJECT 는 같습니다(같은 버스에 모임).

[ 백엔드 레포 / .mcp.json ]
{
  "mcpServers": {
    "peer-bus": {
      "command": "$WRAPPER",
      "env": { "NAME": "backend", "PROJECT": "blogn", "PEER_BUS_MODE": "poll" }
    }
  }
}

[ 프론트 레포 / .mcp.json ]
{
  "mcpServers": {
    "peer-bus": {
      "command": "$WRAPPER",
      "env": { "NAME": "front:blogn", "PROJECT": "blogn", "PEER_BUS_MODE": "poll" }
    }
  }
}
──────────────────────────────────────────────────────────────
· 프로젝트 = 버스 단위(포트 분리): PROJECT 가 다르면 다른 포트의 허브에 붙어 구조적으로 격리됩니다.
  무재부팅으로 프로젝트를 갈아끼워도 이전 프로젝트의 핀·broadcast 가 새지 않습니다.
  같은 프로젝트의 backend·front 는 반드시 PROJECT 값을 동일하게 두세요(둘이 한 버스에서 만나야 함).
· 첫 CC 세션이 뜨면 해당 PROJECT 포트의 허브가 자동 기동됩니다 (별도 실행 불필요).
· 포트는 PROJECT 에서 결정론적으로 파생됩니다(default=:8900). 서로 다른 프로젝트가 같은 포트로
  충돌하면 env 에 "HUB_PORT":"8901" 처럼 명시해 직접 박으면 됩니다(명시값이 항상 우선).
· poll 모드라 --dangerously-load-development-channels 불필요. 세션은 유휴 시 read_messages 를 호출합니다.
· 교체형 프론트(front:erd 등)는 그 레포의 NAME 만 바꾸면 됩니다.
· push(Channels) 모드로 올릴 땐 env 를 "PEER_BUS_MODE":"push" 로 바꾸고 CC 를
  --dangerously-load-development-channels 로 기동하세요.
EOF
