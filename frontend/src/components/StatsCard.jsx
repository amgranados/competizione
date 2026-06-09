import Card from "./ui/Card.jsx";
import { T } from "../styles/theme.js";

/**
 * A single dashboard metric card (005-user-dashboard, US1).
 *
 * Props:
 * - label:    uppercase caption (e.g. "Torneos activos").
 * - value:    the main metric (number or string).
 * - delta:    optional weekly variation. Positive renders "+N", negative "-N",
 *             zero renders "0" (no sign), null/undefined renders nothing.
 * - subvalue: optional secondary text shown next to the value (e.g. winrate
 *             "60%"); handled gracefully when "0%".
 * - accent:   draws the accent bar on top of the card.
 */
export default function StatsCard({ label, value, delta = null, subvalue = null, accent = false }) {
  return (
    <Card accent={accent}>
      <div
        style={{
          fontFamily: T.fM,
          fontSize: 10,
          color: T.tx3,
          textTransform: "uppercase",
          letterSpacing: 1,
          marginBottom: 10,
        }}
      >
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
        <div
          style={{
            fontFamily: T.fH,
            fontSize: 30,
            fontWeight: 700,
            letterSpacing: "-1px",
            lineHeight: 1,
          }}
        >
          {value}
        </div>
        {subvalue != null && (
          <div style={{ fontFamily: T.fM, fontSize: 13, color: T.tx2 }}>{subvalue}</div>
        )}
        <DeltaBadge delta={delta} />
      </div>
    </Card>
  );
}

function DeltaBadge({ delta }) {
  if (delta == null) return null;
  const positive = delta > 0;
  const negative = delta < 0;
  // Positive gets an explicit "+"; negative numbers already render their "-";
  // zero renders plain "0" with no sign.
  const text = positive ? `+${delta}` : `${delta}`;
  const color = positive ? "#4ade80" : negative ? T.ac : T.tx3;
  return (
    <span
      style={{
        fontFamily: T.fM,
        fontSize: 12,
        fontWeight: 700,
        color,
      }}
    >
      {text}
    </span>
  );
}
