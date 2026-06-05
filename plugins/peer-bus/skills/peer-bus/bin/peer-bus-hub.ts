#!/usr/bin/env bun
/**
 * peer-bus-hub.ts — 세션 간 MCP 버스의 중앙 허브 (프로젝트 = 버스 1개, localhost 상시 구동)
 *
 * 프로젝트 = 버스 단위(포트 분리). 한 PC 에 여러 프로젝트가 떠 있으면 HUB_PORT 가 다른 허브가
 * 프로젝트 수만큼 공존한다(예: 프로젝트 blogn=:8991, erd=:8924). 포트가 다르면 레지스트리·큐·핀
 * 인덱스가 통째로 분리되므로 프로젝트 간 핀 누적·broadcast 누수가 구조적으로 발생하지 않는다.
 * 포트는 wrapper(peer-bus-node)가 PROJECT 에서 파생해 HUB_PORT 로 넘긴다.
 *
 * 역할: (1) 접속자 레지스트리  (2) 메시지 라우팅(1:1 / broadcast)  (3) 핀 포인터 인덱스
 *
 * 설계 원칙 — 허브는 "계약 본문"을 들지 않는다.
 *   계약/요청/응답의 단일 진실(source of truth)은 BlogN 포스트다.
 *   허브가 보존하는 것은 "지금 유효한 계약이 어느 postId냐"는 포인터(refPostId)뿐이다.
 *
 * 보안: localhost 바인딩 + 공유 토큰. 절대 0.0.0.0 / 리버스 프록시로 노출하지 말 것.
 * 런타임: Bun (macOS / Linux / WSL2 공통). `bun peer-bus-hub.ts`
 *
 * ── 배포판 추가분(원본 대비) ──
 *   · 토큰을 BUS_TOKEN 미설정 시 ~/.peer-bus/token 에서 읽는 폴백 (PC별 로컬 토큰).
 *   · GET /drain  — long-poll 없이 즉시 큐를 비워 반환 (폴링 폴백 모드용).
 *   · GET /pins   — 현재 핀 포인터 목록 (세션 시작 동기화용).
 */

import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const PORT = Number(process.env.HUB_PORT ?? 8900);

// 토큰 해석: 환경변수 우선 → 없으면 ~/.peer-bus/token (PC별 로컬 토큰 파일).
function resolveToken(): string {
  if (process.env.BUS_TOKEN) return process.env.BUS_TOKEN;
  const home = process.env.PEER_BUS_HOME ?? join(homedir(), ".peer-bus");
  try { return readFileSync(join(home, "token"), "utf8").trim(); } catch { return ""; }
}
const TOKEN = resolveToken();
if (!TOKEN) throw new Error("BUS_TOKEN 환경변수 또는 ~/.peer-bus/token 이 필요합니다.");

// 메시지 봉투 — body는 "짧은 메모"용. 긴 계약 본문은 절대 싣지 않고 refPostId로 가리킨다.
type MsgType = "req" | "resp" | "notice";
type Msg = {
  from: string;
  to: string | null;          // null = broadcast
  type: MsgType;
  refPostId?: string;         // BlogN 포스트 UUID — 실제 계약/요청/응답은 여기에 있다
  body?: string;              // 한 줄 메모 (예: "blogn 검색 API 시그니처 변경")
  ts: number;
};

// 핀 포인터 인덱스: refPostId 기준 dedup → 같은 계약 갱신 시 최신값으로 덮어씀(무한 증가 없음)
type Pin = { refPostId: string; from: string; type: MsgType; body?: string; ts: number };

const peers = new Set<string>();                       // 현재 접속 중인 세션 이름
const queues = new Map<string, Msg[]>();               // name -> 미수신 메시지
const waiters = new Map<string, (m: Msg[]) => void>(); // name -> long-poll resolver
const pins = new Map<string, Pin>();                   // refPostId -> 포인터 (계약 본문 아님)

const q = (n: string) => (queues.has(n) ? queues.get(n)! : queues.set(n, []).get(n)!);

function deliver(to: string, m: Msg) {
  const w = waiters.get(to);
  if (w) { waiters.delete(to); w([m]); }   // 대기 중이면 즉시 깨움
  else q(to).push(m);                      // 아니면 큐에 적재
}

function json(data: unknown) {
  return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });
}

Bun.serve({
  port: PORT,
  hostname: "127.0.0.1",     // 외부 노출 금지
  idleTimeout: 0,            // long-poll를 위해 idle 타임아웃 해제
  async fetch(req) {
    if (req.headers.get("X-Bus-Token") !== TOKEN) return new Response("forbidden", { status: 403 });
    const url = new URL(req.url);

    // 등록 → 현재 핀 포인터 목록 반환(신규/교체 세션의 catch-up용). 본문 아님, postId 목록만.
    if (url.pathname === "/register" && req.method === "POST") {
      const { name } = (await req.json()) as { name: string };
      peers.add(name);
      return json({ pins: [...pins.values()] });
    }

    if (url.pathname === "/peers") return json({ peers: [...peers] });

    // 핀 포인터 목록만 조회(폴링 폴백 모드의 세션 시작 동기화용). 등록 부수효과 없음.
    if (url.pathname === "/pins") return json({ pins: [...pins.values()] });

    // 송신: to 있으면 1:1, 없으면 broadcast. pin=true면 핀 인덱스 upsert, pin=false면 해제.
    if (url.pathname === "/send" && req.method === "POST") {
      const b = (await req.json()) as Partial<Msg> & { pin?: boolean };
      const m: Msg = {
        from: b.from!, to: b.to ?? null, type: (b.type ?? "notice") as MsgType,
        refPostId: b.refPostId, body: b.body, ts: Date.now(),
      };
      if (m.refPostId && b.pin === true)
        pins.set(m.refPostId, { refPostId: m.refPostId, from: m.from, type: m.type, body: m.body, ts: m.ts });
      if (m.refPostId && b.pin === false) pins.delete(m.refPostId);  // 계약 폐기 시 해제

      if (m.to) deliver(m.to, m);
      else for (const p of peers) if (p !== m.from) deliver(p, m);   // 자기 자신 제외 broadcast
      return new Response("ok");
    }

    // 폴링 폴백 수신: long-poll 없이 쌓인 메시지를 즉시 비워 반환. (read_messages 도구가 호출)
    if (url.pathname === "/drain") {
      const name = url.searchParams.get("name");
      if (!name) return new Response("name required", { status: 400 });
      peers.add(name);                       // 폴링 모드도 명단에 올려 broadcast 수신
      const pend = q(name); queues.set(name, []);
      return json({ msgs: pend });
    }

    // 푸시 수신: long-poll. 쌓인 게 있으면 즉시, 없으면 최대 25초 대기. 연결 끊기면 자동 탈퇴.
    if (url.pathname === "/recv") {
      const name = url.searchParams.get("name");
      if (!name) return new Response("name required", { status: 400 });
      const pend = q(name);
      if (pend.length) { queues.set(name, []); return json({ msgs: pend }); }
      const msgs = await new Promise<Msg[]>((res) => {
        waiters.set(name, res);
        const t = setTimeout(() => { if (waiters.get(name) === res) { waiters.delete(name); res([]); } }, 25000);
        req.signal.addEventListener("abort", () => {       // 세션 종료 = 연결 끊김 → 명단에서 제거
          clearTimeout(t);
          if (waiters.get(name) === res) { waiters.delete(name); res([]); }
          peers.delete(name);
        });
      });
      return json({ msgs });
    }

    return new Response("not found", { status: 404 });
  },
});

console.error(`[peer-bus-hub] listening on http://127.0.0.1:${PORT}  (project bus · peers·routing·pin-index only)`);
