import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import Dashboard from "../../src/pages/Dashboard.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { NotificationProvider } from "../../src/context/NotificationContext.jsx";
import { resetMockState, seedUser } from "../mocks/authHandlers.js";
import { resetDashboardState, seedDashboard } from "../mocks/dashboardHandlers.js";

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <AuthProvider>
        <NotificationProvider intervalMs={999999}>
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/tournaments" element={<div>Todos los torneos</div>} />
            <Route path="/tournaments/:tournamentId" element={<div>Torneo detail</div>} />
            <Route path="/users/:nickname" element={<div>Perfil de usuario</div>} />
          </Routes>
        </NotificationProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("Dashboard", () => {
  beforeEach(() => {
    resetMockState();
    resetDashboardState();
    seedUser({ email: "org@example.com", password: "pw", nickname: "Org", authenticated: true });
  });

  it("shows a personalized greeting and the fixed subtitle", async () => {
    seedDashboard({ greeting: "Hola, Org", subtitle: "Tu centro de operaciones competitivo" });
    renderDashboard();
    await waitFor(() => expect(screen.getByText("Hola, Org")).toBeInTheDocument());
    expect(screen.getByText("Tu centro de operaciones competitivo")).toBeInTheDocument();
  });

  it("renders the four stat cards with the mock values", async () => {
    seedDashboard({
      stats: {
        active_tournaments: { count: 3, weekly_delta: 1 },
        total_wins: { wins: 12, games_played: 20, winrate: 60.0 },
        best_streak: { best: 5, tournament_id: "t9", tournament_name: "Spring Cup" },
        friends_count: 7,
      },
    });
    renderDashboard();

    await waitFor(() => expect(screen.getByText(/Torneos activos/i)).toBeInTheDocument());
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("+1")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("lists my tournaments and 'Ver todos' navigates to the Tournaments section", async () => {
    seedDashboard({
      my_tournaments: [
        {
          id: "t1",
          name: "Summer League",
          state: "in_progress",
          format: "round_robin",
          players_count: 16,
          current_round: 3,
          start_at: null,
        },
      ],
    });
    const user = userEvent.setup();
    renderDashboard();

    await waitFor(() => expect(screen.getByText("Summer League")).toBeInTheDocument());

    await user.click(screen.getByRole("link", { name: /Ver todos/i }));
    await waitFor(() => expect(screen.getByText("Todos los torneos")).toBeInTheDocument());
  });

  it("renders the activity feed with links to actor and tournament", async () => {
    seedDashboard({
      activity: [
        {
          id: "a1",
          event_type: "MATCH_WIN",
          created_at: new Date().toISOString(),
          actor: { id: "u2", nickname: "playerB", avatar_url: null, exists: true },
          tournament: { id: "t1", name: "Spring Cup" },
        },
      ],
    });
    renderDashboard();

    await waitFor(() => expect(screen.getByText("playerB")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /playerB/i })).toHaveAttribute("href", "/users/playerB");
    expect(screen.getByRole("link", { name: /Spring Cup/i })).toHaveAttribute(
      "href",
      "/tournaments/t1",
    );
  });

  it("shows informative empty states without errors when there is no data", async () => {
    // default seed: empty my_tournaments and activity.
    renderDashboard();
    await waitFor(() => expect(screen.getByText("Hola, Org")).toBeInTheDocument());
    expect(screen.getByText(/no tienes torneos|sin torneos/i)).toBeInTheDocument();
    expect(screen.getByText(/sin actividad|no hay actividad/i)).toBeInTheDocument();
  });
});
