import { useState } from "react";
import type { MatchStatistics, RosterEntry, TeamPayload } from "../types";

type Props = {
  stats: MatchStatistics | null;
  home: TeamPayload | null;
  away: TeamPayload | null;
  roster: Map<string, RosterEntry>;
};

export function PlayerStatistics({ stats, home, away, roster }: Props) {
  const [side, setSide] = useState<"home" | "away">("home");

  if (!stats || !home || !away) {
    return (
      <section className="panel player-stats">
        <h2 className="panel__title">Player statistics</h2>
        <p className="panel__muted">Available after kickoff.</p>
      </section>
    );
  }

  const team = side === "home" ? home : away;
  const players = [...team.starting_xi, ...team.bench];

  return (
    <section className="panel player-stats">
      <div className="player-stats__header">
        <h2 className="panel__title">Player statistics</h2>
        <div className="player-stats__tabs">
          <button
            type="button"
            className={side === "home" ? "btn btn--primary" : "btn"}
            onClick={() => setSide("home")}
          >
            {home.name}
          </button>
          <button
            type="button"
            className={side === "away" ? "btn btn--primary" : "btn"}
            onClick={() => setSide("away")}
          >
            {away.name}
          </button>
        </div>
      </div>
      <div className="player-stats__table-wrap">
        <table className="player-stats__table">
          <thead>
            <tr>
              <th>Player</th>
              <th>Pos</th>
              <th>Min</th>
              <th>G</th>
              <th>Sh</th>
              <th>SOT</th>
              <th>Fouls</th>
              <th>Y/R</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p) => {
              const row = stats.players[p.id];
              const name = roster.get(p.id)?.name ?? p.name;
              const highlight = (row?.goals ?? 0) > 0;
              return (
                <tr key={p.id} className={highlight ? "player-stats__row--hot" : undefined}>
                  <td>{name}</td>
                  <td>{p.position}</td>
                  <td>{row?.minutes_played ?? 0}</td>
                  <td>{row?.goals ?? 0}</td>
                  <td>{row?.shots ?? 0}</td>
                  <td>{row?.shots_on_target ?? 0}</td>
                  <td>{row?.fouls_committed ?? 0}</td>
                  <td>
                    {row?.yellow_cards ?? 0}/{row?.red_cards ?? 0}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}