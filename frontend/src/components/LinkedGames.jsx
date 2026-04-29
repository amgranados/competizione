import { useState } from "react";
import { profileApi } from "../api/profileApi.js";
import Card from "./ui/Card.jsx";
import Btn from "./ui/Btn.jsx";
import Tag from "./ui/Tag.jsx";
import Input from "./ui/Input.jsx";
import Icon from "./ui/Icon.jsx";
import { T } from "../styles/theme.js";

const PLATFORMS = [
  "EUW1",
  "EUN1",
  "TR1",
  "RU",
  "NA1",
  "BR1",
  "LA1",
  "LA2",
  "OC1",
  "KR",
  "JP1",
];

export default function LinkedGames({ profile, onUpdated, readOnly = false }) {
  const lolLinked = profile.linked_games?.find((game) => game.game === "lol");

  if (lolLinked) {
    return <LinkedLoL linkedGame={lolLinked} onUpdated={onUpdated} readOnly={readOnly} />;
  }
  if (readOnly) {
    return (
      <Card hoverable={false}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: T.r2,
              background: T.acD,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: T.ac,
            }}
          >
            <Icon name="trophy" size={20} />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>League of Legends</div>
            <div
              style={{
                fontFamily: T.fM,
                fontSize: 10,
                color: T.tx3,
                letterSpacing: 1,
                textTransform: "uppercase",
              }}
            >
              Sin cuenta vinculada
            </div>
          </div>
        </div>
      </Card>
    );
  }
  return <UnlinkedLoL onUpdated={onUpdated} />;
}

function UnlinkedLoL({ onUpdated }) {
  const [open, setOpen] = useState(false);

  return (
    <Card hoverable={false}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: open ? 16 : 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: T.r2,
              background: T.acD,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: T.ac,
            }}
          >
            <Icon name="trophy" size={20} />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>League of Legends</div>
            <div
              style={{
                fontFamily: T.fM,
                fontSize: 10,
                color: T.tx3,
                letterSpacing: 1,
                textTransform: "uppercase",
              }}
            >
              No vinculado
            </div>
          </div>
        </div>
        <Btn size="sm" onClick={() => setOpen((value) => !value)} variant={open ? "ghost" : "primary"}>
          {open ? (
            <>
              <Icon name="x" size={12} />
              Cancelar
            </>
          ) : (
            <>
              <Icon name="link" size={12} />
              Vincular LoL
            </>
          )}
        </Btn>
      </div>
      {open && <LinkLoLForm onUpdated={onUpdated} />}
    </Card>
  );
}

function LinkLoLForm({ onUpdated }) {
  const [gameName, setGameName] = useState("");
  const [tagLine, setTagLine] = useState("");
  const [region, setRegion] = useState("EUW1");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await profileApi.linkLoL({ game_name: gameName, tag_line: tagLine, region });
      await onUpdated?.();
    } catch (err) {
      if (err?.status === 503) {
        setError("Riot no está disponible temporalmente. Inténtalo de nuevo en unos minutos.");
      } else if (err?.status === 409) {
        setError(err?.detail ?? "Ya existe una vinculación. Desvincúlala antes de vincular otra.");
      } else {
        setError("No se pudo vincular la cuenta de Riot. Verifica los datos introducidos.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      aria-label="Vincular LoL"
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 130px auto",
        gap: 10,
        alignItems: "end",
        paddingTop: 14,
        borderTop: `1px solid ${T.bd}`,
      }}
    >
      <Input
        label="Riot ID (game name)"
        value={gameName}
        onChange={(event) => setGameName(event.target.value)}
        icon={<Icon name="user" />}
      />
      <Input
        label="Tag line"
        value={tagLine}
        onChange={(event) => setTagLine(event.target.value)}
      />
      <RegionSelect value={region} onChange={setRegion} />
      <Btn type="submit" disabled={submitting}>
        <Icon name="link" size={13} />
        {submitting ? "Vinculando…" : "Vincular"}
      </Btn>
      {error && (
        <p
          role="alert"
          style={{
            gridColumn: "1 / -1",
            fontSize: 12,
            color: T.ac,
            marginTop: 4,
          }}
        >
          {error}
        </p>
      )}
    </form>
  );
}

function RegionSelect({ value, onChange }) {
  return (
    <div>
      <label
        style={{
          display: "block",
          fontFamily: T.fB,
          fontSize: 12,
          fontWeight: 500,
          color: T.tx2,
          letterSpacing: 0.3,
          marginBottom: 6,
        }}
      >
        Región
      </label>
      <div
        style={{
          background: T.s3,
          border: `1px solid ${T.bd}`,
          borderRadius: T.r,
          padding: "10px 13px",
          display: "flex",
          alignItems: "center",
        }}
      >
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          style={{
            flex: 1,
            background: "transparent",
            color: T.tx,
            border: "none",
            outline: "none",
            fontFamily: T.fM,
            fontSize: 12,
            letterSpacing: 0.5,
            cursor: "pointer",
          }}
        >
          {PLATFORMS.map((p) => (
            <option key={p} value={p} style={{ background: T.s2 }}>
              {p}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

function LinkedLoL({ linkedGame, onUpdated, readOnly = false }) {
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function onUnlink() {
    setError(null);
    setSubmitting(true);
    try {
      await profileApi.unlinkLoL();
      await onUpdated?.();
    } catch (err) {
      if (err?.status === 409) {
        setError(err?.detail ?? "No puedes desvincular mientras participes en un torneo activo del juego.");
      } else {
        setError("No se pudo desvincular la cuenta.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card hoverable={false} accent>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, minWidth: 0 }}>
          <SummonerIcon
            url={linkedGame.profile_icon_url}
            level={linkedGame.summoner_level}
            unavailable={linkedGame.summoner_unavailable}
          />
          <div style={{ minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, flexWrap: "wrap" }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>League of Legends</span>
              <Tag variant="ac">vinculado</Tag>
            </div>
            <div
              style={{
                fontFamily: T.fM,
                fontSize: 12,
                color: T.tx2,
                letterSpacing: 0.4,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {linkedGame.game_name}
              <span style={{ color: T.tx3 }}>#{linkedGame.tag_line}</span>
              <span style={{ color: T.tx3, marginLeft: 8 }}>· {linkedGame.region}</span>
            </div>
            {linkedGame.summoner_level != null && (
              <div
                style={{
                  fontFamily: T.fM,
                  fontSize: 10,
                  color: T.tx3,
                  letterSpacing: 1,
                  textTransform: "uppercase",
                  marginTop: 4,
                }}
              >
                Nivel {linkedGame.summoner_level}
              </div>
            )}
          </div>
        </div>
        {!readOnly && (
          <Btn variant="ghost" size="sm" onClick={onUnlink} disabled={submitting}>
            <Icon name="x" size={12} />
            Desvincular
          </Btn>
        )}
      </div>
      {error && !readOnly && (
        <p
          role="alert"
          style={{
            fontSize: 12,
            color: T.ac,
            marginTop: 12,
          }}
        >
          {error}
        </p>
      )}
      <MasteryList
        masteries={linkedGame.masteries ?? []}
        unavailable={linkedGame.masteries_unavailable}
      />
    </Card>
  );
}

function SummonerIcon({ url, level, unavailable }) {
  const size = 56;
  const baseStyle = {
    width: size,
    height: size,
    borderRadius: "50%",
    border: `2px solid ${T.ac}`,
    background: T.acD,
    flexShrink: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: T.ac,
    overflow: "hidden",
  };
  if (url && !unavailable) {
    return (
      <div style={baseStyle}>
        <img
          src={url}
          alt={level != null ? `Nivel ${level}` : "Icono de invocador"}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>
    );
  }
  return (
    <div style={baseStyle}>
      <Icon name="trophy" size={22} />
    </div>
  );
}

function MasteryList({ masteries, unavailable }) {
  if (unavailable) {
    return (
      <p style={{ marginTop: 16, fontSize: 12, color: T.tx3 }}>
        Maestrías no disponibles ahora mismo.
      </p>
    );
  }
  if (!masteries.length) {
    return (
      <p style={{ marginTop: 16, fontSize: 12, color: T.tx3 }}>
        Aún no hay maestrías para esta cuenta.
      </p>
    );
  }
  return (
    <div style={{ marginTop: 18 }}>
      <div
        style={{
          fontFamily: T.fM,
          fontSize: 10,
          color: T.tx3,
          letterSpacing: 1,
          textTransform: "uppercase",
          marginBottom: 10,
        }}
      >
        Maestrías
      </div>
      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: 8,
        }}
      >
        {masteries.map((m) => (
          <li
            key={m.champion_id}
            style={{
              background: T.s3,
              border: `1px solid ${T.bd}`,
              borderRadius: T.r,
              padding: "10px 12px",
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            {m.image_url ? (
              <img
                src={m.image_url}
                alt={m.champion_name}
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: T.r2,
                  objectFit: "cover",
                  flexShrink: 0,
                  border: `1px solid ${T.bd}`,
                }}
              />
            ) : (
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: T.r2,
                  background: T.acD,
                  flexShrink: 0,
                }}
              />
            )}
            <div style={{ minWidth: 0, flex: 1 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
                title={m.champion_name}
              >
                {m.champion_name}
              </div>
              <div
                style={{
                  fontFamily: T.fM,
                  fontSize: 10,
                  color: T.tx3,
                  letterSpacing: 0.5,
                }}
              >
                {m.champion_points.toLocaleString()} pts
              </div>
            </div>
            <Tag variant="ac">Nv {m.champion_level}</Tag>
          </li>
        ))}
      </ul>
    </div>
  );
}
