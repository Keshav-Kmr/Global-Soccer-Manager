import { useCallback, useEffect, useState } from "react";
import type { TeamPayload } from "../types";
import { buildDemoTeam, ensureDistinctMatchTeams, listTeams, saveTeam } from "../api/client";
import { applyFormationToTeam, FORMATION_OPTIONS, isFormationCode } from "../formations";

const TACTIC_PRESET_KEY = "gsm.tacticPresets";

type Props = {
  home: TeamPayload | null;
  away: TeamPayload | null;
  onHomeChange: (team: TeamPayload) => void;
  onAwayChange: (team: TeamPayload) => void;
};

function loadPresets(): Record<string, TeamPayload["tactic"]> {
  try {
    return JSON.parse(localStorage.getItem(TACTIC_PRESET_KEY) ?? "{}") as Record<string, TeamPayload["tactic"]>;
  } catch {
    return {};
  }
}

export function SquadHub({ home, away, onHomeChange, onAwayChange }: Props) {
  const [savedTeams, setSavedTeams] = useState<TeamPayload[]>([]);
  const [listBusy, setListBusy] = useState(false);
  const [seedBusy, setSeedBusy] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [editSide, setEditSide] = useState<"home" | "away">("home");
  const editTeam = editSide === "home" ? home : away;

  const refreshTeams = useCallback(async () => {
    setListBusy(true);
    setListError(null);
    try {
      const teams = await listTeams();
      setSavedTeams(teams);
    } catch (err) {
      setSavedTeams([]);
      setListError(err instanceof Error ? err.message : "Could not load saved teams");
    } finally {
      setListBusy(false);
    }
  }, []);

  useEffect(() => {
    void refreshTeams();
  }, [refreshTeams]);

  const ensureDemoSquads = async () => {
    setSeedBusy(true);
    setListError(null);
    try {
      const h = buildDemoTeam("club_phoenix", "FC Phoenix", 64);
      const a = buildDemoTeam("club_united", "United City", 61);
      await Promise.all([saveTeam(h), saveTeam(a)]);
      onHomeChange(h);
      onAwayChange(a);
      setMessage("Demo squads saved to the database.");
      await refreshTeams();
    } catch (err) {
      setListError(err instanceof Error ? err.message : "Could not seed demo clubs");
    } finally {
      setSeedBusy(false);
    }
  };

  const applyTeam = (team: TeamPayload, side: "home" | "away") => {
    const presets = loadPresets();
    const withTactic = presets[team.id] ? { ...team, tactic: presets[team.id] } : team;
    if (side === "home") {
      onHomeChange(withTactic);
      setMessage(`Loaded ${team.name} as home.`);
      return;
    }
    const otherHome = home ?? withTactic;
    const { away: awayFix } = ensureDistinctMatchTeams(otherHome, withTactic);
    const cloned = awayFix.id !== withTactic.id;
    onAwayChange(awayFix);
    setMessage(
      cloned
        ? `Loaded ${team.name} as away (auto copy "${awayFix.name}" — teams need different ids).`
        : `Loaded ${team.name} as away.`,
    );
  };

  const saveTacticPreset = () => {
    if (!editTeam) return;
    const presets = loadPresets();
    presets[editTeam.id] = editTeam.tactic;
    localStorage.setItem(TACTIC_PRESET_KEY, JSON.stringify(presets));
    setMessage(`Tactic preset saved for ${editTeam.name} (browser).`);
  };

  const persistTeamTactics = async () => {
    if (!editTeam) return;
    setListError(null);
    try {
      await saveTeam(editTeam);
      setMessage(`Team ${editTeam.name} saved (formation ${editTeam.formation}, tactics, lineup).`);
      await refreshTeams();
    } catch (err) {
      setListError(err instanceof Error ? err.message : "Could not save team");
    }
  };

  const updateTactic = (field: keyof TeamPayload["tactic"], value: string) => {
    if (!editTeam) return;
    const next = { ...editTeam, tactic: { ...editTeam.tactic, [field]: value } };
    if (editSide === "home") onHomeChange(next);
    else onAwayChange(next);
  };

  const updateFormation = (raw: string) => {
    if (!editTeam || !isFormationCode(raw)) return;
    const next = applyFormationToTeam(editTeam, raw);
    if (editSide === "home") onHomeChange(next);
    else onAwayChange(next);
    setMessage(`${editTeam.name} formation set to ${raw} (XI slots updated).`);
  };

  return (
    <section className="panel squad-hub">
      <h2 className="panel__title">Squads & tactics</h2>
      <p className="panel__muted">Browse saved clubs, edit tactics, and load them into the next match.</p>

      <div className="squad-hub__actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={seedBusy}
          onClick={() => void ensureDemoSquads()}
        >
          {seedBusy ? "Seeding…" : "Seed demo clubs"}
        </button>
        <button type="button" className="btn" disabled={listBusy} onClick={() => void refreshTeams()}>
          {listBusy ? "Loading…" : "Refresh list"}
        </button>
      </div>

      {listError && (
        <p className="squad-hub__error" role="alert">
          {listError}
        </p>
      )}
      {message && <p className="squad-hub__msg">{message}</p>}

      <div className="squad-hub__grid">
        <div>
          <h3 className="squad-hub__subtitle">Saved teams ({savedTeams.length})</h3>
          <ul className="squad-hub__list">
            {savedTeams.map((team) => (
              <li key={team.id} className="squad-hub__row">
                <span>
                  {team.name}
                  <span className="squad-hub__meta">
                    {team.formation} · {team.starting_xi.length} xi / {team.bench.length} bench
                  </span>
                </span>
                <span className="squad-hub__row-actions">
                  <button type="button" className="btn btn--ghost" onClick={() => applyTeam(team, "home")}>
                    Home
                  </button>
                  <button type="button" className="btn btn--ghost" onClick={() => applyTeam(team, "away")}>
                    Away
                  </button>
                </span>
              </li>
            ))}
            {savedTeams.length === 0 && <li className="panel__muted">No teams in DB yet — seed demo clubs.</li>}
          </ul>
        </div>

        <div>
          <h3 className="squad-hub__subtitle">Tactic editor</h3>
          <div className="squad-hub__tabs">
            <button
              type="button"
              className={editSide === "home" ? "btn btn--primary" : "btn"}
              onClick={() => setEditSide("home")}
            >
              Home
            </button>
            <button
              type="button"
              className={editSide === "away" ? "btn btn--primary" : "btn"}
              onClick={() => setEditSide("away")}
            >
              Away
            </button>
          </div>

          {editTeam && (
            <div className="squad-hub__tactics">
              <p className="squad-hub__meta">{editTeam.name}</p>
              <label>
                formation
                <select value={editTeam.formation} onChange={(e) => updateFormation(e.target.value)}>
                  {FORMATION_OPTIONS.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </label>
              {(
                [
                  ["mentality", ["defensive", "balanced", "attacking"]],
                  ["pressing", ["low", "medium", "high"]],
                  ["tempo", ["slow", "normal", "fast"]],
                  ["width", ["narrow", "normal", "wide"]],
                  ["defensive_line", ["deep", "normal", "high"]],
                  ["marking_scheme", ["zonal", "man_to_man"]],
                ] as const
              ).map(([field, options]) => (
                <label key={field}>
                  {field.replace("_", " ")}
                  <select value={editTeam.tactic[field]} onChange={(e) => updateTactic(field, e.target.value)}>
                    {options.map((o) => (
                      <option key={o} value={o}>
                        {o}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              <div className="squad-hub__actions">
                <button type="button" className="btn" onClick={saveTacticPreset}>
                  Save preset (browser)
                </button>
                <button type="button" className="btn btn--primary" onClick={() => void persistTeamTactics()}>
                  Save to database
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="squad-hub__roster-preview">
        <h3 className="squad-hub__subtitle">Matchday squads</h3>
        <div className="squad-hub__preview-grid">
          {home && (
            <div>
              <strong>{home.name}</strong>
              <ul>
                {home.starting_xi.map((p) => (
                  <li key={p.id}>
                    {p.name} ({p.position})
                  </li>
                ))}
              </ul>
            </div>
          )}
          {away && (
            <div>
              <strong>{away.name}</strong>
              <ul>
                {away.starting_xi.map((p) => (
                  <li key={p.id}>
                    {p.name} ({p.position})
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}