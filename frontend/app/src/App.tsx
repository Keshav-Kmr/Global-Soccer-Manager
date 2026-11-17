import { Scoreboard } from "./components/Scoreboard";
import { Pitch } from "./components/Pitch";
import { CommentaryFeed } from "./components/CommentaryFeed";
import { StatisticsPanel } from "./components/StatisticsPanel";
import { PlayerStatistics } from "./components/PlayerStatistics";
import { ManagerControls } from "./components/ManagerControls";
import { useMatchSession } from "./hooks/useMatchSession";

export default function App() {
  const session = useMatchSession();
  const lastType = session.events[session.events.length - 1]?.type;

  return (
    <div className="app">
      <Scoreboard
        state={session.state}
        home={session.homeTeam}
        away={session.awayTeam}
        lastEventType={lastType}
        stats={session.stats}
      />

      {session.error && (
        <div className="banner banner--error" role="alert">
          {session.error}
          <span className="banner__hint"> Is the backend running? (uvicorn from backend/)</span>
        </div>
      )}

      <main className="layout">
        <div className="layout__main">
          <Pitch
            pitch={session.pitch}
            roster={session.roster}
            home={session.homeTeam}
            away={session.awayTeam}
          />
          <PlayerStatistics
            stats={session.stats}
            home={session.homeTeam}
            away={session.awayTeam}
            roster={session.roster}
          />
          <ManagerControls
            state={session.state}
            home={session.homeTeam}
            away={session.awayTeam}
            loading={session.loading}
            onAdvance={session.runAdvance}
            onPauseToggle={session.togglePause}
            onTactics={session.applyTactics}
            onFormation={session.applyFormation}
            onSubstitution={session.applySubstitution}
            onStartControlled={() => session.startNewMatch("controlled")}
            onStartAuto={() => session.startNewMatch("auto")}
          />
        </div>

        <aside className="layout__side">
          <StatisticsPanel stats={session.stats} home={session.homeTeam} away={session.awayTeam} />
          <CommentaryFeed events={session.events} />
        </aside>
      </main>

      <footer className="footer">
        <span>
          Match ID: {session.matchId ?? "—"} · Mode: {session.state?.mode ?? "—"} · Seed:{" "}
          {session.state?.seed ?? "—"}
        </span>
      </footer>
    </div>
  );
}