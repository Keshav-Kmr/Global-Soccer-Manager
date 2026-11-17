import type { MatchState, TeamPayload } from "../types";

type Props = {
  state: MatchState | null;
  home: TeamPayload | null;
  away: TeamPayload | null;
  lastEventType?: string;
  stats?: { teams: Record<string, { yellow_cards?: number; red_cards?: number }> } | null;
};

export function Scoreboard({ state, home, away, lastEventType, stats }: Props) {
  if (!state || !home || !away) {
    return (
      <header className="scoreboard scoreboard--empty">
        <p>Start a match to see live scores</p>
      </header>
    );
  }

  const homeGoals = state.score[home.id] ?? 0;
  const awayGoals = state.score[away.id] ?? 0;
  const clock = state.clock;
  const inStoppage =
    clock &&
    ((clock.period === "first_half" && state.minute > clock.regulation_first_half_end) ||
      (clock.period === "second_half" && state.minute > clock.regulation_match_end));

  const status = state.finished
    ? "Full time"
    : lastEventType === "half_time"
      ? "Half time"
      : state.paused
        ? "Paused"
        : state.mode === "controlled"
          ? "Ready"
          : "Live";

  const homeDiscipline = stats?.teams[home.id];
  const awayDiscipline = stats?.teams[away.id];

  return (
    <header className="scoreboard">
      <div className="scoreboard__club scoreboard__club--home">
        <span className="scoreboard__crest" aria-hidden>{home.name.slice(0, 2).toUpperCase()}</span>
        <span className="scoreboard__name">{home.name}</span>
        {(homeDiscipline?.yellow_cards ?? 0) > 0 && (
          <span className="scoreboard__card scoreboard__card--yellow" title="Yellow cards">
            {homeDiscipline!.yellow_cards}
          </span>
        )}
        {(homeDiscipline?.red_cards ?? 0) > 0 && (
          <span className="scoreboard__card scoreboard__card--red" title="Red cards">
            {homeDiscipline!.red_cards}
          </span>
        )}
      </div>
      <div className="scoreboard__center">
        <div className="scoreboard__score">
          <span>{homeGoals}</span>
          <span className="scoreboard__sep">–</span>
          <span>{awayGoals}</span>
        </div>
        <div className="scoreboard__meta">
          <span className="scoreboard__clock">
            {state.minute}&apos;
            {inStoppage ? "+" : ""}
          </span>
          <span className="scoreboard__status">{status}</span>
          {clock && (
            <span className="scoreboard__period">
              {clock.period === "first_half" ? "1st half" : clock.period === "second_half" ? "2nd half" : ""}
            </span>
          )}
        </div>
      </div>
      <div className="scoreboard__club scoreboard__club--away">
        {(awayDiscipline?.red_cards ?? 0) > 0 && (
          <span className="scoreboard__card scoreboard__card--red" title="Red cards">
            {awayDiscipline!.red_cards}
          </span>
        )}
        {(awayDiscipline?.yellow_cards ?? 0) > 0 && (
          <span className="scoreboard__card scoreboard__card--yellow" title="Yellow cards">
            {awayDiscipline!.yellow_cards}
          </span>
        )}
        <span className="scoreboard__name">{away.name}</span>
        <span className="scoreboard__crest scoreboard__crest--away" aria-hidden>
          {away.name.slice(0, 2).toUpperCase()}
        </span>
      </div>
    </header>
  );
}