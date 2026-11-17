/**
 * Smoke test: create a controlled match, advance, fetch events + stats.
 * Usage: node scripts/verify-backend.mjs (backend must be on :8000)
 */

const API = process.env.API_BASE ?? "http://127.0.0.1:8000";

const FORMATION = ["GK", "CB", "CB", "FB", "FB", "DM", "CM", "CM", "W", "ST", "W"];
const ATTRS = [
  "pace", "dribbling", "passing", "vision", "shooting", "tackling",
  "marking", "strength", "positioning", "aggression", "composure", "stamina", "flair",
];

function player(id, name, position, overall = 60) {
  const attributes = Object.fromEntries(ATTRS.map((a) => [a, overall]));
  return { id, name, position, attributes };
}

function team(id, name) {
  return {
    id,
    name,
    formation: "4-3-3",
    tactic: {
      mentality: "balanced",
      tempo: "normal",
      pressing: "medium",
      width: "normal",
      defensive_line: "normal",
      marking_scheme: "zonal",
    },
    starting_xi: FORMATION.map((pos, i) => player(`${id}_${i}`, `${name} #${i}`, pos)),
    bench: [player(`${id}_sub`, `${name} Sub`, "ST", 65)],
  };
}

async function main() {
  const create = await fetch(`${API}/matches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mode: "controlled",
      seed: 99,
      team_a: team("vh", "Verify Home"),
      team_b: team("va", "Verify Away"),
      weather: "clear",
    }),
  });
  if (!create.ok) throw new Error(await create.text());
  const { match_id } = await create.json();

  const adv = await fetch(`${API}/matches/${match_id}/advance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ steps: 3 }),
  });
  if (!adv.ok) throw new Error(await adv.text());

  const events = await fetch(`${API}/matches/${match_id}/events`).then((r) => r.json());
  const stats = await fetch(`${API}/matches/${match_id}/statistics`).then((r) => r.json());
  const hasPitch = events.some((e) => e.payload?.pitch?.players);

  console.log(JSON.stringify({ match_id, eventCount: events.length, hasPitch, statsTeams: Object.keys(stats.teams) }));
  if (events.length < 2 || !hasPitch) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});