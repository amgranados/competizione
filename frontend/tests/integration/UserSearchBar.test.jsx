import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import UserSearchBar from "../../src/components/UserSearchBar.jsx";
import {
  resetFriendsMockState,
  seedSearchUsers,
} from "../mocks/friendsHandlers.js";

function renderBar() {
  return render(
    <MemoryRouter>
      <UserSearchBar />
    </MemoryRouter>,
  );
}

describe("UserSearchBar", () => {
  beforeEach(() => {
    resetFriendsMockState();
  });

  it("shows empty state when input is blank", () => {
    renderBar();
    expect(
      screen.queryByLabelText("Resultados de búsqueda"),
    ).not.toBeInTheDocument();
  });

  it("shows results dropdown for non-empty query", async () => {
    seedSearchUsers([
      {
        id: "00000000-0000-0000-0000-000000000aaa",
        nickname: "bob",
        avatar_url: null,
        relationship_status: "SIN_RELACION",
        pending_request_id: null,
      },
      {
        id: "00000000-0000-0000-0000-000000000bbb",
        nickname: "bobby",
        avatar_url: null,
        relationship_status: "SIN_RELACION",
        pending_request_id: null,
      },
    ]);
    const user = userEvent.setup();
    renderBar();

    const input = screen.getByLabelText("Buscar usuarios");
    await user.type(input, "bob");

    expect(await screen.findByText("bob")).toBeInTheDocument();
    expect(screen.getByText("bobby")).toBeInTheDocument();
    // Both rows have an "Añadir amigo" button.
    const buttons = await screen.findAllByRole("button", { name: /añadir amigo/i });
    expect(buttons).toHaveLength(2);
  });

  it("shows empty state when api returns []", async () => {
    seedSearchUsers([]);
    const user = userEvent.setup();
    renderBar();

    const input = screen.getByLabelText("Buscar usuarios");
    await user.type(input, "zzz");

    expect(await screen.findByText("No hay resultados")).toBeInTheDocument();
  });

  it("sends a friend request when clicking Añadir amigo", async () => {
    seedSearchUsers([
      {
        id: "tgt-123",
        nickname: "bob",
        avatar_url: null,
        relationship_status: "SIN_RELACION",
        pending_request_id: null,
      },
    ]);
    const user = userEvent.setup();
    renderBar();

    await user.type(screen.getByLabelText("Buscar usuarios"), "bob");
    const sendBtn = await screen.findByRole("button", { name: /añadir amigo/i });
    await user.click(sendBtn);

    // After refetch the row should now show "Pendiente".
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /pendiente/i }),
      ).toBeInTheDocument(),
    );
  });
});
