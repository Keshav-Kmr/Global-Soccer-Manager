import type {
  MatchState,
  MatchStatistics,
  MatchWireEvent,
  TeamPayload,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";
const REQUEST_TIMEOUT_MS = 15_000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`${response.status}: ${detail}`);
    }
    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Request timed out — is the API running at ${API_BASE}?`);
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

const FORMATION_433 = ["GK", "CB", "CB", "FB", "FB", "DM", "CM", "CM", "W", "ST", "W"] as const;
const ATTRS = [
  "pace", "dribbling", "passing", "vision", "shooting", "tackling",
  "marking", "strength", "positioning", "aggression", "composure", "stamina", "flair",
] as const;

export function buildDemoTeam(teamId: string, name: string, overall = 62): TeamPayload {
  const attributes = Object.fromEntries(ATTRS.map((a) => [a, overall]));
  const starting_xi = FORMATION_433.map((position, i) => ({
    id: `${teamId}_${i}`,
    name: `${name} #${i + 1}`,
    position,
    attributes: { ...attributes, reflexes: 65, handling: 65, gk_positioning: 65 },
  }));
  const bench = [
    {
      id: `${teamId}_sub0`,
      name: `${name} Sub ST`,
      position: "ST",
      attributes: { ...attributes },
    },
  ];
  return {
    id: teamId,
    name,
    starting_xi,
    bench,
    formation: "4-3-3",
    tactic: {
      mentality: "balanced",
      tempo: "normal",
      pressing: "medium",
      width: "normal",
      defensive_line: "normal",
      marking_scheme: "zonal",
    },
  };
}

export function pitchFromEvent(event: MatchWireEvent | undefined): import("../types").PitchSnapshot | null {
  const pitch = event?.payload?.pitch;
  if (pitch?.players) return pitch;
  return null;
}

export async function createMatch(
  teamA: TeamPayload,
  teamB: TeamPayload,
  options?: { seed?: number; mode?: "auto" | "controlled" },
): Promise<{ match_id: string }> {
  return request("/matches", {
    method: "POST",
    body: JSON.stringify({
      team_a: teamA,
      team_b: teamB,
      seed: options?.seed ?? Math.floor(Math.random() * 1_000_000),
      mode: options?.mode ?? "controlled",
      weather: "clear",
    }),
  });
}

export function matchWebSocketUrl(matchId: string): string {
  const base = import.meta.env.VITE_WS_BASE;
  if (base) {
    return `${base}/matches/${matchId}/stream`;
  }
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.host;
  return `${protocol}://${host}/api/matches/${matchId}/stream`;
}

export async function getMatchState(matchId: string): Promise<MatchState> {
  return request(`/matches/${matchId}`);
}

export async function getEvents(matchId: string, sinceIndex = 0): Promise<MatchWireEvent[]> {
  const q = sinceIndex > 0 ? `?since_index=${sinceIndex}` : "";
  return request(`/matches/${matchId}/events${q}`);
}

export async function getMatchResult(matchId: string): Promise<{
  events: MatchWireEvent[];
  score_a: number;
  score_b: number;
  seed: number;
}> {
  return request(`/matches/${matchId}/result`);
}

export async function listTeams(): Promise<TeamPayload[]> {
  return request("/teams");
}

export async function saveTeam(team: TeamPayload): Promise<TeamPayload> {
  return request("/teams", { method: "POST", body: JSON.stringify(team) });
}

export async function getStatistics(matchId: string): Promise<MatchStatistics> {
  return request(`/matches/${matchId}/statistics`);
}

export async function advanceMatch(
  matchId: string,
  options: {
    steps?: number;
    targetMinute?: number;
    nextKey?: boolean;
    untilFinished?: boolean;
  } = {},
) {
  const body: Record<string, unknown> = { steps: options.steps ?? 1 };
  if (options.targetMinute != null) body.target_minute = options.targetMinute;
  if (options.nextKey) body.next_key_event = true;
  if (options.untilFinished) body.until_finished = true;
  return request<{ advanced_chains: number; finished: boolean; minute: number }>(
    `/matches/${matchId}/advance`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function pauseMatch(matchId: string) {
  return request(`/matches/${matchId}/pause`, { method: "POST" });
}

export async function resumeMatch(matchId: string) {
  return request(`/matches/${matchId}/resume`, { method: "POST" });
}

export async function changeTactics(matchId: string, teamId: string, tactic: TeamPayload["tactic"]) {
  return request(`/matches/${matchId}/tactics`, {
    method: "POST",
    body: JSON.stringify({ team_id: teamId, tactic }),
  });
}

export async function changeFormation(matchId: string, teamId: string, formation: string) {
  return request(`/matches/${matchId}/formation`, {
    method: "POST",
    body: JSON.stringify({ team_id: teamId, formation }),
  });
}

export async function substitute(
  matchId: string,
  teamId: string,
  playerOutId: string,
  playerInId: string,
) {
  return request(`/matches/${matchId}/substitutions`, {
    method: "POST",
    body: JSON.stringify({ team_id: teamId, player_out_id: playerOutId, player_in_id: playerInId }),
  });
}

export function latestPitch(events: MatchWireEvent[]): import("../types").PitchSnapshot | null {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const pitch = events[i].payload?.pitch;
    if (pitch?.players) {
      return pitch;
    }
  }
  return null;
}