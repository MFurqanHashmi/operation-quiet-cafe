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
