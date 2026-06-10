import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import Tournaments from "../../src/pages/Tournaments.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { NotificationProvider } from "../../src/context/NotificationContext.jsx";
import { resetMockState, seedUser } from "../mocks/authHandlers.js";
import {
  resetTournamentState,
  seedTournament,
  seedInvitation,
} from "../mocks/tournamentHandlers.js";

function renderTournaments() {
  return render(
    <MemoryRouter initialEntries={["/tournaments"]}>
      <AuthProvider>
        <NotificationProvider intervalMs={999999}>
          <Routes>
            <Route path="/tournaments" element={<Tournaments />} />
            <Route path="/tournaments/:tournamentId" element={<div>Torneo detail</div>} />
            <Route path="/users/:nickname" element={<div>Perfil de usuario</div>} />
          </Routes>
        </NotificationProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("Tournaments", () => {
  beforeEach(() => {
    resetMockState();
    resetTournamentState();
    seedUser({ email: "org@example.com", password: "pw", nickname: "Org", authenticated: true });
  });

  it("lists my tournaments with state, format and players count", async () => {
    seedTournament({
      id: "t1",
      name: "Summer League",
      state: "active",
      format: "round_robin",
      participants: [{ id: "p1" }, { id: "p2" }],
    });
    seedTournament({
      id: "t2",
      name: "Winter Cup",
      state: "open",
      format: "single_elim",
      participants: [{ id: "p3" }],
    });
    renderTournaments();

    await waitFor(() => expect(screen.getByText("Summer League")).toBeInTheDocument());
    expect(screen.getByText("Winter Cup")).toBeInTheDocument();
    expect(screen.getByText("En curso")).toBeInTheDocument();
    expect(screen.getByText("Próximo")).toBeInTheDocument();
    expect(screen.getByText(/2 jugadores/)).toBeInTheDocument();
    expect(screen.getByText(/1 jugador$/)).toBeInTheDocument();
  });

  it("shows an empty state when there are no tournaments", async () => {
    renderTournaments();
    await waitFor(() =>
      expect(screen.getByText(/No tienes torneos todavía/i)).toBeInTheDocument(),
    );
  });

  it("renders pending invitations and removes them after accepting", async () => {
    seedInvitation({ id: "inv1", tournament_id: "abcdef12-0000-0000-0000-000000000000" });
    const user = userEvent.setup();
    renderTournaments();

    await waitFor(() =>
      expect(screen.getByText(/Invitaciones pendientes/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: /Aceptar/i }));
    await waitFor(() =>
      expect(screen.queryByText(/Invitaciones pendientes/i)).not.toBeInTheDocument(),
    );
  });

  it("removes a pending invitation after rejecting it", async () => {
    seedInvitation({ id: "inv2", tournament_id: "abcdef12-0000-0000-0000-000000000000" });
    const user = userEvent.setup();
    renderTournaments();

    await waitFor(() =>
      expect(screen.getByText(/Invitaciones pendientes/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: /Rechazar/i }));
    await waitFor(() =>
      expect(screen.queryByText(/Invitaciones pendientes/i)).not.toBeInTheDocument(),
    );
  });

  it("creates a tournament and navigates to its detail page", async () => {
    const user = userEvent.setup();
    renderTournaments();

    await waitFor(() => expect(screen.getByText(/Crear torneo/i)).toBeInTheDocument());
    await user.type(screen.getByLabelText(/Nombre/i), "Mi torneo");
    await user.selectOptions(screen.getByLabelText(/Formato/i), "single_elim");
    await user.click(screen.getByRole("button", { name: /Crear/i }));

    await waitFor(() => expect(screen.getByText("Torneo detail")).toBeInTheDocument());
  });
});
