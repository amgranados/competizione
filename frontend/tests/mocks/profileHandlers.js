import { http, HttpResponse } from "msw";

const API = "http://localhost:8000";

const state = {
  profile: null,
};

export function resetProfileMockState() {
  state.profile = null;
}

export function seedProfile(profile) {
  state.profile = profile;
}

function defaultProfile() {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    nickname: "alice",
    email: "alice@example.com",
    avatar_url: null,
    linked_games: [],
    lol_stats: null,
  };
}

export const profileHandlers = [
  http.get(`${API}/api/profile`, () => {
    const profile = state.profile ?? defaultProfile();
    return HttpResponse.json(profile);
  }),

  http.patch(`${API}/api/profile/nickname`, async ({ request }) => {
    const body = await request.json();
    const profile = state.profile ?? defaultProfile();
    if (body.nickname === "taken") {
      return HttpResponse.json({ detail: "Nickname no disponible" }, { status: 409 });
    }
    state.profile = { ...profile, nickname: body.nickname };
    return HttpResponse.json(state.profile);
  }),

  http.patch(`${API}/api/profile/password`, async ({ request }) => {
    const body = await request.json();
    if (body.current_password !== "old-password-1") {
      return HttpResponse.json({ detail: "Contraseña actual incorrecta" }, { status: 400 });
    }
    return new HttpResponse(null, { status: 204 });
  }),

  http.patch(`${API}/api/profile/avatar`, async ({ request }) => {
    const body = await request.json();
    const profile = state.profile ?? defaultProfile();
    state.profile = { ...profile, avatar_url: body.avatar_url };
    return HttpResponse.json(state.profile);
  }),

  http.post(`${API}/api/profile/link/lol`, async ({ request }) => {
    const body = await request.json();
    if (body.tag_line === "BAD") {
      return HttpResponse.json(
        { detail: "No se pudo vincular la cuenta de Riot. Verifica los datos introducidos." },
        { status: 400 },
      );
    }
    if (body.tag_line === "DOWN") {
      return HttpResponse.json(
        { detail: "Riot no está disponible temporalmente. Inténtalo de nuevo en unos minutos." },
        { status: 503 },
      );
    }
    const profile = state.profile ?? defaultProfile();
    const linked = { game: "lol", region: body.region, linked_at: new Date().toISOString() };
    state.profile = { ...profile, linked_games: [linked] };
    return HttpResponse.json(linked, { status: 201 });
  }),

  http.delete(`${API}/api/profile/link/lol`, () => {
    const profile = state.profile ?? defaultProfile();
    if (profile.has_active_tournament) {
      return HttpResponse.json(
        { detail: "No puedes desvincular mientras participes en un torneo activo del juego." },
        { status: 409 },
      );
    }
    state.profile = { ...profile, linked_games: [] };
    return new HttpResponse(null, { status: 204 });
  }),

  http.delete(`${API}/api/profile/me`, async ({ request }) => {
    const body = await request.json();
    const profile = state.profile ?? defaultProfile();
    if (body.confirmation !== profile.nickname) {
      return HttpResponse.json({ detail: "La confirmación no coincide con tu nickname" }, { status: 400 });
    }
    if (profile.has_active_tournament) {
      return HttpResponse.json(
        { detail: "Tienes torneos activos en curso. Espera a que terminen o abandónalos." },
        { status: 409 },
      );
    }
    return new HttpResponse(null, { status: 204 });
  }),
];
