import React, { createContext, useContext, useEffect, useReducer, useRef, useCallback } from "react";
import type { SessionState, WSEvent, ChatBubble, Packet, Actor } from "./types";
import { api } from "./api";

type Phase = "coldopen" | "playing" | "closed";

interface State {
  session: SessionState | null;
  phase: Phase;
  mission: number;
  bubbles: ChatBubble[];
  packets: Packet[];
  connected: boolean;
  eveNoise: boolean;
  keyExposed: boolean;
  bobFingerprint: string | null;
  stationLog: string[];
  flash: { kind: string; ts: number } | null;
}

const initial: State = {
  session: null,
  phase: "coldopen",
  mission: 1,
  bubbles: [],
  packets: [],
  connected: false,
  eveNoise: false,
  keyExposed: false,
  bobFingerprint: null,
  stationLog: [],
  flash: null,
};

type Action =
  | { t: "SESSION"; s: SessionState }
  | { t: "PHASE"; p: Phase }
  | { t: "MISSION"; n: number }
  | { t: "WS"; e: WSEvent }
  | { t: "CONNECTED"; v: boolean }
  | { t: "CLEAR_ROOM" };

const cap = <T,>(arr: T[], n = 6) => arr.slice(Math.max(0, arr.length - n));

function reducer(st: State, a: Action): State {
  switch (a.t) {
    case "SESSION":
      return { ...st, session: a.s };
    case "PHASE":
      return { ...st, phase: a.p };
    case "MISSION":
      return { ...st, mission: a.n };
    case "CONNECTED":
      return { ...st, connected: a.v };
    case "CLEAR_ROOM":
      return { ...st, bubbles: [], packets: [], eveNoise: false, keyExposed: false, stationLog: [] };
    case "WS": {
      const { type, payload } = a.e;
      switch (type) {
        case "actor.message":
          return {
            ...st,
            bubbles: cap([
              ...st.bubbles,
              {
                id: `${Date.now()}-${Math.random()}`,
                from: payload.from as Actor,
                to: payload.to,
                text: payload.text,
                encrypted: !!payload.encrypted,
              },
            ]),
          };
        case "packet.sent":
          return {
            ...st,
            packets: cap([
              ...st.packets,
              {
                id: payload.id || `${Date.now()}`,
                from: payload.from,
                to: payload.to,
                encrypted: !!payload.encrypted,
                preview: payload.preview,
                cipher: payload.cipher,
              },
            ], 8),
          };
        case "eve.capture":
          return { ...st, eveNoise: !!payload.noise };
        case "key.exposed":
          return { ...st, keyExposed: true, flash: { kind: "exposed", ts: Date.now() } };
        case "key.published":
          return { ...st, bobFingerprint: payload.pubkey_fingerprint };
        case "ssh.step":
          return { ...st, stationLog: [...st.stationLog, payload.text] };
        case "ssh.login_success":
          return { ...st, flash: { kind: "ssh_ok", ts: Date.now() } };
        case "door.warning":
          return { ...st, flash: { kind: "warning", ts: Date.now() } };
        case "door.verified":
        case "passkey.verified":
          return { ...st, flash: { kind: "granted", ts: Date.now() } };
        default:
          return st;
      }
    }
    default:
      return st;
  }
}

interface Ctx {
  state: State;
  start: () => Promise<void>;
  enter: (n: number) => Promise<void>;
  doAction: (action: string, params?: any) => Promise<any>;
  verify: (code: string) => Promise<any>;
  reset: () => Promise<void>;
  goPhase: (p: Phase) => void;
  goMission: (n: number) => void;
}

const StoreCtx = createContext<Ctx>(null as any);
export const useStore = () => useContext(StoreCtx);

const SID_KEY = "qc_session_id";

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initial);
  const wsRef = useRef<WebSocket | null>(null);

  const connectWS = useCallback((sid: string) => {
    if (wsRef.current) wsRef.current.close();
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws?session=${sid}`);
    ws.onopen = () => dispatch({ t: "CONNECTED", v: true });
    ws.onclose = () => dispatch({ t: "CONNECTED", v: false });
    ws.onmessage = (m) => {
      try {
        dispatch({ t: "WS", e: JSON.parse(m.data) });
      } catch {}
    };
    wsRef.current = ws;
  }, []);

  const bind = useCallback((s: SessionState) => {
    dispatch({ t: "SESSION", s });
    localStorage.setItem(SID_KEY, s.session_id);
    connectWS(s.session_id);
  }, [connectWS]);

  const start = useCallback(async () => {
    const existing = localStorage.getItem(SID_KEY);
    if (existing) {
      const s = await api.getSession(existing);
      if (s && (s as any).session_id) {
        bind(s);
        return;
      }
    }
    bind(await api.createSession());
  }, [bind]);

  useEffect(() => { start(); }, [start]);

  const enter = useCallback(async (n: number) => {
    if (!state.session) return;
    dispatch({ t: "CLEAR_ROOM" });
    dispatch({ t: "MISSION", n });
    await api.enter(state.session.session_id, n);
  }, [state.session]);

  const doAction = useCallback(async (action: string, params: any = {}) => {
    if (!state.session) return { ok: false };
    return api.action(state.session.session_id, state.mission, action, params);
  }, [state.session, state.mission]);

  const verify = useCallback(async (code: string) => {
    if (!state.session) return { ok: false };
    const r = await api.verify(state.session.session_id, state.mission, code);
    if (r.correct && r.state) dispatch({ t: "SESSION", s: r.state });
    return r;
  }, [state.session, state.mission]);

  const reset = useCallback(async () => {
    if (!state.session) return;
    const s = await api.reset(state.session.session_id);
    bind(s);
    dispatch({ t: "CLEAR_ROOM" });
    dispatch({ t: "MISSION", n: 1 });
    dispatch({ t: "PHASE", p: "coldopen" });
  }, [state.session, bind]);

  const goPhase = (p: Phase) => dispatch({ t: "PHASE", p });
  const goMission = (n: number) => dispatch({ t: "MISSION", n });

  return (
    <StoreCtx.Provider value={{ state, start, enter, doAction, verify, reset, goPhase, goMission }}>
      {children}
    </StoreCtx.Provider>
  );
}
