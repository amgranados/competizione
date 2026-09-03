import { T } from "../../styles/theme.js";

const variants = {
  ac: { background: T.acD, color: T.ac },
  green: { background: "rgba(34,197,94,0.13)", color: "#4ade80" },
  orange: { background: "rgba(251,146,60,0.13)", color: "#fb923c" },
  blue: { background: "rgba(99,179,237,0.13)", color: "#63b3ed" },
  default: { background: T.s4, color: T.tx2 },
};

const base = {
  display: "inline-flex",
  alignItems: "center",
  padding: "3px 8px",
  borderRadius: 4,
  fontSize: 10,
  fontWeight: 700,
  fontFamily: T.fM,
  letterSpacing: 0.8,
  textTransform: "uppercase",
};

export default function Tag({ variant = "default", children, style }) {
  return <span style={{ ...base, ...variants[variant], ...style }}>{children}</span>;
}
