import { T } from "../../styles/theme.js";

const base = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 6,
  borderRadius: T.r,
  fontWeight: 500,
  fontFamily: T.fB,
  letterSpacing: 0.2,
  whiteSpace: "nowrap",
  cursor: "pointer",
  transition: "filter .12s, background .12s, border-color .12s",
  userSelect: "none",
};

const sizes = {
  sm: { padding: "6px 13px", fontSize: 12 },
  default: { padding: "10px 20px", fontSize: 13 },
};

const variants = {
  primary: { background: T.ac, color: T.tx, border: "1px solid transparent" },
  ghost: { background: "transparent", border: `1px solid ${T.bd}`, color: T.tx },
  disabled: { background: T.s4, color: T.tx3, border: "1px solid transparent", cursor: "not-allowed" },
};

export default function Btn({
  variant = "primary",
  size = "default",
  disabled = false,
  style,
  children,
  ...rest
}) {
  const effectiveVariant = disabled ? "disabled" : variant;
  return (
    <button
      {...rest}
      disabled={disabled}
      style={{ ...base, ...sizes[size], ...variants[effectiveVariant], ...style }}
      onMouseOver={(e) => {
        if (!disabled) e.currentTarget.style.filter = "brightness(1.1)";
      }}
      onMouseOut={(e) => {
        e.currentTarget.style.filter = "none";
      }}
    >
      {children}
    </button>
  );
}
