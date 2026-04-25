import { T } from "../../styles/theme.js";

export default function Card({ children, style, accent = false, hoverable = true, ...rest }) {
  return (
    <div
      {...rest}
      style={{
        position: "relative",
        background: T.s2,
        border: `1px solid ${T.bd}`,
        borderRadius: T.r2,
        padding: 18,
        overflow: "hidden",
        transition: "border-color .12s",
        ...style,
      }}
      onMouseOver={(e) => {
        if (hoverable) e.currentTarget.style.borderColor = T.bdM;
        rest.onMouseOver?.(e);
      }}
      onMouseOut={(e) => {
        if (hoverable) e.currentTarget.style.borderColor = T.bd;
        rest.onMouseOut?.(e);
      }}
    >
      {accent && (
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 2,
            background: T.ac,
          }}
        />
      )}
      {children}
    </div>
  );
}
