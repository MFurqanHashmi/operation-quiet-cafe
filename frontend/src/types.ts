export type Actor = "alice" | "bob" | "eve";

export interface SessionState {
  session_id: string;
  current_mission: number;
  completed: number[];
  codes_verified: number[];
  total: number;
}

export interface WSEvent {
  type: string;
  room: string;
  ts: number;
  payload: any;
}

export interface ChatBubble {
  id: string;
  from: Actor | "station" | "vault";
  to?: string;
  text: string;
  encrypted: boolean;
}

export interface Packet {
  id: string;
  from: string;
  to: string;
  encrypted: boolean;
  preview?: string | null;
  cipher?: string | null;
}

