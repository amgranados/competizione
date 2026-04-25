import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import MatchDetail from "../../src/pages/MatchDetail.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { NotificationProvider } from "../../src/context/NotificationContext.jsx";
import { resetMockState, seedUser } from "../mocks/authHandlers.js";
import { resetTournamentState, seedTournament } from "../mocks/tournamentHandlers.js";
import { resetMatchState, seedMatchStandalone } from "../mocks/matchHandlers.js";

function renderMatchDetail(matchId) {
  return render(
    <MemoryRouter initialEntries={[`/matches/${matchId}`]}>
      <AuthProvider>
        <NotificationProvider intervalMs={999999}>
          <Routes>
            <Route path="/matches/:id" element={<MatchDetail />} />
            <Route path="/tournaments/:tournamentId" element={<div>Torneo</div>} />
          </Routes>
        </NotificationProvider>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("MatchDetail", () => {
  beforeEach(() => {
    resetMockState();
    resetTournamentState();
    resetMatchState();
  });

  it("shows the organizer the button to register a manual result", async () => {
    seedUser({
      email: "org@example.com",
      password: "pw",
      nickname: "Org",
      authenticated: true,
    });
    const me = await (await fetch("http://localhost:8000/auth/me")).json();
    seedTournament({
      id: "t-1",
      name: "T",
      format: "single_elim",
      state: "active",
      organizer_id: me.id,
      participants: [],
    });
    seedMatchStandalone({
      id: "m-1",
      tournament_id: "t-1",
      round_number: 1,
      player1_id: "p1",
      player2_id: "p2",
      is_bye: false,
      state: "pending",
      tournament_code: "CODE-XYZ",
    });

    renderMatchDetail("m-1");
    await waitFor(() => {
      expect(screen.getByText(/CODE-XYZ/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Gana jugador 1/i })).toBeInTheDocument();
  });

  it("hides the register button when the viewer is not the organizer", async () => {
    seedUser({
      email: "player@example.com",
      password: "pw",
      nickname: "Player",
      authenticated: true,
    });
    seedTournament({
      id: "t-2",
      name: "T",
      format: "single_elim",
      state: "active",
      organizer_id: "someone-else",
      participants: [],
    });
    seedMatchStandalone({
      id: "m-2",
      tournament_id: "t-2",
      round_number: 1,
      player1_id: "p1",
      player2_id: "p2",
      is_bye: false,
      state: "pending",
    });

    renderMatchDetail("m-2");
    await waitFor(() => {
      expect(screen.getByText(/Enfrentamiento/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /Gana jugador 1/i })).toBeNull();
  });

  it("registers a manual result and shows the permanent manual tag", async () => {
    seedUser({
      email: "org@example.com",
      password: "pw",
      nickname: "Org",
      authenticated: true,
    });
    const me = await (await fetch("http://localhost:8000/auth/me")).json();
    seedTournament({
      id: "t-3",
      name: "T",
      format: "single_elim",
      state: "active",
      organizer_id: me.id,
      participants: [],
    });
    seedMatchStandalone({
      id: "m-3",
      tournament_id: "t-3",
      round_number: 1,
      player1_id: "p1",
      player2_id: "p2",
      is_bye: false,
      state: "pending",
    });

    const user = userEvent.setup();
    renderMatchDetail("m-3");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Gana jugador 1/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /Gana jugador 1/i }));
    await waitFor(() => {
      expect(screen.getByText(/Introducido manualmente/i)).toBeInTheDocument();
    });
  });
});
