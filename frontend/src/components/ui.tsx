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
