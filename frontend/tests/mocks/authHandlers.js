import { http, HttpResponse } from "msw";

const API = "http://localhost:8000";
const state = {
  users: new Map(),
  currentEmail: null,
};

export function resetMockState() {
  state.users.clear();
  state.currentEmail = null;
}

export function seedUser({ email, password, nickname, authenticated = false }) {
  state.users.set(email, {
    id: crypto.randomUUID(),
    email,
    nickname: nickname ?? `user${Math.floor(10000 + Math.random() * 89999)}`,
    password,
  });
  if (authenticated) {
    state.currentEmail = email;
  }
}

export function setCurrentUser(email) {
  state.currentEmail = email;
}

function makeUser(email, password, nickname) {
  const id = crypto.randomUUID();
  const assigned = nickname ?? `user${Math.floor(10000 + Math.random() * 89999)}`;
  const record = { id, email, nickname: assigned, password };
  state.users.set(email, record);
  return record;
}

export const authHandlers = [
  http.post(`${API}/auth/register`, async ({ request }) => {
    const body = await request.json();
    if (state.users.has(body.email)) {
      return HttpResponse.json({ detail: "El email ya está en uso" }, { status: 409 });
    }
    if (body.nickname && [...state.users.values()].some((u) => u.nickname === body.nickname)) {
      return HttpResponse.json({ detail: "El nickname ya está en uso" }, { status: 409 });
    }
    const user = makeUser(body.email, body.password, body.nickname);
    state.currentEmail = body.email;
    return HttpResponse.json(
      { id: user.id, email: user.email, nickname: user.nickname },
      {
        status: 201,
        headers: {
          "Set-Cookie": "access_token=test; HttpOnly; Secure; SameSite=Lax; Path=/",
        },
      }
    );
  }),

  http.post(`${API}/auth/login`, async ({ request }) => {
    const body = await request.json();
    const user = state.users.get(body.email);
    if (!user || user.password !== body.password) {
      return HttpResponse.json({ detail: "Credenciales inválidas" }, { status: 401 });
    }
    state.currentEmail = body.email;
    return HttpResponse.json(
      { id: user.id, email: user.email, nickname: user.nickname },
      {
        status: 200,
        headers: {
          "Set-Cookie": "access_token=test; HttpOnly; Secure; SameSite=Lax; Path=/",
        },
      }
    );
  }),

  http.get(`${API}/auth/me`, () => {
    if (!state.currentEmail) {
      return HttpResponse.json({ detail: "Credenciales inválidas" }, { status: 401 });
    }
    const user = state.users.get(state.currentEmail);
    if (!user) {
      return HttpResponse.json({ detail: "Credenciales inválidas" }, { status: 401 });
    }
    return HttpResponse.json({ id: user.id, email: user.email, nickname: user.nickname });
  }),

  http.post(`${API}/auth/logout`, () => {
    state.currentEmail = null;
    return new HttpResponse(null, { status: 204 });
  }),

  http.post(`${API}/auth/refresh`, () => {
    if (!state.currentEmail) {
      return HttpResponse.json({ detail: "Credenciales inválidas" }, { status: 401 });
    }
    const user = state.users.get(state.currentEmail);
    return HttpResponse.json({ id: user.id, email: user.email, nickname: user.nickname });
  }),
];
