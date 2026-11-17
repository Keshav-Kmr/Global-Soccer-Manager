export type PitchSnapshot = {
  ball: { x: number; y: number };
  possession_team_id: string | null;
  ball_carrier_id: string | null;
  players: Record<string, { x: number; y: number }>;
};

export type MatchWireEvent = {
  index: number;
  minute: number;
  type: string;
  team: string | null;
  players: string[];
  payload: Record<string, unknown> & { pitch?: PitchSnapshot; color?: string };
  commentary: string;
};

export type MatchClock = {
  period: string;
  first_half_stoppage: number;
  second_half_stoppage: number;
  display_minute: number;
  regulation_first_half_end: number;
  regulation_match_end: number;
};

export type MatchState = {
  match_id: string;
  mode: string;
  minute: number;
  paused: boolean;
  finished: boolean;
  score: Record<string, number>;
  team_a_id: string;
  team_b_id: string;
  seed: number;
  clock?: MatchClock | null;
};

export type TeamPlayer = {
  id: string;
  name: string;
  position: string;
  attributes: Record<string, number>;
};

export type TeamPayload = {
  id: string;
  name: string;
  starting_xi: TeamPlayer[];
  bench: TeamPlayer[];
  formation: string;
  tactic: Record<string, string>;
};

export type TeamStatisticsRow = {
  goals: number;
  shots: number;
  shots_on_target: number;
  shots_off_target?: number;
  blocked_shots?: number;
  fouls: number;
  yellow_cards?: number;
  red_cards?: number;
  possession_pct: number;
  passes_completed?: number;
  passes_attempted?: number;
  pass_completion_pct?: number;
  offsides?: number;
  penalties?: number;
  saves?: number;
  tackles?: number;
};

export type PlayerStatisticsRow = {
  minutes_played: number;
  goals: number;
  shots: number;
  shots_on_target: number;
  fouls_committed: number;
  yellow_cards: number;
  red_cards: number;
};

export type MatchStatistics = {
  teams: Record<string, TeamStatisticsRow>;
  players: Record<string, PlayerStatisticsRow>;
};

export type RosterEntry = { id: string; name: string; teamId: string; number: number };