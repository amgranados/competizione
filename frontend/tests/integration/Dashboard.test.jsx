import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import Dashboard from "../../src/pages/Dashboard.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { NotificationProvider } from "../../src/context/NotificationContext.jsx";
import { resetMockState, seedUser } from "../mocks/authHandlers.js";
import {
  resetTournamentState,
  seedTournament,
  seedInvitation,
} from "../mocks/tournamentHandlers.js";

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <AuthProvider>
        <NotificationProvider intervalMs={999999}>
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/tournaments/:tournamentId" element={<div>Torneo detail</div>} />
          </Routes>
        </NotificationProvider>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("Dashboard", () => {
  beforeEach(() => {
    resetMockState();
    resetTournamentState();
    seedUser({ email: "org@example.com", password: "pw", nickname: "Org", authenticated: true });
  });

  it("shows empty states and a create form", async () => {
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/No tienes torneos todavía/i)).toBeInTheDocument(),
    );
    // No invitations section is rendered when there are no pending invitations.
    expect(screen.queryByText(/Invitaciones pendientes/i)).toBeNull();
    expect(screen.getByRole("button", { name: /Crear/i })).toBeInTheDocument();
  });

  it("creates a tournament and navigates to its detail", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByRole("heading", { level: 2, name: /Crear torneo/i })).toBeInTheDocument(),
    );

    await user.type(screen.getByLabelText(/Nombre/i), "Mi Torneo");
    await user.click(screen.getByRole("button", { name: /Crear/i }));

    await waitFor(() => {
      expect(screen.getByText(/Torneo detail/i)).toBeInTheDocument();
    });
  });

  it("lists existing tournaments", async () => {
    seedTournament({
      id: "t1",
      name: "Ya existe",
      format: "round_robin",
      state: "draft",
      organizer_id: "someone",
    });
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText(/Ya existe/i)).toBeInTheDocument();
    });
  });

  it("lists pending invitations and accepts one", async () => {
    seedInvitation({
      id: "inv-1",
      tournament_id: "t1",
      invited_user_id: "me",
      inviter_user_id: "other",
      state: "pending",
    });
    const user = userEvent.setup();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText(/Invitaciones pendientes/i)).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /Aceptar/i }));
    await waitFor(() => {
      expect(screen.queryByText(/Invitaciones pendientes/i)).toBeNull();
    });
  });
});
