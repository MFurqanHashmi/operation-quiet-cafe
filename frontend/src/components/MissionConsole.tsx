import React, { useEffect, useState } from "react";
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

/* Manual fallback — facilitators or anyone who already has the code. */
function ManualEntry() {
  const { verify } = useStore();
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState<{ tone: string; text: string } | null>(null);
  const submit = async () => {
    const r = await verify(code.trim());
    if (r.correct) setMsg({ tone: "ok", text: "Verified." });
    else setMsg({ tone: "bad", text: r.nudge || "Not the code on record." });
  };
  return (
    <div className="manual">
      <button className="manual-toggle" onClick={() => setOpen(!open)}>
        {open ? "\u25be" : "\u25b8"} Have a code already? Enter it manually
      </button>
      {open && (
        <div className="manual-body">
          <div className="row">
            <Field value={code} onChange={setCode} placeholder="QC{...}" />
            <Button onClick={submit}>Verify</Button>
          </div>
          {msg && <div className={`cb-msg cb-${msg.tone}`}>{msg.text}</div>}
        </div>
      )}
    </div>
  );
}

export default function MissionConsole() {
  const { state, verify, enter, goPhase } = useStore();
  const m = MISSIONS[state.mission - 1];
  const done = state.session?.completed.includes(m.n);
  const total = state.session?.total || 6;
  const isLast = m.n >= total;

  const [earned, setEarned] = useState("");

  // Reset the local "earned" trophy whenever the mission changes.
  useEffect(() => { setEarned(""); }, [m.n]);

  // When a panel reports the code was genuinely earned, confirm it server-side.
  const onEarn = async (code: string) => {
    setEarned(code);
    await verify(code);
  };

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

      <MissionPanels n={m.n} onEarn={onEarn} />

      {!done && <Hints hints={m.hints} />}

      {done ? (
        <div className="debrief">
          <div className="debrief-head">Mission complete &mdash; debrief</div>
          {earned && (
            <div className="earned-line">
              Code recovered: <code className="earned-code">{earned}</code>
            </div>
          )}
          <p>{m.debrief}</p>
          <p className="why"><strong>Why it matters &mdash;</strong> {m.whyItMatters}</p>
          <div className="next-row">
            {isLast ? (
              <Button onClick={() => goPhase("closed")}>Close the case &rarr;</Button>
            ) : (
              <Button onClick={() => enter(m.n + 1)}>Next challenge &rarr;</Button>
            )}
          </div>
        </div>
      ) : (
        <ManualEntry />
      )}
    </div>
  );
}
