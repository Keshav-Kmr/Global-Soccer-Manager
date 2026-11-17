import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  advanceMatch,
  changeFormation,
  changeTactics,
  createMatch,
  getEvents,
  getMatchResult,
  getMatchState,
  getStatistics,
  latestPitch,
  matchWebSocketUrl,
  pauseMatch,
  pitchFromEvent,
  resumeMatch,
  substitute,
  buildDemoTeam,
} from "../api/client";
import type { MatchState, MatchStatistics, MatchWireEvent, PitchSnapshot, RosterEntry, TeamPayload } from "../types";

const KEY_EVENT_TYPES = new Set([
  "goal",
  "penalty_goal",
  "penalty_awarded",
  "card",
  "injury",
  "substitution",
  "half_time",
  "full_time",
]);

function shouldRefreshStats(event: MatchWireEvent): boolean {
  if (KEY_EVENT_TYPES.has(event.type)) return true;
  if (event.type === "card" && event.payload?.color === "red") return true;
  return ["shot", "save", "offside", "foul", "turnover"].includes(event.type);
}

function mergeEvents(prev: MatchWireEvent[], incoming: MatchWireEvent[]): MatchWireEvent[] {
  if (incoming.length === 0) return prev;
  const byIndex = new Map<number, MatchWireEvent>();
  for (const e of prev) byIndex.set(e.index, e);
  for (const e of incoming) byIndex.set(e.index, e);
  return [...byIndex.values()].sort((a, b) => a.index - b.index);
}

export function useMatchSession() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matchId, setMatchId] = useState<string | null>(null);
  const [state, setState] = useState<MatchState | null>(null);
  const [events, setEvents] = useState<MatchWireEvent[]>([]);
  const [stats, setStats] = useState<MatchStatistics | null>(null);
  const [homeTeam, setHomeTeam] = useState<TeamPayload | null>(null);
  const [awayTeam, setAwayTeam] = useState<TeamPayload | null>(null);
  const [roster, setRoster] = useState<Map<string, RosterEntry>>(new Map());
  const [replayHighlightIndex, setReplayHighlightIndex] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const lastIndexRef = useRef(-1);

  const buildRoster = useCallback((home: TeamPayload, away: TeamPayload) => {
    const map = new Map<string, RosterEntry>();
    for (const team of [home, away]) {
      team.starting_xi.forEach((p, i) => {
        map.set(p.id, { id: p.id, name: p.name, teamId: team.id, number: i + 1 });
      });
      team.bench.forEach((p) => {
        map.set(p.id, { id: p.id, name: p.name, teamId: team.id, number: 0 });
      });
    }
    setRoster(map);
  }, []);

  const refreshState = useCallback(async (id: string, withStats = true) => {
    const nextState = await getMatchState(id);
    setState(nextState);
    if (withStats) {
      const nextStats = await getStatistics(id).catch(() => null);
      if (nextStats) setStats(nextStats);
    }
    return nextState;
  }, []);

  const loadAllEvents = useCallback(async (id: string, finished: boolean) => {
    let full = await getEvents(id);
    if (finished) {
      try {
        const result = await getMatchResult(id);
        if (result.events.length > full.length) {
          full = result.events;
        }
      } catch {
        /* live or not persisted yet */
      }
    }
    setEvents(full);
    lastIndexRef.current = full.length > 0 ? full[full.length - 1].index : -1;
    return full;
  }, []);

  const syncFromBackend = useCallback(
    async (id: string) => {
      const nextState = await refreshState(id);
      await loadAllEvents(id, nextState.finished);
    },
    [loadAllEvents, refreshState],
  );

  const handleWireEvent = useCallback(
    (event: MatchWireEvent) => {
      setEvents((prev) => {
        if (prev.some((e) => e.index === event.index)) return prev;
        return mergeEvents(prev, [event]);
      });
      lastIndexRef.current = Math.max(lastIndexRef.current, event.index);

      if (matchId && shouldRefreshStats(event)) {
        void refreshState(matchId);
      }
    },
    [matchId, refreshState],
  );

  const connectStream = useCallback(
    (id: string) => {
      wsRef.current?.close();
      const ws = new WebSocket(matchWebSocketUrl(id));
      wsRef.current = ws;
      ws.onopen = () => {
        void syncFromBackend(id);
      };
      ws.onmessage = (message) => {
        const event = JSON.parse(message.data) as MatchWireEvent;
        handleWireEvent(event);
      };
      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
      };
    },
    [handleWireEvent, syncFromBackend],
  );

  const startNewMatch = useCallback(
    async (mode: "auto" | "controlled" = "controlled") => {
      setLoading(true);
      setError(null);
      setReplayHighlightIndex(null);
      try {
        const home = homeTeam ?? buildDemoTeam(`home_${Date.now()}`, "FC Phoenix", 64);
        const away = awayTeam ?? buildDemoTeam(`away_${Date.now()}`, "United City", 61);
        setHomeTeam(home);
        setAwayTeam(away);
        buildRoster(home, away);
        const { match_id } = await createMatch(home, away, { mode });
        setMatchId(match_id);
        setEvents([]);
        lastIndexRef.current = -1;
        await refreshState(match_id);
        await loadAllEvents(match_id, false);
        connectStream(match_id);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to start match");
      } finally {
        setLoading(false);
      }
    },
    [awayTeam, buildRoster, connectStream, homeTeam, loadAllEvents, refreshState],
  );

  useEffect(() => {
    if (!matchId || !state?.finished) return;
    void syncFromBackend(matchId);
  }, [matchId, state?.finished, syncFromBackend]);

  useEffect(() => {
    if (!homeTeam) setHomeTeam(buildDemoTeam("club_phoenix", "FC Phoenix", 64));
    if (!awayTeam) setAwayTeam(buildDemoTeam("club_united", "United City", 61));
  }, [awayTeam, homeTeam]);

  useEffect(() => () => wsRef.current?.close(), []);

  const pitch: PitchSnapshot | null = useMemo(() => {
    if (replayHighlightIndex != null) {
      const ev = events.find((e) => e.index === replayHighlightIndex);
      const snap = pitchFromEvent(ev);
      if (snap) return snap;
    }
    return latestPitch(events);
  }, [events, replayHighlightIndex]);

  const runAdvance = async (options: {
    steps?: number;
    targetMinute?: number;
    nextKey?: boolean;
    untilFinished?: boolean;
  }) => {
    if (!matchId) return;
    setReplayHighlightIndex(null);
    try {
      if (options.untilFinished || (options.steps ?? 0) > 8) {
        wsRef.current?.close();
      }
      const result = await advanceMatch(matchId, options);
      await syncFromBackend(matchId);
      if (result.finished) wsRef.current?.close();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Advance failed");
    }
  };

  const replayLastEvent = () => {
    if (events.length === 0) return;
    const last = events[events.length - 1];
    setReplayHighlightIndex(last.index);
  };

  const clearReplayHighlight = () => setReplayHighlightIndex(null);

  const togglePause = async () => {
    if (!matchId || !state) return;
    try {
      if (state.paused) await resumeMatch(matchId);
      else await pauseMatch(matchId);
      await refreshState(matchId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Pause failed");
    }
  };

  return {
    loading,
    error,
    matchId,
    state,
    events,
    stats,
    homeTeam,
    awayTeam,
    roster,
    pitch,
    replayHighlightIndex,
    setHomeTeam,
    setAwayTeam,
    startNewMatch,
    runAdvance,
    replayLastEvent,
    clearReplayHighlight,
    togglePause,
    async applyTactics(teamId: string, tactic: TeamPayload["tactic"]) {
      if (!matchId) return;
      await changeTactics(matchId, teamId, tactic);
      await syncFromBackend(matchId);
    },
    async applyFormation(teamId: string, formation: string) {
      if (!matchId) return;
      await changeFormation(matchId, teamId, formation);
      await syncFromBackend(matchId);
    },
    async applySubstitution(teamId: string, outId: string, inId: string) {
      if (!matchId) return;
      await substitute(matchId, teamId, outId, inId);
      await syncFromBackend(matchId);
    },
  };
}