import { T } from "../../styles/theme.js";

export default function Ava({ name, size = 30, ring = false, src = null }) {
  const safe = name ?? "?";
  const hue = [...safe].reduce((acc, ch) => acc + ch.charCodeAt(0), 0) % 360;
  const initials = safe.slice(0, 2).toUpperCase();
  const border = ring ? `2px solid ${T.ac}` : `2px solid rgba(255,255,255,0.08)`;

  if (src) {
    return (
      <img
        src={src}
        alt={safe}
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          objectFit: "cover",
          border,
          flexShrink: 0,
        }}
      />
    );
  }

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: `oklch(0.32 0.1 ${hue})`,
        color: `oklch(0.88 0.08 ${hue})`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: T.fH,
        fontSize: Math.max(10, Math.round(size * 0.36)),
        fontWeight: 700,
        border,
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  );
}
