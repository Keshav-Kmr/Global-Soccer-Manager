import { describe, expect, it } from "vitest";
import { buildDemoTeam, latestPitch } from "./client";
import type { MatchWireEvent } from "../types";

describe("buildDemoTeam", () => {
  it("builds a valid 4-3-3 squad for the API", () => {
    const team = buildDemoTeam("t1", "Rovers", 60);
    expect(team.starting_xi).toHaveLength(11);
    expect(team.formation).toBe("4-3-3");
    expect(team.starting_xi[0].position).toBe("GK");
  });
});

describe("latestPitch", () => {
  it("returns the most recent pitch snapshot from events", () => {
    const events: MatchWireEvent[] = [
      {
        index: 0,
        minute: 0,
        type: "kickoff",
        team: "home",
        players: [],
        payload: { pitch: { ball: { x: 50, y: 50 }, players: {}, possession_team_id: null, ball_carrier_id: null } },
        commentary: "Kickoff",
      },
      {
        index: 1,
        minute: 2,
        type: "possession_progress",
        team: "home",
        players: ["p1"],
        payload: {
          pitch: {
            ball: { x: 55, y: 50 },
            players: { p1: { x: 54, y: 50 } },
            possession_team_id: "home",
            ball_carrier_id: "p1",
          },
        },
        commentary: "Progress",
      },
    ];
    expect(latestPitch(events)?.ball.x).toBe(55);
  });
});