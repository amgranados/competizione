import { T } from "../styles/theme.js";
import Ava from "./ui/Ava.jsx";
import Tag from "./ui/Tag.jsx";

const headerStyle = {
  fontFamily: T.fM,
  fontSize: 10,
  letterSpacing: 1,
  color: T.tx3,
  textTransform: "uppercase",
  textAlign: "left",
  padding: "8px 10px",
  borderBottom: `1px solid ${T.bd}`,
  fontWeight: 600,
};

const cellStyle = {
  padding: "10px",
  fontSize: 13,
  color: T.tx,
  borderBottom: `1px solid ${T.bd}`,
};

export default function StandingsTable({ entries }) {
  if (!entries || entries.length === 0) {
    return <p style={{ color: T.tx3, fontSize: 12 }}>Sin clasificación aún.</p>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ ...headerStyle, width: 40 }}>#</th>
            <th style={headerStyle}>Jugador</th>
            <th style={{ ...headerStyle, textAlign: "right", width: 40 }}>V</th>
            <th style={{ ...headerStyle, textAlign: "right", width: 40 }}>D</th>
            <th style={{ ...headerStyle, textAlign: "right", width: 50 }}>Bye</th>
            <th style={{ ...headerStyle, textAlign: "right", width: 60 }}>Pts</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e, idx) => {
            const isLast = idx === entries.length - 1;
            const cell = isLast ? { ...cellStyle, borderBottom: "none" } : cellStyle;
            return (
              <tr key={e.participant_id}>
                <td style={{ ...cell, fontFamily: T.fM, color: T.tx3, fontSize: 12 }}>
                  {e.rank === 1 ? <Tag variant="ac">1</Tag> : e.rank}
                </td>
                <td style={cell}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <Ava name={e.nickname} size={26} />
                    <span style={{ fontWeight: 600 }}>{e.nickname}</span>
                  </div>
                </td>
                <td style={{ ...cell, textAlign: "right", fontFamily: T.fM, fontSize: 12 }}>
                  {e.wins}
                </td>
                <td style={{ ...cell, textAlign: "right", fontFamily: T.fM, fontSize: 12, color: T.tx2 }}>
                  {e.losses}
                </td>
                <td style={{ ...cell, textAlign: "right", fontFamily: T.fM, fontSize: 12, color: T.tx3 }}>
                  {e.byes}
                </td>
                <td
                  style={{
                    ...cell,
                    textAlign: "right",
                    fontFamily: T.fH,
                    fontSize: 16,
                    fontWeight: 700,
                  }}
                >
                  {e.points}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
