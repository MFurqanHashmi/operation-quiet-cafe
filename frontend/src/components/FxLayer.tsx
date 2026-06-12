import React, { useEffect } from "react";
import { motion } from "framer-motion";
import { useStore } from "../store";
import type { FxItem } from "../types";

// Stage anchor points (percentages over the .stage overlay).
const X = { alice: "16%", bob: "50%", eve: "84%", center: "50%" };
const Y = { pane: "38%", wire: "80%" };

const DURATION: Record<FxItem["kind"], number> = {
  plaintext_grab: 2000,
  key_grab: 2300,
  pubkey_roundtrip: 2700,
  eve_decrypts: 2200,
  granted: 1700,
  denied: 1700,
};

function Token({
  glyph,
  from,
  to,
  delay = 0,
  dur = 1,
  className = "",
}: {
  glyph: string;
  from: { x: string; y: string };
  to: { x: string; y: string };
  delay?: number;
  dur?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={`fx-token ${className}`}
      initial={{ left: from.x, top: from.y, x: "-50%", y: "-50%", opacity: 0, scale: 0.5 }}
      animate={{
        left: [from.x, to.x],
        top: [from.y, to.y],
        x: "-50%",
        y: "-50%",
        opacity: [0, 1, 1, 0.9],
        scale: [0.5, 1.1, 1],
      }}
      transition={{ duration: dur, delay, ease: "easeInOut" }}
    >
      {glyph}
    </motion.div>
  );
}

function Burst({
  x,
  y,
  text,
  tone,
  delay = 0,
}: {
  x: string;
  y: string;
  text: string;
  tone: "bad" | "good";
  delay?: number;
}) {
  return (
    <motion.div
      className={`fx-burst fx-burst-${tone}`}
      style={{ left: x, top: y }}
      initial={{ x: "-50%", y: "-50%", opacity: 0, scale: 0.4 }}
      animate={{ x: "-50%", y: "-50%", opacity: [0, 1, 1, 0], scale: [0.4, 1.15, 1, 1] }}
      transition={{ duration: 1.1, delay, ease: "easeOut" }}
    >
      {text}
    </motion.div>
  );
}

function Stamp({ text, tone }: { text: string; tone: "good" | "bad" }) {
  return (
    <motion.div
      className={`fx-stamp fx-stamp-${tone}`}
      initial={{ x: "-50%", y: "-50%", opacity: 0, scale: 1.6, rotate: -14 }}
      animate={{ x: "-50%", y: "-50%", opacity: [0, 1, 1, 0], scale: [1.6, 0.95, 1, 1], rotate: -8 }}
      transition={{ duration: 1.5, ease: "easeOut", times: [0, 0.25, 0.7, 1] }}
    >
      {text}
    </motion.div>
  );
}

function FxOne({ item }: { item: FxItem }) {
  const { fxDone } = useStore();
  useEffect(() => {
    const t = setTimeout(() => fxDone(item.id), DURATION[item.kind] + 120);
    return () => clearTimeout(t);
  }, [item.id, item.kind, fxDone]);

  switch (item.kind) {
    case "plaintext_grab":
      return (
        <>
          <Token
            glyph={"\u{1F4C4}"}
            from={{ x: X.center, y: Y.wire }}
            to={{ x: X.eve, y: Y.pane }}
            dur={1.3}
            className="fx-doc"
          />
          <Burst x={X.eve} y={Y.pane} tone="bad" text="Eve copied it" delay={1.2} />
        </>
      );
    case "key_grab":
      return (
        <>
          <Token
            glyph={"\u{1F511}"}
            from={{ x: X.center, y: Y.wire }}
            to={{ x: X.eve, y: Y.pane }}
            dur={1.1}
            className="fx-key"
          />
          <Token
            glyph={"\u{1F513}"}
            from={{ x: X.eve, y: Y.pane }}
            to={{ x: X.eve, y: Y.pane }}
            delay={1.15}
            dur={0.6}
            className="fx-lock"
          />
          <Burst x={X.eve} y={Y.pane} tone="bad" text="UNLOCKED" delay={1.3} />
        </>
      );
    case "pubkey_roundtrip":
      return (
        <>
          {/* Locked box travels Alice -> Bob */}
          <Token
            glyph={"\u{1F512}"}
            from={{ x: X.alice, y: Y.pane }}
            to={{ x: X.bob, y: Y.pane }}
            dur={1.2}
            className="fx-lock"
          />
          {/* Bob opens it with his private key */}
          <Token
            glyph={"\u{1F511}"}
            from={{ x: X.bob, y: Y.pane }}
            to={{ x: X.bob, y: Y.pane }}
            delay={1.25}
            dur={0.6}
            className="fx-key"
          />
          <Burst x={X.bob} y={Y.pane} tone="good" text="Bob opens it (private key)" delay={1.4} />
          {/* Eve only ever sees noise */}
          <Token
            glyph={"\u2593\u2593\u2593"}
            from={{ x: X.center, y: Y.wire }}
            to={{ x: X.eve, y: Y.pane }}
            dur={1.3}
            className="fx-noise"
          />
          <Burst x={X.eve} y={Y.pane} tone="good" text="Eve: just noise" delay={1.4} />
        </>
      );
    case "eve_decrypts":
      return (
        <>
          <Token
            glyph={"\u{1F512}"}
            from={{ x: X.alice, y: Y.pane }}
            to={{ x: X.eve, y: Y.pane }}
            dur={1.2}
            className="fx-lock"
          />
          <Token
            glyph={"\u{1F511}"}
            from={{ x: X.eve, y: Y.pane }}
            to={{ x: X.eve, y: Y.pane }}
            delay={1.25}
            dur={0.6}
            className="fx-key"
          />
          <Burst x={X.eve} y={Y.pane} tone="bad" text="Eve opens it!" delay={1.4} />
        </>
      );
    case "granted":
      return <Stamp tone="good" text="ACCESS GRANTED" />;
    case "denied":
      return <Stamp tone="bad" text="ACCESS DENIED" />;
    default:
      return null;
  }
}

export default function FxLayer() {
  const { state } = useStore();
  if (!state.fx.length) return null;
  return (
    <div className="fx-layer" aria-hidden="true">
      {state.fx.map((f) => (
        <FxOne key={f.id} item={f} />
      ))}
    </div>
  );
}
