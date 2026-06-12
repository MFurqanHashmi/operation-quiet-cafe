import type { SessionState } from "./types";

const J = { "Content-Type": "application/json" };

async function post(url: string, body: any) {
  const r = await fetch(url, { method: "POST", headers: J, body: JSON.stringify(body) });
  return r.json();
}

export const api = {
  createSession: (): Promise<SessionState> =>
    fetch("/api/session", { method: "POST", headers: J, body: "{}" }).then((r) => r.json()),

  getSession: (sid: string): Promise<SessionState> =>
    fetch(`/api/session/${sid}`).then((r) => r.json()),

  reset: (sid: string): Promise<SessionState> =>
    post("/api/reset", { session_id: sid }),

  enter: (sid: string, n: number) =>
    post(`/api/mission/${n}/enter`, { session_id: sid }),

  action: (sid: string, n: number, action: string, params: any = {}) =>
    post(`/api/mission/${n}/action`, { session_id: sid, action, params }),

  verify: (sid: string, n: number, code: string) =>
    post(`/api/mission/${n}/verify`, { session_id: sid, code }),
};
