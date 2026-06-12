import React, { useState } from "react";

export function Button({
  children, onClick, kind = "primary", disabled,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  kind?: "primary" | "ghost" | "danger";
  disabled?: boolean;
}) {
  return (
    <button className={`btn btn-${kind}`} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}

export function ActionButton({
  label, run, kind = "primary",
}: {
  label: string;
  run: () => Promise<any>;
  kind?: "primary" | "ghost" | "danger";
}) {
  const [busy, setBusy] = useState(false);
  return (
    <Button
      kind={kind}
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        try { await run(); } finally { setBusy(false); }
      }}
    >
      {busy ? "Working\u2026" : label}
    </Button>
  );
}

export function Field({
  value, onChange, placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      className="field"
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export function ResultBox({ tone = "info", children }: { tone?: string; children: React.ReactNode }) {
  if (children == null) return null;
  return <div className={`result result-${tone}`}>{children}</div>;
}

export function Mono({ children }: { children: React.ReactNode }) {
  return <code className="mono">{children}</code>;
}

/* ---- Decision cards: a real choice with consequences ---- */
export function Choice({
  prompt, options, onChoose, disabled,
}: {
  prompt: string;
  options: { value: string; label: string; sub?: string }[];
  onChoose: (value: string) => Promise<void> | void;
  disabled?: boolean;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  return (
    <div className="choice">
      <div className="choice-prompt">{prompt}</div>
      <div className="choice-grid">
        {options.map((o) => (
          <button
            key={o.value}
            className="choice-card"
            disabled={disabled || busy !== null}
            onClick={async () => {
              setBusy(o.value);
              try { await onChoose(o.value); } finally { setBusy(null); }
            }}
          >
            <span className="choice-label">{busy === o.value ? "Working\u2026" : o.label}</span>
            {o.sub && <span className="choice-sub">{o.sub}</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ---- Consequence box: shows what the wrong/right move caused ---- */
export function Consequence({ tone = "bad", children }: { tone?: "bad" | "good"; children: React.ReactNode }) {
  if (children == null) return null;
  return (
    <div className={`consequence consequence-${tone}`}>
      <span className="consequence-icon">{tone === "good" ? "\u2713" : "\u26a0"}</span>
      <div>{children}</div>
    </div>
  );
}

/* ---- Deduction checkpoint: MCQ, nudges on wrong, reveal + code on right ---- */
export function Checkpoint({
  prompt, options, onAnswer, onSolved,
}: {
  prompt: string;
  options: string[];
  onAnswer: (idx: number) => Promise<{ correct: boolean; nudge?: string; reveal?: string; code?: string }>;
  onSolved: (code: string) => void;
}) {
  const [nudge, setNudge] = useState("");
  const [reveal, setReveal] = useState("");
  const [picked, setPicked] = useState<number | null>(null);
  const [solved, setSolved] = useState(false);
  return (
    <div className={`checkpoint ${solved ? "checkpoint-solved" : ""}`}>
      <div className="checkpoint-q"><span className="cp-tag">Checkpoint</span> {prompt}</div>
      <div className="checkpoint-opts">
        {options.map((o, i) => (
          <button
            key={i}
            className={`cp-opt ${picked === i && !solved ? "cp-wrong" : ""} ${solved && picked === i ? "cp-right" : ""}`}
            disabled={solved}
            onClick={async () => {
              setPicked(i);
              const r = await onAnswer(i);
              if (r.correct) {
                setSolved(true); setNudge(""); setReveal(r.reveal || "");
                if (r.code) onSolved(r.code);
              } else {
                setNudge(r.nudge || "Not quite — try again.");
              }
            }}
          >
            {o}
          </button>
        ))}
      </div>
      {nudge && !solved && <div className="cp-nudge">{nudge}</div>}
      {reveal && <div className="cp-reveal">{reveal}</div>}
    </div>
  );
}

/* ---- Code reveal: the earned confirmation code, with copy ---- */
export function CodeReveal({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  if (!code) return null;
  return (
    <div className="code-reveal">
      <span className="cr-label">Code recovered</span>
      <code className="cr-code">{code}</code>
      <button
        className="cr-copy"
        onClick={() => {
          navigator.clipboard?.writeText(code).then(() => {
            setCopied(true); setTimeout(() => setCopied(false), 1500);
          }).catch(() => {});
        }}
      >
        {copied ? "Copied \u2713" : "Copy"}
      </button>
      <span className="cr-hint">Paste it into the confirmation box below.</span>
    </div>
  );
}

/* ---- Recall: ties the mission back to a concept from the talk ---- */
export function Recall({ phrase, children }: { phrase?: string; children: React.ReactNode }) {
  return (
    <div className="recall">
      <span className="recall-tag">From the talk</span>
      <div className="recall-body">
        {children}
        {phrase && <div className="recall-phrase">&ldquo;{phrase}&rdquo;</div>}
      </div>
    </div>
  );
}

/* ---- Predict: force a hypothesis BEFORE acting (the "think first" gate) ----
   Pedagogical, not a code gate: once they commit, the real action is revealed
   and they get to see whether their prediction held. */
export function Predict({
  prompt, options, correctIndex, whyCorrect, onCommitted,
}: {
  prompt: string;
  options: string[];
  correctIndex: number;
  whyCorrect: string;
  onCommitted: () => void;
}) {
  const [picked, setPicked] = useState<number | null>(null);
  const committed = picked !== null;
  const right = picked === correctIndex;
  return (
    <div className={`predict ${committed ? "predict-committed" : ""}`}>
      <div className="predict-q"><span className="predict-tag">Predict first</span> {prompt}</div>
      <div className="predict-opts">
        {options.map((o, i) => (
          <button
            key={i}
            className={`predict-opt ${committed && i === picked ? (right ? "predict-right" : "predict-close") : ""} ${committed && i === correctIndex ? "predict-answer" : ""}`}
            disabled={committed}
            onClick={() => { setPicked(i); onCommitted(); }}
          >
            {o}
          </button>
        ))}
      </div>
      {committed && (
        <div className="predict-feedback">
          <strong>{right ? "Good hypothesis." : "Let's test that."}</strong> {whyCorrect}
          <span className="predict-cta"> Now run it below and watch what actually happens.</span>
        </div>
      )}
    </div>
  );
}

/* ---- Terminal: the guided, multi-step Tradecraft CLI (real output) ---- */
export function Terminal({
  exec,
}: {
  exec: (cmd: string, step: number) => Promise<any>;
}) {
  const [head, setHead] = useState<any>(null);
  const [history, setHistory] = useState<string[]>([]);
  const [step, setStep] = useState<any>(null);
  const [input, setInput] = useState("");
  const [hintOpen, setHintOpen] = useState(false);
  const [reveal, setReveal] = useState("");
  const [done, setDone] = useState(false);
  const [lesson, setLesson] = useState("");
  const [progress, setProgress] = useState("");
  const [busy, setBusy] = useState(false);
  const [started, setStarted] = useState(false);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [history, done]);

  const begin = async () => {
    const r = await exec("", 0);
    setHead({ tool: r.tool, blurb: r.blurb, href: r.href, intro: r.intro });
    setStep(r.step);
    setProgress(r.progress || "");
    setStarted(true);
  };

  const submit = async () => {
    const cmd = input.trim();
    if (!cmd || !step || busy) return;
    setBusy(true);
    try {
      const r = await exec(cmd, step.index);
      if (r.output) setHistory((h) => [...h, r.output]);
      setProgress(r.progress || progress);
      if (r.match) {
        setReveal(""); setHintOpen(false); setInput("");
        if (r.done) { setDone(true); setLesson(r.lesson || ""); setStep(null); }
        else setStep(r.step);
      } else {
        if (r.reveal) setReveal(r.reveal);
      }
    } finally { setBusy(false); }
  };

  if (!started) {
    return <Button kind="ghost" onClick={begin}>Open the terminal</Button>;
  }

  return (
    <div className="terminal">
      {head && (
        <div className="term-head">
          <strong>{head.tool}</strong> &middot; {head.blurb}{" "}
          <a href={head.href} target="_blank" rel="noreferrer">official docs &rarr;</a>
          <div className="term-intro">{head.intro}</div>
        </div>
      )}
      <div className="term-screen" ref={scrollRef}>
        {history.map((b, i) => <pre key={i} className="term-block">{b}</pre>)}
        {done && <pre className="term-block term-ok">{"\u2713 objective complete"}</pre>}
      </div>

      {!done && step && (
        <div className="term-task">
          <div className="term-objective">
            <span className="term-step">Step {step.index + 1}/{step.total}</span>
            {step.prompt}
          </div>
          <button className="term-hint-toggle" onClick={() => setHintOpen(!hintOpen)}>
            {hintOpen ? "Hide hint" : "Need a hint?"}
          </button>
          {hintOpen && <div className="term-hint">{step.hint}</div>}
          {reveal && (
            <div className="term-reveal">
              Stuck? Try: <code className="mono">{reveal}</code>
            </div>
          )}
          <div className="term-input-row">
            <span className="term-prompt">analyst@quiet-cafe:~$</span>
            <input
              className="term-input"
              value={input}
              placeholder={step.placeholder}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
              autoFocus
            />
            <Button kind="ghost" onClick={submit} disabled={busy}>{busy ? "Running\u2026" : "Run"}</Button>
          </div>
        </div>
      )}

      {done && lesson && (
        <div className="term-lesson"><span className="term-lesson-tag">Takeaway</span> {lesson}</div>
      )}
    </div>
  );
}
