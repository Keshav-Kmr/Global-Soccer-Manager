import { useState } from "react";
import type { MatchState, TeamPayload } from "../types";

const FORMATIONS = ["4-3-3", "4-2-3-1", "4-4-2", "3-5-2", "3-4-3", "5-3-2"] as const;

type AdvanceOptions = {
  steps?: number;
  targetMinute?: number;
  nextKey?: boolean;
  untilFinished?: boolean;
};

type Props = {
  state: MatchState | null;
  home: TeamPayload | null;
  away: TeamPayload | null;
  onAdvance: (options: AdvanceOptions) => void;
  onPauseToggle: () => void;
  onTactics: (teamId: string, tactic: TeamPayload["tactic"]) => void;
  onFormation: (teamId: string, formation: string) => void;
  onSubstitution: (teamId: string, outId: string, inId: string) => void;
  onStartAuto: () => void;
  onStartControlled: () => void;
  onReplayLast: () => void;
  hasEvents: boolean;
  loading: boolean;
};

export function ManagerControls({
  state,
  home,
  away,
  onAdvance,
  onPauseToggle,
  onTactics,
  onFormation,
  onSubstitution,
  onStartAuto,
  onStartControlled,
  onReplayLast,
  hasEvents,
  loading,
}: Props) {
  const [subOut, setSubOut] = useState("");
  const [subIn, setSubIn] = useState("");
  const [targetMinute, setTargetMinute] = useState("45");
  const [activeTeam, setActiveTeam] = useState<"home" | "away">("home");

  const controlled = state?.mode === "controlled";
  const finished = state?.finished ?? false;
  const managedTeam = activeTeam === "home" ? home : away;

  return (
    <section className="panel controls">
      <h2 className="panel__title">Manager</h2>

      {!state && (
        <div className="controls__start">
          <button type="button" className="btn btn--primary" disabled={loading} onClick={onStartControlled}>
            New controlled match
          </button>
          <button type="button" className="btn" disabled={loading} onClick={onStartAuto}>
            New live (auto) match
          </button>
        </div>
      )}

      {state && !finished && (
        <>
          <div className="controls__row">
            {controlled ? (
              <>
                <button type="button" className="btn btn--primary" onClick={() => onAdvance({ steps: 1 })}>
                  +1 chain
                </button>
                <button type="button" className="btn" onClick={() => onAdvance({ steps: 5 })}>
                  +5
                </button>
                <button type="button" className="btn" onClick={() => onAdvance({ nextKey: true })}>
                  Next key event
                </button>
                <button type="button" className="btn" onClick={() => onAdvance({ untilFinished: true })}>
                  Full time
                </button>
              </>
            ) : (
              <span className="controls__hint">Auto sim — pause slows the background run</span>
            )}
            <button type="button" className="btn" onClick={onPauseToggle}>
              {state.paused ? "Resume" : "Pause"}
            </button>
            <button type="button" className="btn" disabled={!hasEvents} onClick={onReplayLast}>
              Replay last move
            </button>
          </div>

          {controlled && (
            <div className="controls__row">
              <label>
                Jump to minute
                <input
                  type="number"
                  min={0}
                  max={120}
                  value={targetMinute}
                  onChange={(e) => setTargetMinute(e.target.value)}
                />
              </label>
              <button
                type="button"
                className="btn"
                onClick={() => onAdvance({ targetMinute: Number(targetMinute) || 0 })}
              >
                Go
              </button>
            </div>
          )}

          {home && away && controlled && (
            <div className="controls__team-pick">
              <span>Manage:</span>
              <button
                type="button"
                className={activeTeam === "home" ? "btn btn--primary" : "btn"}
                onClick={() => setActiveTeam("home")}
              >
                {home.name}
              </button>
              <button
                type="button"
                className={activeTeam === "away" ? "btn btn--primary" : "btn"}
                onClick={() => setActiveTeam("away")}
              >
                {away.name}
              </button>
            </div>
          )}

          {managedTeam && controlled && (
            <div className="controls__tactics">
              <label>
                Mentality
                <select
                  defaultValue={managedTeam.tactic.mentality}
                  onChange={(e) =>
                    onTactics(managedTeam.id, { ...managedTeam.tactic, mentality: e.target.value })
                  }
                >
                  <option value="defensive">Defensive</option>
                  <option value="balanced">Balanced</option>
                  <option value="attacking">Attacking</option>
                </select>
              </label>
              <label>
                Pressing
                <select
                  defaultValue={managedTeam.tactic.pressing}
                  onChange={(e) =>
                    onTactics(managedTeam.id, { ...managedTeam.tactic, pressing: e.target.value })
                  }
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </label>
              <label>
                Tempo
                <select
                  defaultValue={managedTeam.tactic.tempo ?? "normal"}
                  onChange={(e) =>
                    onTactics(managedTeam.id, { ...managedTeam.tactic, tempo: e.target.value })
                  }
                >
                  <option value="slow">Slow</option>
                  <option value="normal">Normal</option>
                  <option value="fast">Fast</option>
                </select>
              </label>
              <label>
                Width
                <select
                  defaultValue={managedTeam.tactic.width ?? "normal"}
                  onChange={(e) =>
                    onTactics(managedTeam.id, { ...managedTeam.tactic, width: e.target.value })
                  }
                >
                  <option value="narrow">Narrow</option>
                  <option value="normal">Normal</option>
                  <option value="wide">Wide</option>
                </select>
              </label>
              <label>
                Defensive line
                <select
                  defaultValue={managedTeam.tactic.defensive_line ?? "normal"}
                  onChange={(e) =>
                    onTactics(managedTeam.id, { ...managedTeam.tactic, defensive_line: e.target.value })
                  }
                >
                  <option value="deep">Deep</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                </select>
              </label>
              <label>
                Marking
                <select
                  defaultValue={managedTeam.tactic.marking_scheme ?? "zonal"}
                  onChange={(e) =>
                    onTactics(managedTeam.id, { ...managedTeam.tactic, marking_scheme: e.target.value })
                  }
                >
                  <option value="zonal">Zonal</option>
                  <option value="man_to_man">Man-to-man</option>
                </select>
              </label>
              <label>
                Formation
                <select
                  value={managedTeam.formation}
                  onChange={(e) => onFormation(managedTeam.id, e.target.value)}
                >
                  {FORMATIONS.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {managedTeam && managedTeam.bench.length > 0 && controlled && (
            <div className="controls__sub">
              <label>
                Off
                <select value={subOut} onChange={(e) => setSubOut(e.target.value)}>
                  <option value="">Select</option>
                  {managedTeam.starting_xi.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.position})
                    </option>
                  ))}
                </select>
              </label>
              <label>
                On
                <select value={subIn} onChange={(e) => setSubIn(e.target.value)}>
                  <option value="">Select</option>
                  {managedTeam.bench.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.position})
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className="btn"
                disabled={!subOut || !subIn}
                onClick={() => {
                  onSubstitution(managedTeam.id, subOut, subIn);
                  setSubOut("");
                  setSubIn("");
                }}
              >
                Substitute
              </button>
            </div>
          )}
        </>
      )}

      {state && finished && (
        <div className="controls__row">
          <span className="controls__hint">Match complete — full event log is in the sidebar.</span>
          <button type="button" className="btn" disabled={!hasEvents} onClick={onReplayLast}>
            Replay last move
          </button>
        </div>
      )}
    </section>
  );
}