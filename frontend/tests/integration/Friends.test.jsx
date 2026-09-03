import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import Friends from "../../src/pages/Friends.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { NotificationProvider } from "../../src/context/NotificationContext.jsx";
import { resetMockState, seedUser } from "../mocks/authHandlers.js";
import { resetTournamentState } from "../mocks/tournamentHandlers.js";
import {
  resetFriendsMockState,
  seedFriends,
  seedReceivedRequests,
} from "../mocks/friendsHandlers.js";

function renderFriends() {
  return render(
    <MemoryRouter initialEntries={["/friends"]}>
      <AuthProvider>
        <NotificationProvider intervalMs={999999}>
          <Routes>
            <Route path="/friends" element={<Friends />} />
            <Route path="/users/:nickname" element={<div>Perfil de usuario</div>} />
          </Routes>
        </NotificationProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("Friends", () => {
  beforeEach(() => {
    resetMockState();
    resetTournamentState();
    resetFriendsMockState();
    seedUser({ email: "org@example.com", password: "pw", nickname: "Org", authenticated: true });
  });

  it("lists my friends with a link to their profile", async () => {
    seedFriends([
      { id: "u1", nickname: "playerB", avatar_url: null, relationship_status: "AMIGO" },
      { id: "u2", nickname: "playerC", avatar_url: null, relationship_status: "AMIGO" },
    ]);
    renderFriends();

    await waitFor(() => expect(screen.getByText("playerB")).toBeInTheDocument());
    expect(screen.getByText("playerC")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /playerB/i })).toHaveAttribute(
      "href",
      "/users/playerB",
    );
  });

  it("shows an empty state when there are no friends", async () => {
    renderFriends();
    await waitFor(() =>
      expect(screen.getByText(/Aún no tienes amigos/i)).toBeInTheDocument(),
    );
  });

  it("removes a friend from the list", async () => {
    seedFriends([
      { id: "u1", nickname: "playerB", avatar_url: null, relationship_status: "AMIGO" },
    ]);
    const user = userEvent.setup();
    renderFriends();

    await waitFor(() => expect(screen.getByText("playerB")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /Eliminar a playerB/i }));
    await waitFor(() =>
      expect(screen.getByText(/Aún no tienes amigos/i)).toBeInTheDocument(),
    );
  });

  it("accepting a received request moves the requester to the friends list", async () => {
    seedReceivedRequests([
      {
        id: "req1",
        requester_id: "u9",
        requester_nickname: "playerD",
        created_at: new Date().toISOString(),
      },
    ]);
    const user = userEvent.setup();
    renderFriends();

    await waitFor(() =>
      expect(screen.getByText(/Solicitudes recibidas/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: /Aceptar/i }));

    await waitFor(() =>
      expect(screen.queryByText(/Solicitudes recibidas/i)).not.toBeInTheDocument(),
    );
    expect(screen.getByText("playerD")).toBeInTheDocument();
  });

  it("rejecting a received request removes it without adding a friend", async () => {
    seedReceivedRequests([
      {
        id: "req2",
        requester_id: "u8",
        requester_nickname: "playerE",
        created_at: new Date().toISOString(),
      },
    ]);
    const user = userEvent.setup();
    renderFriends();

    await waitFor(() => expect(screen.getByText("playerE")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /Rechazar/i }));
    await waitFor(() => expect(screen.queryByText("playerE")).not.toBeInTheDocument());
    expect(screen.getByText(/Aún no tienes amigos/i)).toBeInTheDocument();
  });
});
