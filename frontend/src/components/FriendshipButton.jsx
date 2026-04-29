import Btn from "./ui/Btn.jsx";
import Icon from "./ui/Icon.jsx";

/**
 * Renders the relationship button next to a user listing or profile.
 *
 * Status drives the rendered text and the active handler (HD-1):
 * - SIN_RELACION       -> "Añadir amigo"   (onSendRequest)
 * - PENDIENTE_ENVIADA  -> "Pendiente"      (disabled)
 * - PENDIENTE_RECIBIDA -> "Aceptar" + "Rechazar" (onAccept / onReject)
 * - AMIGO              -> "Eliminar amigo" (onRemove)
 */
export default function FriendshipButton({
  status,
  onSendRequest,
  onAccept,
  onReject,
  onCancel,
  onRemove,
  size = "sm",
}) {
  const baseStyle = { fontSize: 12 };

  if (status === "PENDIENTE_ENVIADA") {
    return (
      <Btn
        variant="ghost"
        onClick={onCancel}
        aria-label="Pendiente — pulsa para cancelar"
        title="Pulsa para cancelar la solicitud"
        style={baseStyle}
      >
        <Icon name="x" size={12} />
        Pendiente
      </Btn>
    );
  }

  if (status === "PENDIENTE_RECIBIDA") {
    return (
      <span style={{ display: "inline-flex", gap: 6 }}>
        <Btn variant="primary" onClick={onAccept} style={baseStyle}>
          Aceptar
        </Btn>
        <Btn variant="ghost" onClick={onReject} style={baseStyle}>
          Rechazar
        </Btn>
      </span>
    );
  }

  if (status === "AMIGO") {
    return (
      <Btn variant="ghost" onClick={onRemove} style={baseStyle}>
        <Icon name="trash" size={12} />
        Eliminar amigo
      </Btn>
    );
  }

  // SIN_RELACION (default)
  return (
    <Btn variant="primary" onClick={onSendRequest} style={baseStyle}>
      <Icon name="user" size={12} />
      Añadir amigo
    </Btn>
  );
}
