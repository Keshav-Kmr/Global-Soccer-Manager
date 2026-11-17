import { useEffect, useRef } from "react";
import type { MatchWireEvent } from "../types";

type Props = { events: MatchWireEvent[] };

const KEY_TYPES = new Set(["goal", "card", "injury", "substitution", "half_time", "full_time", "shot"]);

export function CommentaryFeed({ events }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <section className="panel commentary">
      <h2 className="panel__title">Match events</h2>
      <ul className="commentary__list">
        {events.map((ev, index) => (
          <li
            key={`${ev.minute}-${ev.type}-${index}`}
            className={`commentary__item${KEY_TYPES.has(ev.type) ? " commentary__item--key" : ""}`}
          >
            <span className="commentary__minute">{ev.minute}&apos;</span>
            <span className="commentary__text">{ev.commentary}</span>
          </li>
        ))}
      </ul>
      <div ref={bottomRef} />
    </section>
  );
}