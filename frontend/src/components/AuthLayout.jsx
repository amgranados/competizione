import { T } from "../styles/theme.js";

const FEATURES = [
  { title: "Sesiones seguras", desc: "JWT en cookies HttpOnly con rotación automática." },
  { title: "Protección de cuenta", desc: "Bloqueo tras 10 intentos fallidos en 15 minutos." },
  { title: "Login constante", desc: "Respuestas y tiempos indistinguibles ante credenciales inválidas." },
];

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div
      className="route-fade"
      style={{
        display: "flex",
        height: "100%",
        background: T.bg,
        color: T.tx,
        fontFamily: T.fB,
      }}
    >
      {/* Branding panel */}
      <aside
        style={{
          position: "relative",
          width: 520,
          flexShrink: 0,
          background: T.s1,
          borderRight: `1px solid ${T.bd}`,
          padding: "48px 56px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          overflow: "hidden",
        }}
      >
        {/* Decoration */}
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            top: -120,
            left: -120,
            width: 400,
            height: 400,
            border: `1px solid ${T.bd}`,
            borderRadius: "50%",
          }}
        />
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            top: -60,
            left: -60,
            width: 260,
            height: 260,
            border: `1px solid ${T.bdM}`,
            borderRadius: "50%",
          }}
        />
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            bottom: -100,
            right: -80,
            width: 320,
            height: 320,
            background: `radial-gradient(circle, ${T.acD} 0%, transparent 70%)`,
            borderRadius: "50%",
            pointerEvents: "none",
          }}
        />

        <div style={{ position: "relative", zIndex: 1 }}>
          <Logo />
        </div>

        <div style={{ position: "relative", zIndex: 1 }}>
          <h2
            style={{
              fontFamily: T.fH,
              fontSize: 36,
              fontWeight: 700,
              letterSpacing: "-1.2px",
              lineHeight: 1.1,
              marginBottom: 14,
            }}
          >
            Compite. Mejora. Domina.
          </h2>
          <p
            style={{
              fontFamily: T.fB,
              fontSize: 14,
              color: T.tx2,
              lineHeight: 1.5,
              maxWidth: 380,
              marginBottom: 28,
            }}
          >
            La plataforma para equipos y jugadores que quieren llevar sus estadísticas, torneos y progresión al siguiente nivel.
          </p>

          <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 16 }}>
            {FEATURES.map((f) => (
              <li key={f.title} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                <span
                  aria-hidden="true"
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: T.ac,
                    marginTop: 7,
                    flexShrink: 0,
                  }}
                />
                <div>
                  <div
                    style={{
                      fontFamily: T.fB,
                      fontSize: 13,
                      fontWeight: 600,
                      color: T.tx,
                      marginBottom: 2,
                    }}
                  >
                    {f.title}
                  </div>
                  <div style={{ fontFamily: T.fB, fontSize: 12, color: T.tx2, lineHeight: 1.4 }}>
                    {f.desc}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div style={{ position: "relative", zIndex: 1 }}>
          <span
            style={{
              fontFamily: T.fM,
              fontSize: 10,
              letterSpacing: 1.2,
              textTransform: "uppercase",
              color: T.tx3,
            }}
          >
            v0.1.0 · BUILD DEV
          </span>
        </div>
      </aside>

      {/* Form panel */}
      <main
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "48px 24px",
          overflow: "auto",
        }}
      >
        <div style={{ width: "100%", maxWidth: 380 }}>
          <h1
            style={{
              fontFamily: T.fH,
              fontSize: 26,
              fontWeight: 700,
              letterSpacing: "-0.5px",
              marginBottom: 8,
            }}
          >
            {title}
          </h1>
          {subtitle && (
            <p
              style={{
                fontFamily: T.fB,
                fontSize: 14,
                color: T.tx2,
                marginBottom: 28,
                lineHeight: 1.4,
              }}
            >
              {subtitle}
            </p>
          )}

          {children}

          {footer && (
            <div
              style={{
                marginTop: 28,
                fontFamily: T.fB,
                fontSize: 13,
                color: T.tx2,
                textAlign: "center",
              }}
            >
              {footer}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function Logo() {
  return (
    <div>
      <div
        style={{
          fontFamily: T.fH,
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: "-0.6px",
          color: T.tx,
        }}
      >
        <span style={{ color: T.ac }}>C</span>ompetizione
      </div>
      <div
        style={{
          fontFamily: T.fM,
          fontSize: 10,
          letterSpacing: 1.2,
          textTransform: "uppercase",
          color: T.tx3,
          marginTop: 4,
        }}
      >
        ESPORTS · ANALYTICS
      </div>
    </div>
  );
}
