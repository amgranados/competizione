import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import TournamentDetail from "../../src/pages/TournamentDetail.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { NotificationProvider } from "../../src/context/NotificationContext.jsx";
import { resetMockState, seedUser } from "../mocks/authHandlers.js";
import {
  resetTournamentState,
  seedTournament,
  seedMatch,
} from "../mocks/tournamentHandlers.js";

function renderDetail(tournamentId) {
  return render(
    <MemoryRouter initialEntries={[`/tournaments/${tournamentId}`]}>
      <AuthProvider>
        <NotificationProvider intervalMs={999999}>
          <Routes>
            <Route path="/tournaments/:tournamentId" element={<TournamentDetail />} />
            <Route path="/dashboard" element={<div>dashboard</div>} />
            <Route path="/matches/:id" element={<div>match detail</div>} />
          </Routes>
        </NotificationProvider>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("TournamentDetail", () => {
  beforeEach(() => {
    resetMockState();
    resetTournamentState();
  });

  it("shows organizer actions when user is the organizer of a draft tournament", async () => {
    seedUser({
      email: "org@example.com",
      password: "pw",
      nickname: "Org",
      authenticated: true,
    });
    const me = await (await fetch("http://localhost:8000/auth/me")).json();
    seedTournament({
      id: "t-1",
      name: "Organizado",
      format: "round_robin",
      state: "draft",
      organizer_id: me.id,
      participants: [],
    });

    renderDetail("t-1");
    await waitFor(() => {
      expect(screen.getByText(/Organizado/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Abrir inscripciones/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Invitar/i })).toBeInTheDocument();
  });

  it("hides management controls when the user is not the organizer", async () => {
    seedUser({
      email: "spectator@example.com",
      password: "pw",
      nickname: "Spec",
      authenticated: true,
    });
    seedTournament({
      id: "t-2",
      name: "Ajeno",
      format: "round_robin",
      state: "open",
      organizer_id: "someone-else",
      participants: [],
    });

    renderDetail("t-2");
    await waitFor(() => {
      expect(screen.getByText(/Ajeno/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /Iniciar torneo/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Abrir inscripciones/i })).toBeNull();
  });

  it("renders the schedule with player names and a visible link to the match", async () => {
    seedUser({
      email: "player@example.com",
      password: "pw",
      nickname: "Player",
      authenticated: true,
    });
    seedTournament({
      id: "t-3",
      name: "Activo",
      format: "round_robin",
      state: "active",
      organizer_id: "somebody",
      participants: [
        { id: "p1", user_id: "u1", nickname: "Alice", accepted_at: "2026-06-01T10:00:00Z" },
        { id: "p2", user_id: "u2", nickname: "Bob", accepted_at: "2026-06-01T11:00:00Z" },
      ],
    });
    seedMatch({
      id: "m-1",
      tournament_id: "t-3",
      round_number: 1,
      player1_id: "p1",
      player2_id: "p2",
      is_bye: false,
      state: "pending",
    });

    renderDetail("t-3");
    await waitFor(() => {
      expect(screen.getByText(/Ronda 1/i)).toBeInTheDocument();
    });
    // The match row shows both nicknames, the VS separator and the call to action.
    const row = screen.getByRole("link", { name: /Ver partida Alice contra Bob/i });
    expect(row).toHaveAttribute("href", "/matches/m-1");
    expect(screen.getByText("VS")).toBeInTheDocument();
    expect(screen.getByText(/Ver partida/i)).toBeInTheDocument();
  });

  it("shows an access error instead of loading forever when the tournament 404s", async () => {
    seedUser({
      email: "outsider@example.com",
      password: "pw",
      nickname: "Out",
      authenticated: true,
    });
    // Nothing seeded: GET /tournaments/unknown responds 404, like the backend
    // does for tournaments the user can't see.
    renderDetail("unknown");
    await waitFor(() => {
      expect(screen.getByText(/Torneo no disponible/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/No tienes acceso/i);
    expect(screen.queryByText(/Cargando torneo/i)).toBeNull();
  });

  it("lets the organizer join their own tournament with the Participar button", async () => {
    seedUser({
      email: "org@example.com",
      password: "pw",
      nickname: "Org",
      authenticated: true,
    });
    const me = await (await fetch("http://localhost:8000/auth/me")).json();
    seedTournament({
      id: "t-4",
      name: "Conmigo",
      format: "round_robin",
      state: "draft",
      organizer_id: me.id,
      participants: [],
    });

    const user = userEvent.setup();
    renderDetail("t-4");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Participar/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /Participar/i }));

    // The organizer now appears among the participants and the button is gone.
    await waitFor(() => {
      expect(screen.getByText(/Participantes \(1\)/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /Participar/i })).toBeNull();
  });
});
