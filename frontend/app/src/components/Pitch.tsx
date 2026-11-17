import type { PitchSnapshot, RosterEntry, TeamPayload } from "../types";

const PITCH_W = 105;
const PITCH_H = 68;

type Props = {
  pitch: PitchSnapshot | null;
  roster: Map<string, RosterEntry>;
  home: TeamPayload | null;
  away: TeamPayload | null;
};

function toSvg(x: number, y: number): { cx: number; cy: number } {
  return {
    cx: (x / 100) * PITCH_W,
    cy: (y / 100) * PITCH_H,
  };
}

export function Pitch({ pitch, roster, home }: Props) {
  const playerEntries = pitch ? Object.entries(pitch.players) : [];

  return (
    <div className="pitch-wrap">
      <svg
        className="pitch"
        viewBox={`0 0 ${PITCH_W} ${PITCH_H}`}
        role="img"
        aria-label="Football pitch"
      >
        <defs>
          <linearGradient id="grass" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2d6a3e" />
            <stop offset="100%" stopColor="#1e4d2b" />
          </linearGradient>
        </defs>
        <rect width={PITCH_W} height={PITCH_H} fill="url(#grass)" rx="1" />
        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
          <rect
            key={i}
            x={0}
            y={(i * PITCH_H) / 10}
            width={PITCH_W}
            height={PITCH_H / 10}
            fill={i % 2 === 0 ? "rgba(255,255,255,0.04)" : "transparent"}
          />
        ))}
        <rect
          x={1}
          y={1}
          width={PITCH_W - 2}
          height={PITCH_H - 2}
          fill="none"
          stroke="rgba(255,255,255,0.55)"
          strokeWidth={0.35}
        />
        <line
          x1={PITCH_W / 2}
          y1={0}
          x2={PITCH_W / 2}
          y2={PITCH_H}
          stroke="rgba(255,255,255,0.45)"
          strokeWidth={0.25}
        />
        <circle
          cx={PITCH_W / 2}
          cy={PITCH_H / 2}
          r={9}
          fill="none"
          stroke="rgba(255,255,255,0.4)"
          strokeWidth={0.25}
        />
        <rect x={0} y={PITCH_H * 0.22} width={16} height={PITCH_H * 0.56} fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth={0.25} />
        <rect x={PITCH_W - 16} y={PITCH_H * 0.22} width={16} height={PITCH_H * 0.56} fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth={0.25} />

        {pitch && (
          <g className="pitch__ball">
            {(() => {
              const { cx, cy } = toSvg(pitch.ball.x, pitch.ball.y);
              return (
                <circle
                  cx={cx}
                  cy={cy}
                  r={1.8}
                  fill="#f5f5f4"
                  stroke="#1c1917"
                  strokeWidth={0.2}
                  className="pitch__ball-dot"
                />
              );
            })()}
          </g>
        )}

        {playerEntries.map(([id, pos]) => {
          const { cx, cy } = toSvg(pos.x, pos.y);
          const entry = roster.get(id);
          const isHome = entry?.teamId === home?.id;
          const fill = isHome ? "#2563eb" : "#dc2626";
          const stroke = isHome ? "#93c5fd" : "#fca5a5";
          return (
            <g key={id} className="pitch__player pitch__player--animated">
              <circle cx={cx} cy={cy} r={2.2} fill={fill} stroke={stroke} strokeWidth={0.25} />
              <text x={cx} y={cy + 0.65} textAnchor="middle" fontSize={1.6} fill="#fff" fontWeight={700}>
                {entry?.number || "?"}
              </text>
              <title>{entry?.name ?? id}</title>
            </g>
          );
        })}
      </svg>
      {!pitch && <p className="pitch-wrap__hint">Waiting for pitch data from the engine…</p>}
    </div>
  );
}