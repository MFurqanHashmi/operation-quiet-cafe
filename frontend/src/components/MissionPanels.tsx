import React, { useState } from "react";
import { useStore } from "../store";
import { ActionButton, Field, ResultBox, Mono, Button } from "./ui";

function Tradecraft({ title, blurb, tool, href, children }: any) {
  const [open, setOpen] = useState(false);
  return (
    <div className="tradecraft">
      <button className="tc-toggle" onClick={() => setOpen(!open)}>
        {open ? "\u25be" : "\u25b8"} Tradecraft &mdash; {title}
      </button>
      {open && (
        <div className="tc-body">
          <div className="tc-tool">
            <strong>{tool}</strong> &middot; {blurb}{" "}
            <a href={href} target="_blank" rel="noreferrer">official docs &rarr;</a>
          </div>
          {children}
        </div>
      )}
    </div>
  );
}

/* ---------------- Mission 1 ---------------- */
function M1() {
  const { doAction } = useStore();
  const [t, setT] = useState<any[] | null>(null);
  return (
    <div className="panel">
      <ActionButton label="Tap the wire" run={async () => setT((await doAction("tap")).transcript)} />
      {t && (
        <div className="transcript">
          {t.map((m, i) => (
            <div key={i} className="t-line">
              <span className={`t-who t-${m.from}`}>{m.from}</span>
              <span>{m.text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------- Mission 2 ---------------- */
function M2() {
  const { doAction } = useStore();
  const [msg, setMsg] = useState("Meet me at the back table at 6.");
  const [ct, setCt] = useState("");
  const [reply, setReply] = useState("");
  const [wall, setWall] = useState("");
  return (
    <div className="panel">
      <Field value={msg} onChange={setMsg} placeholder="Your message to Bob" />
      <div className="row">
        <ActionButton label="Scramble" run={async () => setCt((await doAction("encrypt", { plaintext: msg })).ciphertext || "")} />
        <ActionButton label="Send to Bob" kind="ghost" run={async () => setReply((await doAction("send")).bob_reply || "")} />
        <ActionButton label="Send Bob the key" kind="danger" run={async () => setWall((await doAction("send_key")).wall || "")} />
      </div>
      {ct && <ResultBox tone="noise">Scrambled: <Mono>{ct.slice(0, 60)}&hellip;</Mono></ResultBox>}
      {reply && <ResultBox tone="bob">{reply}</ResultBox>}
      {wall && <ResultBox tone="warn">{wall}</ResultBox>}
      <Tradecraft
        title="watch tampering get rejected"
        tool="AES-256-GCM"
        blurb="authenticated encryption hides the message and detects any change to it."
        href="https://en.wikipedia.org/wiki/Galois/Counter_Mode"
      >
        <ActionButton label="Tamper with the ciphertext" run={async () => {
          const r = await doAction("tamper");
          alert(`${r.result}\n\n${r.lesson}`);
        }} />
      </Tradecraft>
    </div>
  );
}

/* ---------------- Mission 3 ---------------- */
function M3() {
  const { doAction } = useStore();
  const [fp, setFp] = useState("");
  const [msg, setMsg] = useState("The drop is confirmed for midnight.");
  const [ct, setCt] = useState("");
  const [reply, setReply] = useState("");
  return (
    <div className="panel">
      <ActionButton label="Fetch Bob's public padlock" run={async () => setFp((await doAction("fetch_key")).fingerprint || "")} />
      {fp && <ResultBox tone="info">Bob's public-key fingerprint: <Mono>{fp}</Mono></ResultBox>}
      <Field value={msg} onChange={setMsg} placeholder="Message to lock for Bob" />
      <div className="row">
        <ActionButton label="Lock with Bob's key" run={async () => setCt((await doAction("encrypt", { plaintext: msg })).ciphertext || "")} />
        <ActionButton label="Send to Bob" kind="ghost" run={async () => setReply((await doAction("send")).bob_reply || "")} />
      </div>
      {ct && <ResultBox tone="noise">Locked: <Mono>{ct.slice(0, 60)}&hellip;</Mono> (only Bob's private key opens this)</ResultBox>}
      {reply && <ResultBox tone="bob">{reply}</ResultBox>}
      <Tradecraft
        title="agree on a secret without sending one"
        tool="Diffie-Hellman (X25519)"
        blurb="both sides mix public + private values to derive the same secret independently."
        href="https://www.cloudflare.com/learning/ssl/what-happens-in-a-tls-handshake/"
      >
        <ActionButton label="Run a real key exchange" run={async () => {
          const r = await doAction("dh");
          alert(
            `Alice derived: ${r.alice_secret?.slice(0, 24)}...\n` +
            `Bob derived:   ${r.bob_secret?.slice(0, 24)}...\n\n` +
            `Identical? ${r.match}\n\n${r.lesson}`
          );
        }} />
      </Tradecraft>
    </div>
  );
}

/* ---------------- Mission 4 ---------------- */
function M4() {
  const { doAction } = useStore();
  const [known, setKnown] = useState("");
  const [left, setLeft] = useState<any>(null);
  const [right, setRight] = useState<any>(null);
  const [msg, setMsg] = useState("");

  const inspect = async (door: string) => {
    const r = await doAction("inspect", { door });
    setKnown(r.known_good_fingerprint);
    door === "left" ? setLeft(r.cert) : setRight(r.cert);
  };
  const choose = async (door: string) => {
    const r = await doAction("choose", { door });
    setMsg(r.verified ? r.message : r.warning);
  };

  const Door = ({ side, cert }: { side: string; cert: any }) => (
    <div className="door">
      <div className="door-title">{side === "left" ? "Door A" : "Door B"}</div>
      <ActionButton label="Inspect certificate" kind="ghost" run={() => inspect(side)} />
      {cert && (
        <div className="cert">
          <div>Subject: <Mono>{cert.subject_cn}</Mono></div>
          <div>Issuer: <Mono>{cert.issuer_cn}</Mono></div>
          <div>Expires: <Mono>{cert.not_after}</Mono></div>
          <div className={known && cert.fingerprint === known ? "fp-match" : "fp-bad"}>
            Fingerprint: <Mono>{cert.fingerprint.slice(0, 29)}&hellip;</Mono>
          </div>
        </div>
      )}
      <Button onClick={() => choose(side)}>Walk through {side === "left" ? "Door A" : "Door B"}</Button>
    </div>
  );

  return (
    <div className="panel">
      {known && <ResultBox tone="info">Bob's known-good fingerprint: <Mono>{known.slice(0, 29)}&hellip;</Mono></ResultBox>}
      <div className="doors">
        <Door side="left" cert={left} />
        <Door side="right" cert={right} />
      </div>
      {msg && <ResultBox tone={msg.includes("really Bob") ? "bob" : "warn"}>{msg}</ResultBox>}
    </div>
  );
}

/* ---------------- Mission 5 ---------------- */
function M5() {
  const { doAction } = useStore();
  const [steps, setSteps] = useState<string[]>([]);
  const [flag, setFlag] = useState("");
  const [err, setErr] = useState("");
  return (
    <div className="panel">
      <ActionButton label="Secure login (key-based)" run={async () => {
        const r = await doAction("login");
        setSteps(r.steps || []);
        if (r.ok) { setFlag(r.flag); setErr(""); } else { setErr(r.error || "login failed"); }
      }} />
      {steps.length > 0 && (
        <div className="ssh-log">
          {steps.map((s, i) => <div key={i} className="ssh-line">{"\u2713"} {s}</div>)}
        </div>
      )}
      {flag && <ResultBox tone="bob">Sealed orders read from the station.</ResultBox>}
      {err && <ResultBox tone="warn">{err}</ResultBox>}
    </div>
  );
}

/* ---------------- Mission 6 ---------------- */
function M6() {
  const { doAction } = useStore();
  const [auth, setAuth] = useState<any>(null);
  const [code, setCode] = useState("");
  const [totpMsg, setTotpMsg] = useState("");
  const [pkMsg, setPkMsg] = useState("");
  return (
    <div className="panel">
      <ActionButton label="Reveal authenticator" run={async () => setAuth(await doAction("totp_show"))} />
      {auth && (
        <ResultBox tone="info">
          Live code: <Mono>{auth.current}</Mono> &mdash; rotates every 30s. {auth.note}
        </ResultBox>
      )}
      <div className="row">
        <Field value={code} onChange={setCode} placeholder="Enter the 6-digit code" />
        <ActionButton label="Verify code" kind="ghost" run={async () => {
          const r = await doAction("totp_verify", { code });
          setTotpMsg(r.accepted ? "Accepted \u2713 now go passwordless." : r.note);
        }} />
      </div>
      {totpMsg && <ResultBox tone={totpMsg.includes("\u2713") ? "bob" : "warn"}>{totpMsg}</ResultBox>}
      <div className="divider-or">then kill the password</div>
      <div className="row">
        <ActionButton label="Request passkey challenge" run={() => doAction("passkey_challenge")} />
        <ActionButton label="Sign &amp; open the vault" kind="ghost" run={async () => {
          const r = await doAction("passkey_verify");
          setPkMsg(r.verified ? r.message : (r.error || "rejected"));
        }} />
      </div>
      {pkMsg && <ResultBox tone="bob">{pkMsg}</ResultBox>}
    </div>
  );
}

export default function MissionPanels({ n }: { n: number }) {
  switch (n) {
    case 1: return <M1 />;
    case 2: return <M2 />;
    case 3: return <M3 />;
    case 4: return <M4 />;
    case 5: return <M5 />;
    case 6: return <M6 />;
    default: return null;
  }
}
