import React, { useState } from "react";
import { useStore } from "../store";
import { MISSIONS, ACTOR_LABEL } from "../missionsMeta";
import MissionPanels from "./MissionPanels";
import { Button, Field } from "./ui";

function Hints({ hints }: { hints: string[] }) {
  const [shown, setShown] = useState(0);
  return (
    <div className="hints">
      <div className="hints-head">Stuck?</div>
      {hints.slice(0, shown).map((h, i) => (
        <div key={i} className="hint">Nudge {i + 1}: {h}</div>
      ))}
      {shown < hints.length && (
        <button className="hint-more" onClick={() => setShown(shown + 1)}>
          {shown === 0 ? "Show a nudge" : "Need another nudge"}
        </button>
      )}
    </div>
  );
}

function CodeBox({ n, codeHint }: { n: number; codeHint: string }) {
  const { verify } = useStore();
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<"idle" | "ok" | "bad">("idle");
  const [msg, setMsg] = useState("");
  const submit = async () => {
    const r = await verify(code.trim());
    if (r.correct) { setStatus("ok"); setMsg("Verified. Mission complete."); }
    else { setStatus("bad"); setMsg(r.nudge || "Not the code on record."); }
  };
  return (
    <div className={`codebox codebox-${status}`}>
      <div className="cb-label">Confirmation code</div>
      <div className="cb-hint">{codeHint}</div>
      <div className="row">
        <Field value={code} onChange={setCode} placeholder="QC{...}" />
        <Button onClick={submit}>Verify</Button>
      </div>
      {msg && <div className={`cb-msg cb-${status}`}>{msg}</div>}
    </div>
  );
}

export default function MissionConsole() {
  const { state } = useStore();
  const m = MISSIONS[state.mission - 1];
  const done = state.session?.completed.includes(m.n);
  return (
    <div className="console">
      <div className="seat-banner" data-actor={m.actor}>
        You're {m.youAre}: <strong>{ACTOR_LABEL[m.actor]}</strong>
        <span className="seat-role">Seat: {m.seat}</span>
      </div>

      <h2 className="m-title">
        <span className="m-num">{String(m.n).padStart(2, "0")}</span> {m.title}
        <span className="m-concept">{m.concept}</span>
      </h2>

      <p className="m-brief">{m.brief}</p>
      <div className="m-running"><span className="live-dot" /> Running around you: {m.running}</div>
      <p className="m-goal"><strong>Your move:</strong> {m.goal}</p>

      <MissionPanels n={m.n} />

      <Hints hints={m.hints} />

      {done ? (
        <div className="debrief">
          <div className="debrief-head">Debrief</div>
          <p>{m.debrief}</p>
          <p className="why"><strong>Why it matters &mdash;</strong> {m.whyItMatters}</p>
        </div>
      ) : (
        <CodeBox n={m.n} codeHint={m.codeHint} />
      )}
    </div>
  );
}
