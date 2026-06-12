import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "../store";
import { ACTOR_LABEL } from "../missionsMeta";
import type { Actor } from "../types";
import FxLayer from "./FxLayer";

const COLORS: Record<string, string> = {
  alice: "var(--alice)",
  bob: "var(--bob)",
  eve: "var(--eve)",
};

function ActorPane({ actor, active }: { actor: Actor; active: boolean }) {
  const { state } = useStore();
  const mine = state.bubbles.filter((b) => b.from === actor).slice(-3);
  const isEve = actor === "eve";
  return (
    <motion.div
      className={`pane ${active ? "pane-active" : "pane-idle"}`}
      style={{ borderColor: COLORS[actor] }}
      animate={active ? { scale: 1.0, opacity: 1 } : { scale: 0.97, opacity: 0.78 }}
    >
      <div className="pane-head">
        <span className="pane-dot" style={{ background: COLORS[actor] }} />
        <span className="pane-name">{ACTOR_LABEL[actor]}</span>
        {active && <span className="pane-you">YOU</span>}
      </div>
      <div className="pane-body">
        {isEve && state.keyExposed && (
          <div className="eve-grab">caught the key!</div>
        )}
        {isEve && state.eveNoise && (
          <div className="eve-noise">
            recording&hellip; <span className="noise">a3f9c1 7b2e44 9d01ff</span>
          </div>
        )}
        <AnimatePresence>
          {mine.map((b) => (
            <motion.div
              key={b.id}
              className="bubble"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              {b.encrypted ? <span className="noise">{"\u2588\u2588\u2588 encrypted \u2588\u2588\u2588"}</span> : b.text}
            </motion.div>
          ))}
        </AnimatePresence>
        {mine.length === 0 && !isEve && <div className="pane-quiet">&mdash; quiet &mdash;</div>}
      </div>
    </motion.div>
  );
}

function WireStrip() {
  const { state } = useStore();
  const recent = state.packets.slice(-5);
  return (
    <div className="wire">
      <div className="wire-label">the wire</div>
      <div className="wire-track">
        <AnimatePresence>
          {recent.map((p) => (
            <motion.div
              key={p.id}
              className={`packet ${p.encrypted ? "packet-enc" : "packet-plain"}`}
              initial={{ x: -40, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ opacity: 0 }}
              title={p.encrypted ? "encrypted" : p.preview || "plaintext"}
            >
              {p.encrypted ? "\u2588\u2588\u2588" : (p.preview || "msg").slice(0, 16)}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function Stage({ activeActor }: { activeActor: Actor }) {
  return (
    <div className="stage">
      <div className="panes">
        <ActorPane actor="alice" active={activeActor === "alice"} />
        <ActorPane actor="bob" active={activeActor === "bob"} />
        <ActorPane actor="eve" active={activeActor === "eve"} />
      </div>
      <WireStrip />
      <FxLayer />
    </div>
  );
}
