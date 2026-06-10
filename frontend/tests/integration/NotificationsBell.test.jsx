import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import Dashboard from "../../src/pages/Dashboard.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { NotificationProvider } from "../../src/context/NotificationContext.jsx";
import { resetMockState, seedUser } from "../mocks/authHandlers.js";
import { resetDashboardState } from "../mocks/dashboardHandlers.js";
import { resetTournamentState, pushNotification } from "../mocks/tournamentHandlers.js";
import { resetFriendsMockState, seedReceivedRequests } from "../mocks/friendsHandlers.js";

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <AuthProvider>
        <NotificationProvider intervalMs={999999}>
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/tournaments" element={<div>Catálogo de torneos</div>} />
            <Route path="/tournaments/:tournamentId" element={<div>Torneo detail</div>} />
            <Route path="/users/:nickname" element={<div>Perfil de usuario</div>} />
          </Routes>
        </NotificationProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("NotificationsBell", () => {
  beforeEach(() => {
    resetMockState();
    resetDashboardState();
    resetTournamentState();
    resetFriendsMockState();
    seedUser({ email: "org@example.com", password: "pw", nickname: "Org", authenticated: true });
  });

  it("opens the panel on click and navigates to the tournament when clicking a notification", async () => {
    pushNotification({ id: "n1", user_id: "u1", type: "tournament_started", tournament_id: "t1" });
    const user = userEvent.setup();
    renderDashboard();

    await waitFor(() =>
      expect(screen.getByLabelText(/1 notificaciones sin leer/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Notificaciones" }));
    expect(screen.getByText("Un torneo ha comenzado")).toBeInTheDocument();

    await user.click(screen.getByText("Un torneo ha comenzado"));
    await waitFor(() => expect(screen.getByText("Torneo detail")).toBeInTheDocument());
  });

  it("clears the unread badge with 'Marcar todas como leídas'", async () => {
    pushNotification({ id: "n1", user_id: "u1", type: "friend_request_received" });
    pushNotification({ id: "n2", user_id: "u1", type: "match_generated", match_id: "m1" });
    const user = userEvent.setup();
    renderDashboard();

    await waitFor(() =>
      expect(screen.getByLabelText(/2 notificaciones sin leer/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Notificaciones" }));
    await user.click(screen.getByRole("button", { name: /Marcar todas como leídas/i }));

    await waitFor(() =>
      expect(screen.queryByLabelText(/notificaciones sin leer/i)).not.toBeInTheDocument(),
    );
    // Items remain listed, now as read.
    expect(screen.getByText("Has recibido una solicitud de amistad")).toBeInTheDocument();
  });

  it("shows an empty message when there are no notifications", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await waitFor(() => expect(screen.getByText("Hola, Org")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Notificaciones" }));
    expect(screen.getByText(/No tienes notificaciones/i)).toBeInTheDocument();
  });
});

describe("Dashboard friend requests", () => {
  beforeEach(() => {
    resetMockState();
    resetDashboardState();
    resetTournamentState();
    resetFriendsMockState();
    seedUser({ email: "org@example.com", password: "pw", nickname: "Org", authenticated: true });
  });

  it("lists pending friend requests and removes them after accepting", async () => {
    seedReceivedRequests([
      { id: "req1", requester_nickname: "playerB", created_at: new Date().toISOString() },
    ]);
    const user = userEvent.setup();
    renderDashboard();

    await waitFor(() =>
      expect(screen.getByText(/Solicitudes de amistad/i)).toBeInTheDocument(),
    );
    expect(screen.getByText("playerB")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Aceptar/i }));
    await waitFor(() =>
      expect(screen.queryByText(/Solicitudes de amistad/i)).not.toBeInTheDocument(),
    );
  });

  it("removes a request after rejecting it", async () => {
    seedReceivedRequests([
      { id: "req2", requester_nickname: "playerC", created_at: new Date().toISOString() },
    ]);
    const user = userEvent.setup();
    renderDashboard();

    await waitFor(() => expect(screen.getByText("playerC")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /Rechazar/i }));
    await waitFor(() => expect(screen.queryByText("playerC")).not.toBeInTheDocument());
  });
});
