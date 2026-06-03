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
다음 .mcp.json 스니펫을 각 레포 루트에 추가하세요 (NAME 만 다릅니다).

[ 백엔드 레포 / .mcp.json ]
{
  "mcpServers": {
    "peer-bus": {
      "command": "$WRAPPER",
      "env": { "NAME": "backend", "PEER_BUS_MODE": "poll" }
    }
  }
}

[ 프론트 레포 / .mcp.json ]
{
  "mcpServers": {
    "peer-bus": {
      "command": "$WRAPPER",
      "env": { "NAME": "front:blogn", "PEER_BUS_MODE": "poll" }
    }
  }
}
──────────────────────────────────────────────────────────────
· 첫 CC 세션이 뜨면 허브가 자동 기동됩니다 (별도 실행 불필요).
· poll 모드라 --dangerously-load-development-channels 불필요. 세션은 유휴 시 read_messages 를 호출합니다.
· 교체형 프론트(front:erd 등)는 그 레포의 NAME 만 바꾸면 됩니다.
· push(Channels) 모드로 올릴 땐 env 를 "PEER_BUS_MODE":"push" 로 바꾸고 CC 를
  --dangerously-load-development-channels 로 기동하세요.
EOF
