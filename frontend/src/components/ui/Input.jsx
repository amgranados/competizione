import { forwardRef, useId } from "react";
import { T } from "../../styles/theme.js";

const labelStyle = {
  display: "block",
  fontFamily: T.fB,
  fontSize: 12,
  fontWeight: 500,
  color: T.tx2,
  letterSpacing: 0.3,
  marginBottom: 6,
};

const wrapperStyle = {
  background: T.s3,
  border: `1px solid ${T.bd}`,
  borderRadius: T.r,
  padding: "10px 13px",
  display: "flex",
  alignItems: "center",
  gap: 10,
  transition: "border-color .12s",
};

const inputStyle = {
  flex: 1,
  background: "transparent",
  border: "none",
  outline: "none",
  color: T.tx,
  fontFamily: T.fB,
  fontSize: 13,
  width: "100%",
};

const Input = forwardRef(function Input(
  { label, id, icon, hint, error, type = "text", ...rest },
  ref
) {
  const autoId = useId();
  const inputId = id ?? autoId;

  return (
    <div>
      {label && (
        <label htmlFor={inputId} style={labelStyle}>
          {label}
        </label>
      )}
      <div
        style={{
          ...wrapperStyle,
          borderColor: error ? T.ac : T.bd,
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = T.bdM;
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = error ? T.ac : T.bd;
        }}
      >
        {icon}
        <input ref={ref} id={inputId} type={type} style={inputStyle} {...rest} />
      </div>
      {hint && !error && (
        <p style={{ marginTop: 6, fontSize: 11, color: T.tx3, fontFamily: T.fB }}>{hint}</p>
      )}
      {error && (
        <p style={{ marginTop: 6, fontSize: 11, color: T.ac, fontFamily: T.fB }}>{error}</p>
      )}
    </div>
  );
});

export default Input;
