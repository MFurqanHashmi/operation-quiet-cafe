import React, { useEffect } from "react";
import { useStore } from "./store";
import { MISSIONS } from "./missionsMeta";
import Stage from "./components/Stage";
import MissionConsole from "./components/MissionConsole";
import { ColdOpen, CaseClosed } from "./components/Screens";

function Header() {
  const { state, enter, goPhase, reset } = useStore();
  const verified = state.session?.codes_verified || [];
  const total = state.session?.total || 6;
  const pct = Math.round((verified.length / total) * 100);
  const allDone = verified.length === total;
  const m = MISSIONS[state.mission - 1];

  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-dot" /> Operation Quiet Café
      </div>

      <nav className="mnav">
        {MISSIONS.map((mm) => {
          const isDone = verified.includes(mm.n);
          const isCur = state.mission === mm.n;
          return (
            <button
              key={mm.n}
              className={`mtab ${isCur ? "mtab-cur" : ""} ${isDone ? "mtab-done" : ""}`}
              onClick={() => enter(mm.n)}
              title={mm.title}
            >
              {isDone ? "\u2713" : mm.n}
            </button>
          );
        })}
      </nav>

      <div className="prog">
        <div className="prog-track"><div className="prog-fill" style={{ width: `${pct}%` }} /></div>
        <span className="prog-text">{verified.length}/{total} codes</span>
      </div>

      <div className="topbar-actions">
        <span className={`conn ${state.connected ? "conn-on" : "conn-off"}`} title={state.connected ? "live" : "reconnecting"} />
        {allDone && <button className="btn btn-primary btn-sm" onClick={() => goPhase("closed")}>Close the case &rarr;</button>}
        <button className="btn btn-ghost btn-sm" onClick={() => { if (confirm("Reset all progress on this device?")) reset(); }}>Reset</button>
      </div>
    </header>
  );
}

export default function App() {
  const { state, enter } = useStore();

  // Enter the active mission whenever it changes during play.
  useEffect(() => {
    if (state.phase === "playing" && state.session) enter(state.mission);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.mission, state.phase, state.session?.session_id]);

  if (!state.session) {
    return <div className="loading">Warming up the caf&eacute;&hellip;</div>;
  }
  if (state.phase === "coldopen") return <ColdOpen />;
  if (state.phase === "closed") return <CaseClosed />;

  const m = MISSIONS[state.mission - 1];
  return (
    <div className="app">
      <Header />
      <main className="main">
        <Stage activeActor={m.actor} />
        <MissionConsole />
      </main>
    </div>
  );
}
