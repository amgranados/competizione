import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FriendshipButton from "../../src/components/FriendshipButton.jsx";

describe("FriendshipButton", () => {
  it("renders Añadir amigo for SIN_RELACION", () => {
    render(<FriendshipButton status="SIN_RELACION" onSendRequest={vi.fn()} />);
    expect(screen.getByRole("button", { name: /añadir amigo/i })).toBeEnabled();
  });

  it("renders Pendiente clickable for PENDIENTE_ENVIADA (cancels request)", async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(<FriendshipButton status="PENDIENTE_ENVIADA" onCancel={onCancel} />);
    const btn = screen.getByRole("button", { name: /pendiente/i });
    expect(btn).toBeEnabled();
    await user.click(btn);
    expect(onCancel).toHaveBeenCalled();
  });

  it("renders Aceptar/Rechazar inline for PENDIENTE_RECIBIDA", () => {
    render(
      <FriendshipButton
        status="PENDIENTE_RECIBIDA"
        onAccept={vi.fn()}
        onReject={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /aceptar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /rechazar/i })).toBeInTheDocument();
  });

  it("renders Eliminar amigo for AMIGO", () => {
    render(<FriendshipButton status="AMIGO" onRemove={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: /eliminar amigo/i }),
    ).toBeInTheDocument();
  });

  it("calls onSendRequest when clicked in SIN_RELACION", async () => {
    const onSendRequest = vi.fn();
    const user = userEvent.setup();
    render(
      <FriendshipButton status="SIN_RELACION" onSendRequest={onSendRequest} />,
    );
    await user.click(screen.getByRole("button", { name: /añadir amigo/i }));
    expect(onSendRequest).toHaveBeenCalled();
  });

  it("calls onAccept when accepting in PENDIENTE_RECIBIDA", async () => {
    const onAccept = vi.fn();
    const onReject = vi.fn();
    const user = userEvent.setup();
    render(
      <FriendshipButton
        status="PENDIENTE_RECIBIDA"
        onAccept={onAccept}
        onReject={onReject}
      />,
    );
    await user.click(screen.getByRole("button", { name: /aceptar/i }));
    expect(onAccept).toHaveBeenCalled();
    expect(onReject).not.toHaveBeenCalled();
  });

  it("calls onRemove when clicked in AMIGO", async () => {
    const onRemove = vi.fn();
    const user = userEvent.setup();
    render(<FriendshipButton status="AMIGO" onRemove={onRemove} />);
    await user.click(screen.getByRole("button", { name: /eliminar amigo/i }));
    expect(onRemove).toHaveBeenCalled();
  });
});
