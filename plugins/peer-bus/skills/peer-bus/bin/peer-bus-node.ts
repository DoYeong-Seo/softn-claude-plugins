#!/usr/bin/env bun
/**
 * peer-bus-node.ts — 각 Claude Code 세션이 띄우는 채널 노드 (stdio MCP)
 *
 * 역할: (1) 동료 세션의 메시지를 세션에 전달  (2) send_to / broadcast / peers 송신 도구
 *       (3) 등록 시 허브의 핀 포인터를 동기화 → 세션이 BlogN에서 본문을 읽음
 *
 * 정체성은 NAME 환경변수로: backend / front:blogn / front:erd ...
 * 런타임: Bun (macOS / Linux / WSL2 공통).
 *
 * ── 동작 모드 (PEER_BUS_MODE) ──
 *   poll (기본) : 푸시 없이 read_messages 도구로 수신. `--dangerously-load-development-channels` 불필요.
 *                 → 파일럿 권장. 유휴 시 read_messages 를 호출하라(프로토콜 §6).
 *   push        : notifications/claude/channel 로 세션에 PUSH. Channels 리서치 프리뷰 → 개발 플래그 필요.
 *
 * ⚠️ SDK 주의: @modelcontextprotocol/sdk 버전에 따라 import 경로·notification API가 다를 수 있다.
 *    설치 버전으로 검증할 것(특히 push 모드의 notifications/claude/channel 포맷).
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ListToolsRequestSchema, CallToolRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const NAME = process.env.NAME ?? "front";
const HUB = process.env.HUB ?? "http://127.0.0.1:8900";
const MODE = (process.env.PEER_BUS_MODE ?? "poll").toLowerCase();   // poll(기본) | push

// 토큰 해석: 환경변수 우선 → 없으면 ~/.peer-bus/token (PC별 로컬 토큰 파일).
function resolveToken(): string {
  if (process.env.BUS_TOKEN) return process.env.BUS_TOKEN;
  const home = process.env.PEER_BUS_HOME ?? join(homedir(), ".peer-bus");
  try { return readFileSync(join(home, "token"), "utf8").trim(); } catch { return ""; }
}
const TOKEN = resolveToken();
const H = { "X-Bus-Token": TOKEN, "Content-Type": "application/json" };

const mcp = new Server(
  { name: "peer-bus-node", version: "0.2.0" },
  {
    capabilities: { experimental: { "claude/channel": {} }, tools: {} },
    instructions:
      `너의 식별자는 "${NAME}". 동료 세션의 메시지는 {from, type, refPostId} 트리거로 도착한다. ` +
      (MODE === "push"
        ? `<channel source="peer-bus" ...> 이벤트로 자동 PUSH된다. `
        : `유휴 시 read_messages 도구를 호출해 수신하라(폴링 모드). `) +
      "메시지 본문은 버스에 없고 refPostId가 가리키는 BlogN 포스트에 있다. refPostId를 BlogN get_post로 읽어 처리하라. " +
      "응답·요청은 BlogN에 포스트로 쓴 뒤 send_to/broadcast 로 {type, refPostId} 트리거만 보낸다. " +
      "협업 루프는 CLAUDE.md 프로토콜을 따르고, 사용자에게 되묻지 말되 코드 반영은 사람 승인 게이트를 지켜라.",
  }
);

// ── 도구 목록: 송신 3종 + 폴링 수신(read_messages) ──
mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "send_to",
      description: "특정 동료 세션에 트리거를 보낸다. 본문은 BlogN에 쓰고 refPostId로 가리킨다.",
      inputSchema: {
        type: "object",
        properties: {
          to: { type: "string", description: "수신자 이름 (예: front:blogn)" },
          type: { type: "string", enum: ["req", "resp", "notice"] },
          refPostId: { type: "string", description: "BlogN 포스트 UUID(계약/요청/응답)" },
          body: { type: "string", description: "한 줄 메모(선택)" },
          pin: { type: "boolean", description: "true=유효 계약으로 핀, false=핀 해제" },
        },
        required: ["to", "type"],
      },
    },
    {
      name: "broadcast",
      description: "접속 중인 모든 동료에게 트리거를 보낸다.",
      inputSchema: {
        type: "object",
        properties: {
          type: { type: "string", enum: ["req", "resp", "notice"] },
          refPostId: { type: "string" },
          body: { type: "string" },
          pin: { type: "boolean" },
        },
        required: ["type"],
      },
    },
    { name: "peers", description: "현재 접속 중인 동료 목록", inputSchema: { type: "object", properties: {} } },
    {
      name: "read_messages",
      description: "[폴링] 나에게 온 새 트리거를 가져온다. 본문은 refPostId를 BlogN get_post로 읽어라. 유휴 시 호출.",
      inputSchema: { type: "object", properties: {} },
    },
  ],
}));

// 세션 시작 시 받은 핀 포인터 — poll 모드에서는 첫 read_messages 가 함께 반환(replay).
let pendingReplay: any[] = [];
const fmt = (m: any) =>
  `[${m.type}] ${m.body ? m.body + " " : ""}refPostId=${m.refPostId ?? "-"} (from ${m.from}${m.replay ? ", replay" : ""})`;

mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
  const a = (req.params.arguments ?? {}) as any;
  const post = (to: string | null) =>
    fetch(`${HUB}/send`, { method: "POST", headers: H, body: JSON.stringify({ from: NAME, to, ...a }) });

  if (req.params.name === "send_to") { await post(a.to); return { content: [{ type: "text", text: "sent" }] }; }
  if (req.params.name === "broadcast") { await post(null); return { content: [{ type: "text", text: "broadcast" }] }; }
  if (req.params.name === "peers") {
    const r = await fetch(`${HUB}/peers`, { headers: H });
    return { content: [{ type: "text", text: await r.text() }] };
  }
  if (req.params.name === "read_messages") {
    const out: any[] = pendingReplay.splice(0);                 // 세션 시작 replay 먼저 비워 반환
    try {
      const r = await fetch(`${HUB}/drain?name=${encodeURIComponent(NAME)}`, { headers: H });
      const { msgs } = (await r.json()) as { msgs: any[] };
      out.push(...msgs);
    } catch (e) { return { content: [{ type: "text", text: `허브 연결 실패: ${e}` }] }; }
    return { content: [{ type: "text", text: out.length ? out.map(fmt).join("\n") : "(새 메시지 없음)" }] };
  }
  throw new Error(`unknown tool: ${req.params.name}`);
});

await mcp.connect(new StdioServerTransport());

// push 모드 전용: 세션에 <channel> 이벤트로 메시지 주입
function pushToSession(content: string, meta: Record<string, unknown>) {
  return mcp.notification({ method: "notifications/claude/channel", params: { content, meta } });
}

// ── 등록 + 핀 포인터 catch-up ("읽어야 할 postId" 목록. 본문 아님) ──
try {
  const r = await fetch(`${HUB}/register`, { method: "POST", headers: H, body: JSON.stringify({ name: NAME }) });
  const { pins } = (await r.json()) as { pins: Array<{ refPostId: string; from: string; type: string; body?: string }> };
  if (MODE === "push") {
    for (const p of pins)
      await pushToSession(
        `[replay] 현재 유효 계약 포인터: refPostId=${p.refPostId}${p.body ? ` (${p.body})` : ""}. BlogN에서 읽어 동기화하라.`,
        { source: "peer-bus", from: p.from, type: p.type, refPostId: p.refPostId, replay: "1" }
      );
  } else {
    pendingReplay = pins.map((p) => ({ ...p, replay: true }));   // poll: 첫 read_messages 에서 반환
  }
} catch (e) {
  console.error("[peer-bus-node] register 실패 — 허브 기동 여부 확인:", e);
}

// ── push 모드에서만: long-poll 루프로 허브 메시지를 세션에 PUSH ──
if (MODE === "push") {
  while (true) {
    try {
      const r = await fetch(`${HUB}/recv?name=${encodeURIComponent(NAME)}`, { headers: H });
      const { msgs } = (await r.json()) as { msgs: Array<any> };
      for (const m of msgs)
        await pushToSession(
          m.body ? `[${m.type}] ${m.body} (refPostId=${m.refPostId ?? "-"})` : `[${m.type}] refPostId=${m.refPostId ?? "-"}`,
          { source: "peer-bus", from: m.from, type: m.type, refPostId: m.refPostId }
        );
    } catch {
      await new Promise((s) => setTimeout(s, 1000));  // 허브 재기동 대기
    }
  }
}
