import { describe, expect, it } from "vitest";
import { applyFormationToTeam } from "./formations";
import { buildDemoTeam } from "./api/client";

describe("applyFormationToTeam", () => {
  it("relabels XI slots for 4-4-2", () => {
    const team = buildDemoTeam("t1", "Test", 60);
    const next = applyFormationToTeam(team, "4-4-2");
    expect(next.formation).toBe("4-4-2");
    expect(next.starting_xi.map((p) => p.position)).toEqual([
      "GK", "CB", "CB", "FB", "FB", "CM", "CM", "W", "W", "ST", "ST",
    ]);
  });
});