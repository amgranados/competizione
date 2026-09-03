import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import UserProfile from "../../src/pages/UserProfile.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { NotificationProvider } from "../../src/context/NotificationContext.jsx";
import {
  resetFriendsMockState,
  seedPublicProfile,
} from "../mocks/friendsHandlers.js";
import { resetMockState, seedUser } from "../mocks/authHandlers.js";

function renderUserProfile(nickname) {
  return render(
    <AuthProvider>
      <NotificationProvider>
        <MemoryRouter initialEntries={[`/users/${nickname}`]}>
          <Routes>
            <Route path="/users/:nickname" element={<UserProfile />} />
          </Routes>
        </MemoryRouter>
      </NotificationProvider>
    </AuthProvider>,
  );
}

const bob = {
  id: "00000000-0000-0000-0000-000000000bbb",
  nickname: "bob",
  avatar_url: null,
  linked_games: [],
  relationship_status: "SIN_RELACION",
  pending_request_id: null,
};

describe("UserProfile page (US1)", () => {
  beforeEach(() => {
    resetFriendsMockState();
    resetMockState();
    seedUser({
      email: "alice@example.com",
      password: "hunter2-abc",
      nickname: "alice",
      authenticated: true,
    });
  });

  it("renders public profile without edit controls", async () => {
    seedPublicProfile("bob", bob);

    renderUserProfile("bob");

    expect(await screen.findByRole("heading", { level: 2, name: "bob" })).toBeInTheDocument();
    // No edit controls (those live in /profile only).
    expect(screen.queryByRole("button", { name: /editar perfil/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /eliminar cuenta/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /añadir amigo/i })).toBeInTheDocument();
  });

  it("renders 404 page when user not found", async () => {
    renderUserProfile("ghost");

    expect(await screen.findByText(/Usuario no encontrado/i)).toBeInTheDocument();
  });

  it("shows lol stats when target has linked account", async () => {
    seedPublicProfile("bob", {
      ...bob,
      linked_games: [
        {
          game: "lol",
          game_name: "Faker",
          tag_line: "KR1",
          region: "KR",
          summoner_level: 300,
          masteries: [
            {
              champion_id: 1,
              champion_name: "Annie",
              champion_level: 7,
              champion_points: 100000,
            },
          ],
        },
      ],
    });

    renderUserProfile("bob");

    expect(await screen.findByText("Faker")).toBeInTheDocument();
    expect(screen.getByText("#KR1")).toBeInTheDocument();
    expect(screen.getByText("Annie")).toBeInTheDocument();
    expect(screen.getByText(/Nv 7/)).toBeInTheDocument();
  });

  it("shows ranked and match history on another user's profile", async () => {
    seedPublicProfile("bob", {
      ...bob,
      linked_games: [
        {
          game: "lol",
          game_name: "Faker",
          tag_line: "KR1",
          region: "KR",
          summoner_level: 300,
          masteries: [],
          ranked_solo: {
            queue_type: "RANKED_SOLO_5x5",
            tier: "CHALLENGER",
            rank: "I",
            league_points: 1200,
            wins: 300,
            losses: 100,
          },
          ranked_flex: null,
          recent_matches: [
            {
              match_id: "KR_456",
              played_at: "2026-06-02T10:00:00Z",
              duration_seconds: 1500,
              champion_id: 7,
              champion_name: "LeBlanc",
              champion_image_url: "",
              kills: 12,
              deaths: 1,
              assists: 9,
              win: false,
              queue: "CLASSIC",
            },
          ],
        },
      ],
    });

    renderUserProfile("bob");

    const rankedSection = await screen.findByRole("region", { name: "Clasificatoria" });
    expect(rankedSection).toHaveTextContent("CHALLENGER I");
    expect(rankedSection).toHaveTextContent("1200 LP");

    const matchesSection = screen.getByRole("region", { name: "Últimas partidas" });
    expect(matchesSection).toHaveTextContent("LeBlanc");
    expect(matchesSection).toHaveTextContent("Derrota");
    expect(matchesSection).toHaveTextContent("12/1/9");
  });

  it("sends friend request and updates button to Pendiente", async () => {
    seedPublicProfile("bob", bob);
    const user = userEvent.setup();
    renderUserProfile("bob");

    const sendBtn = await screen.findByRole("button", { name: /añadir amigo/i });
    await user.click(sendBtn);

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /pendiente/i }),
      ).toBeInTheDocument(),
    );
  });

  it("removes friend and updates button to Añadir amigo", async () => {
    seedPublicProfile("bob", { ...bob, relationship_status: "AMIGO" });
    const user = userEvent.setup();
    renderUserProfile("bob");

    const removeBtn = await screen.findByRole("button", { name: /eliminar amigo/i });
    await user.click(removeBtn);

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /añadir amigo/i }),
      ).toBeInTheDocument(),
    );
  });

  it("cancels pending request when Pendiente is clicked", async () => {
    seedPublicProfile("bob", {
      ...bob,
      relationship_status: "PENDIENTE_ENVIADA",
      pending_request_id: "req-bob",
    });
    const user = userEvent.setup();
    renderUserProfile("bob");

    const pending = await screen.findByRole("button", { name: /pendiente/i });
    expect(pending).toBeEnabled();
    await user.click(pending);

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /añadir amigo/i }),
      ).toBeInTheDocument(),
    );
  });

  it("accepts an incoming request inline when PENDIENTE_RECIBIDA", async () => {
    seedPublicProfile("bob", {
      ...bob,
      relationship_status: "PENDIENTE_RECIBIDA",
      pending_request_id: "req-bob",
    });
    const user = userEvent.setup();
    renderUserProfile("bob");

    const accept = await screen.findByRole("button", { name: /aceptar/i });
    await user.click(accept);

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /eliminar amigo/i }),
      ).toBeInTheDocument(),
    );
  });
});
