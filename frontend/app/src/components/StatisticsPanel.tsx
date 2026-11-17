import type { MatchStatistics, TeamPayload } from "../types";

type Props = {
  stats: MatchStatistics | null;
  home: TeamPayload | null;
  away: TeamPayload | null;
};

function StatRow({ label, home, away }: { label: string; home: string; away: string }) {
  return (
    <div className="stat-row">
      <span className="stat-row__val stat-row__val--home">{home}</span>
      <span className="stat-row__label">{label}</span>
      <span className="stat-row__val stat-row__val--away">{away}</span>
    </div>
  );
}

export function StatisticsPanel({ stats, home, away }: Props) {
  if (!stats || !home || !away) {
    return (
      <section className="panel stats">
        <h2 className="panel__title">Team statistics</h2>
        <p className="panel__muted">Statistics appear once the match runs.</p>
      </section>
    );
  }

  const h = stats.teams[home.id];
  const a = stats.teams[away.id];
  if (!h || !a) return null;

  const passH =
    h.passes_attempted != null && h.passes_attempted > 0
      ? `${h.passes_completed ?? 0}/${h.passes_attempted} (${h.pass_completion_pct ?? 0}%)`
      : "—";
  const passA =
    a.passes_attempted != null && a.passes_attempted > 0
      ? `${a.passes_completed ?? 0}/${a.passes_attempted} (${a.pass_completion_pct ?? 0}%)`
      : "—";

  return (
    <section className="panel stats">
      <h2 className="panel__title">Team statistics</h2>
      <StatRow label="Possession" home={`${h.possession_pct}%`} away={`${a.possession_pct}%`} />
      <StatRow label="Shots" home={String(h.shots)} away={String(a.shots)} />
      <StatRow label="On target" home={String(h.shots_on_target)} away={String(a.shots_on_target)} />
      <StatRow
        label="Off target"
        home={String(h.shots_off_target ?? "—")}
        away={String(a.shots_off_target ?? "—")}
      />
      <StatRow
        label="Blocked"
        home={String(h.blocked_shots ?? "—")}
        away={String(a.blocked_shots ?? "—")}
      />
      <StatRow label="Passes" home={passH} away={passA} />
      <StatRow label="Fouls" home={String(h.fouls)} away={String(a.fouls)} />
      <StatRow
        label="Yellow cards"
        home={String(h.yellow_cards ?? 0)}
        away={String(a.yellow_cards ?? 0)}
      />
      <StatRow label="Red cards" home={String(h.red_cards ?? 0)} away={String(a.red_cards ?? 0)} />
      <StatRow label="Offsides" home={String(h.offsides ?? 0)} away={String(a.offsides ?? 0)} />
      <StatRow label="Penalties" home={String(h.penalties ?? 0)} away={String(a.penalties ?? 0)} />
      <StatRow label="Saves" home={String(h.saves ?? 0)} away={String(a.saves ?? 0)} />
      <StatRow label="Tackles" home={String(h.tackles ?? 0)} away={String(a.tackles ?? 0)} />
    </section>
  );
}