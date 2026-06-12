import React, { useState } from "react";
import { useStore } from "../store";
import { MISSIONS } from "../missionsMeta";
import {
  ActionButton, Field, ResultBox, Mono, Button,
  Choice, Consequence, Checkpoint, CodeReveal,
  Recall, Predict, Terminal,
} from "./ui";

type Earn = (code: string) => void;

function meta(n: number) {
  return MISSIONS[n - 1];
}

/* Thin collapsible shell; the Terminal renders its own tool header + docs link. */
function TradecraftBox({ exec }: { exec: (cmd: string, step: number) => Promise<any> }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="tradecraft">
      <button className="tc-toggle" onClick={() => setOpen(!open)}>
        {open ? "\u25be" : "\u25b8"} Tradecraft &mdash; hands-on with the real tools
      </button>
      {open && (
        <div className="tc-body">
          <Terminal exec={exec} />
        </div>
      )}
    </div>
  );
}

/* Recall + Predict header shared by every mission. Predict gates the action. */
function MissionIntro({ n, onReady }: { n: number; onReady: () => void }) {
  const m = meta(n);
  const [done, setDone] = useState(false);
  React.useEffect(() => {
    if (!m.predict) onReady();
  }, [n]);
  return (
    <>
      <Recall phrase={m.recall.phrase}>{m.recall.body}</Recall>
      {m.predict && !done ? (
        <Predict
          prompt={m.predict.prompt}
          options={m.predict.options}
          correctIndex={m.predict.correctIndex}
          whyCorrect={m.predict.whyCorrect}
          onCommitted={() => { setDone(true); onReady(); }}
        />
      ) : null}
    </>
  );
}

/* ======================= Mission 1 — Eve sifts the wire ===================== */
function M1({ onEarn }: { onEarn: Earn }) {
  const { doAction } = useStore();
  const [ready, setReady] = useState(false);
  const [lines, setLines] = useState<any[] | null>(null);
  const [conseq, setConseq] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [solved, setSolved] = useState(false);
  const [code, setCode] = useState("");

  const flag = async (id: string) => {
    const r = await doAction("accuse", { line_id: id });
    if (r.correct) {
      setSolved(true); setConseq({ tone: "good", text: r.message });
      setCode(r.code); onEarn(r.code);
    } else setConseq({ tone: "bad", text: r.nudge });
  };

  return (
    <div className="panel">
      <MissionIntro n={1} onReady={() => setReady(true)} />
      {ready && (
        <>
          <ActionButton label="Tap the wire" run={async () => setLines((await doAction("intercept")).intercepts)} />
          {lines && (
            <div className="intercepts">
              <div className="intercepts-head">Six messages crossed the wire in the clear. Flag the one that truly leaks the operation:</div>
              {lines.map((m) => (
                <div key={m.id} className={`intercept ${solved ? "intercept-locked" : ""}`}>
                  <span className={`t-who t-${m.who}`}>{m.who}</span>
                  <span className="intercept-text">{m.text}</span>
                  <button className="intercept-flag" disabled={solved} onClick={() => flag(m.id)}>Flag</button>
                </div>
              ))}
            </div>
          )}
          {conseq && <Consequence tone={conseq.tone}>{conseq.text}</Consequence>}
          {solved && <CodeReveal code={code} />}
        </>
      )}
      <TradecraftBox exec={(cmd, step) => doAction("tc", { cmd, step })} />
    </div>
  );
}

/* ======================= Mission 2 — Alice: the key-sharing wall ============ */
function M2({ onEarn }: { onEarn: Earn }) {
  const { doAction } = useStore();
  const [ready, setReady] = useState(false);
  const [msg, setMsg] = useState("Meet me at the back table at 6.");
  const [ct, setCt] = useState("");
  const [wall, setWall] = useState<string | null>(null);
  const cp = meta(2).checkpoint!;

  return (
    <div className="panel">
      <MissionIntro n={2} onReady={() => setReady(true)} />
      {ready && (
        <>
          <Field value={msg} onChange={setMsg} placeholder="Your message to Bob" />
          <ActionButton label="Scramble it" run={async () => {
            const r = await doAction("encrypt", { plaintext: msg });
            setCt(r.ciphertext || "");
          }} />
          {ct && <ResultBox tone="noise">On the wire: <Mono>{ct.slice(0, 56)}&hellip;</Mono> &mdash; pure noise, <em>if</em> Bob has the key.</ResultBox>}

          {ct && (
            <Choice
              prompt="Bob needs the shared key to read it. How do you get it to him?"
              options={[
                { value: "wire", label: "Send the key over the wire", sub: "quick and easy" },
                { value: "shout", label: "Say it out loud across the café", sub: "he's right there" },
                { value: "courier", label: "Hand it off by trusted courier", sub: "slow but careful" },
              ]}
              onChoose={async (method) => {
                const r = await doAction("share_key", { method });
                setWall(`${r.consequence}\n\n${r.next}`);
              }}
            />
          )}
          {wall && <Consequence tone="bad">{wall}</Consequence>}

          {wall && (
            <Checkpoint
              prompt={cp.prompt}
              options={cp.options}
              onAnswer={async (idx) => doAction("checkpoint", { choice: idx })}
              onSolved={onEarn}
            />
          )}
        </>
      )}
      <TradecraftBox exec={(cmd, step) => doAction("tc", { cmd, step })} />
    </div>
  );
}

/* ======================= Mission 3 — Alice: pick the right key ============== */
function M3({ onEarn }: { onEarn: Earn }) {
  const { doAction } = useStore();
  const [ready, setReady] = useState(false);
  const [ring, setRing] = useState<any[] | null>(null);
  const [msg, setMsg] = useState("The drop is confirmed for midnight.");
  const [conseq, setConseq] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [solved, setSolved] = useState(false);
  const [code, setCode] = useState("");

  return (
    <div className="panel">
      <MissionIntro n={3} onReady={() => setReady(true)} />
      {ready && (
        <>
          <ActionButton label="Open your keyring" run={async () => setRing((await doAction("keyring")).keyring)} />
          {ring && (
            <>
              <div className="keyring">
                {ring.map((k) => (
                  <div key={k.owner} className={`keychip key-${k.owner}`}>
                    <span className="key-label">{k.label}</span>
                    <span className="key-fp mono">{k.fp.slice(0, 19)}&hellip;</span>
                  </div>
                ))}
              </div>
              <Field value={msg} onChange={setMsg} placeholder="Message to lock for Bob" />
              <Choice
                prompt="Lock the box so ONLY Bob can open it. Which public key do you use?"
                options={ring.map((k) => ({ value: k.owner, label: k.label }))}
                disabled={solved}
                onChoose={async (owner) => {
                  const r = await doAction("lock", { plaintext: msg, key_owner: owner });
                  if (r.correct) {
                    setSolved(true); setConseq({ tone: "good", text: r.message });
                    setCode(r.code); onEarn(r.code);
                  } else setConseq({ tone: "bad", text: r.consequence });
                }}
              />
            </>
          )}
          {conseq && <Consequence tone={conseq.tone}>{conseq.text}</Consequence>}
          {solved && <CodeReveal code={code} />}
        </>
      )}
      <TradecraftBox exec={(cmd, step) => doAction("tc", { cmd, step })} />
    </div>
  );
}

/* ======================= Mission 4 — Alice: spot the forgery =============== */
function M4({ onEarn }: { onEarn: Earn }) {
  const { doAction } = useStore();
  const [ready, setReady] = useState(false);
  const [known, setKnown] = useState("");
  const [certs, setCerts] = useState<Record<string, any>>({});
  const [conseq, setConseq] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [verified, setVerified] = useState(false);
  const cp = meta(4).checkpoint!;

  const inspect = async (door: string) => {
    const r = await doAction("inspect", { door });
    setKnown(r.known_good_fingerprint);
    setCerts((c) => ({ ...c, [door]: r.cert }));
  };
  const choose = async (door: string) => {
    const r = await doAction("choose", { door });
    if (r.correct) { setVerified(true); setConseq({ tone: "good", text: r.message }); }
    else setConseq({ tone: "bad", text: r.consequence });
  };

  const Door = ({ side }: { side: string }) => {
    const cert = certs[side];
    const match = cert && known && cert.fingerprint === known;
    return (
      <div className="door">
        <div className="door-title">{side === "left" ? "Door A" : "Door B"}</div>
        <ActionButton label="Inspect certificate" kind="ghost" run={() => inspect(side)} />
        {cert && (
          <div className="cert">
            <div>Subject: <Mono>{cert.subject_cn}</Mono></div>
            <div>Issuer: <Mono>{cert.issuer_cn}</Mono></div>
            <div>Expires: <Mono>{cert.not_after}</Mono></div>
            <div className={match ? "fp-match" : "fp-bad"}>
              Fingerprint: <Mono>{cert.fingerprint.slice(0, 23)}&hellip;</Mono> {match ? "\u2713 match" : "\u2260"}
            </div>
          </div>
        )}
        <Button kind="ghost" onClick={() => choose(side)} disabled={verified}>
          Walk through {side === "left" ? "Door A" : "Door B"}
        </Button>
      </div>
    );
  };

  return (
    <div className="panel">
      <MissionIntro n={4} onReady={() => setReady(true)} />
      {ready && (
        <>
          {known && <ResultBox tone="info">Bob's known-good fingerprint: <Mono>{known.slice(0, 23)}&hellip;</Mono> &mdash; compare every door to this.</ResultBox>}
          <div className="doors">
            <Door side="left" />
            <Door side="right" />
          </div>
          {conseq && <Consequence tone={conseq.tone}>{conseq.text}</Consequence>}
          {verified && (
            <Checkpoint
              prompt={cp.prompt}
              options={cp.options}
              onAnswer={async (idx) => doAction("checkpoint", { choice: idx })}
              onSolved={onEarn}
            />
          )}
        </>
      )}
      <TradecraftBox exec={(cmd, step) => doAction("tc", { cmd, step })} />
    </div>
  );
}

/* ======================= Mission 5 — Bob: which key on the server? ========= */
function M5({ onEarn }: { onEarn: Earn }) {
  const { doAction } = useStore();
  const [ready, setReady] = useState(false);
  const [keys, setKeys] = useState<any>(null);
  const [steps, setSteps] = useState<string[]>([]);
  const [conseq, setConseq] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [loggedIn, setLoggedIn] = useState(false);
  const cp = meta(5).checkpoint!;

  return (
    <div className="panel">
      <MissionIntro n={5} onReady={() => setReady(true)} />
      {ready && (
        <>
          <ActionButton label="Generate your key pair" run={async () => setKeys(await doAction("keygen"))} />
          {keys && (
            <div className="keypair">
              <div className="kp-row"><span className="kp-tag kp-pub">public</span> <Mono>{keys.public}</Mono></div>
              <div className="kp-row"><span className="kp-tag kp-priv">private</span> <Mono>{keys.private}</Mono></div>
            </div>
          )}
          {keys && (
            <Choice
              prompt="Which key do you install on Station Bravo so you can log in?"
              options={[
                { value: "public", label: "The public key", sub: "safe to share" },
                { value: "private", label: "The private key", sub: "so the server knows me" },
                { value: "both", label: "Both, to be safe", sub: "belt and braces" },
              ]}
              disabled={loggedIn}
              onChoose={async (which) => {
                const r = await doAction("install", { which });
                if (r.correct) {
                  setLoggedIn(true); setSteps(r.steps || []);
                  setConseq({ tone: "good", text: r.message });
                } else setConseq({ tone: "bad", text: r.consequence });
              }}
            />
          )}
          {steps.length > 0 && (
            <div className="ssh-log">
              {steps.map((s, i) => <div key={i} className="ssh-line">{"\u2713"} {s}</div>)}
            </div>
          )}
          {conseq && <Consequence tone={conseq.tone}>{conseq.text}</Consequence>}
          {loggedIn && (
            <Checkpoint
              prompt={cp.prompt}
              options={cp.options}
              onAnswer={async (idx) => doAction("checkpoint", { choice: idx })}
              onSolved={onEarn}
            />
          )}
        </>
      )}
      <TradecraftBox exec={(cmd, step) => doAction("tc", { cmd, step })} />
    </div>
  );
}

/* ======================= Mission 6 — Bob: kill the password ================ */
function M6({ onEarn }: { onEarn: Earn }) {
  const { doAction } = useStore();
  const [ready, setReady] = useState(false);
  const [auth, setAuth] = useState<any>(null);
  const [code, setCode] = useState("");
  const [totpMsg, setTotpMsg] = useState<{ tone: string; text: string } | null>(null);
  const [pkReady, setPkReady] = useState(false);
  const [pkDone, setPkDone] = useState(false);
  const cp = meta(6).checkpoint!;

  return (
    <div className="panel">
      <MissionIntro n={6} onReady={() => setReady(true)} />
      {ready && (
        <>
          <ActionButton label="Reveal the authenticator" run={async () => setAuth(await doAction("totp_show"))} />
          {auth && (
            <ResultBox tone="info">Live code: <Mono>{auth.current}</Mono> &mdash; rotates every 30s. {auth.note}</ResultBox>
          )}
          {auth && (
            <>
              <div className="row">
                <ActionButton label="Try replaying an OLD code" kind="ghost" run={async () => {
                  const r = await doAction("totp_verify", { stale: true });
                  setTotpMsg({ tone: r.accepted ? "bob" : "warn", text: `Tried ${r.used_code}: ${r.note}` });
                }} />
              </div>
              <div className="row">
                <Field value={code} onChange={setCode} placeholder="Now enter the LIVE 6-digit code" />
                <ActionButton label="Submit live code" kind="ghost" run={async () => {
                  const r = await doAction("totp_verify", { code });
                  setTotpMsg({ tone: r.accepted ? "bob" : "warn", text: r.note });
                }} />
              </div>
              {totpMsg && <ResultBox tone={totpMsg.tone}>{totpMsg.text}</ResultBox>}
            </>
          )}

          <div className="divider-or">then kill the password entirely</div>
          <div className="row">
            <ActionButton label="Request passkey challenge" run={async () => {
              await doAction("passkey_challenge"); setPkReady(true);
            }} />
            <ActionButton label="Sign & open the vault" kind="ghost" run={async () => {
              const r = await doAction("passkey_verify");
              if (r.verified) setPkDone(true);
            }} />
          </div>
          {pkReady && !pkDone && <ResultBox tone="info">The vault issued a one-time challenge. Your device will sign it &mdash; no secret leaves the laptop.</ResultBox>}
          {pkDone && <Consequence tone="good">Signature verified against your public key. No password ever existed to steal or phish.</Consequence>}

          {pkDone && (
            <Checkpoint
              prompt={cp.prompt}
              options={cp.options}
              onAnswer={async (idx) => doAction("checkpoint", { choice: idx })}
              onSolved={onEarn}
            />
          )}
        </>
      )}
      <TradecraftBox exec={(cmd, step) => doAction("tc", { cmd, step })} />
    </div>
  );
}

export default function MissionPanels({ n, onEarn }: { n: number; onEarn: Earn }) {
  switch (n) {
    case 1: return <M1 onEarn={onEarn} />;
    case 2: return <M2 onEarn={onEarn} />;
    case 3: return <M3 onEarn={onEarn} />;
    case 4: return <M4 onEarn={onEarn} />;
    case 5: return <M5 onEarn={onEarn} />;
    case 6: return <M6 onEarn={onEarn} />;
    default: return null;
  }
}
