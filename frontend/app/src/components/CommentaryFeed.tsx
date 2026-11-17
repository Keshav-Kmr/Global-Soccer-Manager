import { useEffect, useRef } from "react";
import type { MatchWireEvent } from "../types";

type Props = {
  events: MatchWireEvent[];
  replayHighlightIndex: number | null;
  homeTeamId: string | null;
  awayTeamId: string | null;
  onClearReplay?: () => void;
};

function teamSide(
  teamId: string | null,
  homeTeamId: string | null,
  awayTeamId: string | null,
): "home" | "away" | "neutral" {
  if (!teamId || !homeTeamId || !awayTeamId) return "neutral";
  if (teamId === homeTeamId) return "home";
  if (teamId === awayTeamId) return "away";
  return "neutral";
}

const KEY_TYPES = new Set([
  "goal",
  "penalty_goal",
  "card",
  "injury",
  "substitution",
  "half_time",
  "full_time",
  "shot",
]);

export function CommentaryFeed({
  events,
  replayHighlightIndex,
  homeTeamId,
  awayTeamId,
  onClearReplay,
}: Props) {
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    if (replayHighlightIndex == null) {
      listRef.current?.lastElementChild?.scrollIntoView({ behavior: "smooth" });
      return;
    }
    const el = listRef.current?.querySelector(`[data-event-index="${replayHighlightIndex}"]`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [events.length, replayHighlightIndex]);

  return (
    <section className="panel commentary">
      <div className="commentary__header">
        <h2 className="panel__title">Match events ({events.length})</h2>
        {replayHighlightIndex != null && (
          <button type="button" className="btn btn--ghost" onClick={onClearReplay}>
            Exit replay view
          </button>
        )}
      </div>
      <ul className="commentary__list" ref={listRef}>
        {events.map((ev) => {
          const isReplay = replayHighlightIndex === ev.index;
          const side = teamSide(ev.team, homeTeamId, awayTeamId);
          return (
            <li
              key={ev.index}
              data-event-index={ev.index}
              className={[
                "commentary__item",
                `commentary__item--${side}`,
                KEY_TYPES.has(ev.type) ? "commentary__item--key" : "",
                isReplay ? "commentary__item--replay" : "",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <span className="commentary__minute">{ev.minute}&apos;</span>
              <div className="commentary__line">
                {isReplay && <span className="commentary__replay-badge">REPLAY</span>}
                <span className="commentary__type">{ev.type.replaceAll("_", " ")}</span>
                <span className="commentary__text">{ev.commentary}</span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}