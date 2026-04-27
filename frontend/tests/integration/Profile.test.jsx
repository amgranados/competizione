import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import Profile from "../../src/pages/Profile.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { NotificationProvider } from "../../src/context/NotificationContext.jsx";
import { resetMockState, seedUser } from "../mocks/authHandlers.js";
import { resetProfileMockState, seedProfile } from "../mocks/profileHandlers.js";

function renderProfile() {
  return render(
    <AuthProvider>
      <NotificationProvider>
        <MemoryRouter initialEntries={["/profile"]}>
          <Routes>
            <Route path="/profile" element={<Profile />} />
          </Routes>
        </MemoryRouter>
      </NotificationProvider>
    </AuthProvider>,
  );
}

const baseProfile = {
  id: "00000000-0000-0000-0000-000000000001",
  nickname: "alice",
  email: "alice@example.com",
  avatar_url: null,
  linked_games: [],
  lol_stats: null,
};

describe("Profile page (foundational)", () => {
  beforeEach(() => {
    resetMockState();
    resetProfileMockState();
    seedUser({ email: "alice@example.com", password: "hunter2-abc", nickname: "alice", authenticated: true });
  });

  it("renders profile shell with nickname for a user without LoL", async () => {
    seedProfile(baseProfile);

    renderProfile();

    expect(await screen.findByRole("heading", { level: 2, name: "alice" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: /Juegos vinculados/i })).toBeInTheDocument();
    expect(screen.getByText("No vinculado")).toBeInTheDocument();
  });
});

describe("Profile page — US1 edits", () => {
  beforeEach(() => {
    resetMockState();
    resetProfileMockState();
    seedProfile(baseProfile);
    seedUser({ email: "alice@example.com", password: "hunter2-abc", nickname: "alice", authenticated: true });
  });

  it("changes password and shows success", async () => {
    const user = userEvent.setup();
    renderProfile();

    await screen.findByRole("heading", { level: 2, name: "alice" });

    await user.type(screen.getByLabelText("Contraseña actual"), "old-password-1");
    await user.type(screen.getByLabelText("Contraseña nueva"), "NewPassword99");
    await user.click(screen.getByRole("button", { name: "Guardar contraseña" }));

    expect(await screen.findByText("Contraseña actualizada")).toBeInTheDocument();
  });

  it("updates avatar URL and reflects new image", async () => {
    const user = userEvent.setup();
    renderProfile();

    await screen.findByRole("heading", { level: 2, name: "alice" });

    await user.type(screen.getByLabelText("URL del avatar"), "https://cdn.example/me.png");
    await user.click(screen.getByRole("button", { name: "Guardar avatar" }));

    expect(await screen.findByText("Avatar actualizado")).toBeInTheDocument();
    const avatarImg = screen.getByAltText("Avatar");
    expect(avatarImg).toHaveAttribute("src", "https://cdn.example/me.png");
  });
});

describe("Profile page — US2 LoL link/unlink", () => {
  beforeEach(() => {
    resetMockState();
    resetProfileMockState();
    seedUser({ email: "alice@example.com", password: "hunter2-abc", nickname: "alice", authenticated: true });
  });

  it("shows link LoL button when not linked", async () => {
    seedProfile(baseProfile);
    renderProfile();

    expect(await screen.findByRole("button", { name: "Vincular LoL" })).toBeInTheDocument();
  });

  it("links LoL account flow", async () => {
    seedProfile(baseProfile);
    const user = userEvent.setup();
    renderProfile();

    await user.click(await screen.findByRole("button", { name: "Vincular LoL" }));
    await user.type(screen.getByLabelText("Riot ID (game name)"), "Faker");
    await user.type(screen.getByLabelText("Tag line"), "KR1");
    await user.click(screen.getByRole("button", { name: "Vincular" }));

    expect(await screen.findByText("League of Legends")).toBeInTheDocument();
    expect(screen.getByText("vinculado")).toBeInTheDocument();
  });

  it("shows generic error on link failure", async () => {
    seedProfile(baseProfile);
    const user = userEvent.setup();
    renderProfile();

    await user.click(await screen.findByRole("button", { name: "Vincular LoL" }));
    await user.type(screen.getByLabelText("Riot ID (game name)"), "Bad");
    await user.type(screen.getByLabelText("Tag line"), "BAD");
    await user.click(screen.getByRole("button", { name: "Vincular" }));

    expect(
      await screen.findByText("No se pudo vincular la cuenta de Riot. Verifica los datos introducidos.")
    ).toBeInTheDocument();
  });

  it("shows unavailable banner per section when partial Riot failure", async () => {
    seedProfile({
      ...baseProfile,
      linked_games: [{ game: "lol", region: "EUW1", linked_at: new Date().toISOString() }],
      lol_stats: {
        summoner: { unavailable: false, data: { summoner_level: 10, region: "EUW1" } },
        ranked: { unavailable: false, solo_duo: null, flex: null },
        mastery: { unavailable: false, data: [] },
        recent_matches: { unavailable: true, data: null },
      },
    });
    renderProfile();

    expect(await screen.findByText("League of Legends")).toBeInTheDocument();
    expect(screen.getByText("vinculado")).toBeInTheDocument();
    // Unavailable text appears in the recent matches section
    const matchesSection = screen.getByRole("region", { name: "Últimas partidas" });
    expect(matchesSection).toHaveTextContent("No disponible temporalmente");
    // Other sections rendered normally — level number visible
    const summonerSection = screen.getByRole("region", { name: "Invocador" });
    expect(summonerSection).toHaveTextContent("10");
    expect(summonerSection).toHaveTextContent(/EUW1/);
  });

  it("unlinks LoL when no active tournament", async () => {
    seedProfile({
      ...baseProfile,
      linked_games: [{ game: "lol", region: "EUW1", linked_at: new Date().toISOString() }],
      lol_stats: {
        summoner: { unavailable: false, data: { summoner_level: 10, region: "EUW1" } },
        ranked: { unavailable: false, solo_duo: null, flex: null },
        mastery: { unavailable: false, data: [] },
        recent_matches: { unavailable: false, data: [] },
      },
    });
    const user = userEvent.setup();
    renderProfile();

    await user.click(await screen.findByRole("button", { name: "Desvincular" }));

    expect(await screen.findByRole("button", { name: "Vincular LoL" })).toBeInTheDocument();
  });

  it("shows blocking message when unlink rejected by active tournament", async () => {
    seedProfile({
      ...baseProfile,
      has_active_tournament: true,
      linked_games: [{ game: "lol", region: "EUW1", linked_at: new Date().toISOString() }],
      lol_stats: {
        summoner: { unavailable: false, data: { summoner_level: 10, region: "EUW1" } },
        ranked: { unavailable: false, solo_duo: null, flex: null },
        mastery: { unavailable: false, data: [] },
        recent_matches: { unavailable: false, data: [] },
      },
    });
    const user = userEvent.setup();
    renderProfile();

    await user.click(await screen.findByRole("button", { name: "Desvincular" }));

    expect(
      await screen.findByText(/No puedes desvincular mientras participes en un torneo activo/i)
    ).toBeInTheDocument();
  });
});
