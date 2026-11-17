import type { TeamPayload } from "./types";

/** Mirrors backend `FORMATION_SLOTS` in app/domain/formation.py */
export const FORMATION_OPTIONS = ["4-3-3", "4-2-3-1", "4-4-2", "3-5-2", "3-4-3", "5-3-2"] as const;

export type FormationCode = (typeof FORMATION_OPTIONS)[number];

export const FORMATION_SLOTS: Record<FormationCode, string[]> = {
  "4-3-3": ["GK", "CB", "CB", "FB", "FB", "DM", "CM", "CM", "W", "ST", "W"],
  "4-2-3-1": ["GK", "CB", "CB", "FB", "FB", "DM", "DM", "W", "AM", "W", "ST"],
  "4-4-2": ["GK", "CB", "CB", "FB", "FB", "CM", "CM", "W", "W", "ST", "ST"],
  "3-5-2": ["GK", "CB", "CB", "CB", "FB", "DM", "CM", "CM", "FB", "ST", "ST"],
  "3-4-3": ["GK", "CB", "CB", "CB", "CM", "CM", "W", "W", "AM", "ST", "W"],
  "5-3-2": ["GK", "FB", "CB", "CB", "CB", "FB", "CM", "CM", "DM", "ST", "ST"],
};

export function isFormationCode(value: string): value is FormationCode {
  return (FORMATION_OPTIONS as readonly string[]).includes(value);
}

/** Re-label each starting XI slot so the lineup validates for the chosen formation. */
export function applyFormationToTeam(team: TeamPayload, formation: FormationCode): TeamPayload {
  const slots = FORMATION_SLOTS[formation];
  if (team.starting_xi.length !== slots.length) {
    return { ...team, formation };
  }
  return {
    ...team,
    formation,
    starting_xi: team.starting_xi.map((player, index) => ({
      ...player,
      position: slots[index],
    })),
  };
}