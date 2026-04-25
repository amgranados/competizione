import { http, HttpResponse } from "msw";

const API = "http://localhost:8000";

const state = {
  tournaments: new Map(),
  invitations: new Map(),
  participants: new Map(),
  matches: new Map(),
  notifications: [],
};

export function resetTournamentState() {
  state.tournaments.clear();
  state.invitations.clear();
  state.participants.clear();
  state.matches.clear();
  state.notifications.length = 0;
}

export function seedTournament(tournament) {
  state.tournaments.set(tournament.id, {
    id: tournament.id,
    name: tournament.name,
    format: tournament.format || "round_robin",
    state: tournament.state || "draft",
    organizer_id: tournament.organizer_id,
    created_at: tournament.created_at || new Date().toISOString(),
    start_at: null,
    started_at: null,
    finished_at: null,
    cancelled_at: null,
    participants: tournament.participants || [],
    ...tournament,
  });
}

export function seedInvitation(invitation) {
  state.invitations.set(invitation.id, {
    id: invitation.id,
    tournament_id: invitation.tournament_id,
    invited_user_id: invitation.invited_user_id,
    inviter_user_id: invitation.inviter_user_id,
    state: invitation.state || "pending",
    created_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 48 * 3600 * 1000).toISOString(),
    responded_at: null,
    ...invitation,
  });
}

export function seedMatch(match) {
  state.matches.set(match.id, {
    id: match.id,
    tournament_id: match.tournament_id,
    round_number: match.round_number,
    bracket_position: match.bracket_position ?? null,
    player1_id: match.player1_id,
    player2_id: match.player2_id ?? null,
    is_bye: match.is_bye ?? false,
    tournament_code: match.tournament_code ?? null,
    state: match.state || "pending",
    winner_participant_id: match.winner_participant_id ?? null,
    ...match,
  });
}

export function pushNotification(notification) {
  state.notifications.push({
    id: notification.id || crypto.randomUUID(),
    user_id: notification.user_id,
    type: notification.type,
    tournament_id: notification.tournament_id ?? null,
    match_id: notification.match_id ?? null,
    invitation_id: notification.invitation_id ?? null,
    created_at: notification.created_at || new Date().toISOString(),
    read_at: null,
    ...notification,
  });
}

export const tournamentHandlers = [
  http.get(`${API}/tournaments`, () => {
    return HttpResponse.json([...state.tournaments.values()]);
  }),

  http.post(`${API}/tournaments`, async ({ request }) => {
    const body = await request.json();
    const id = crypto.randomUUID();
    const t = {
      id,
      name: body.name,
      format: body.format,
      state: "draft",
      organizer_id: "__current__",
      created_at: new Date().toISOString(),
      started_at: null,
      finished_at: null,
      cancelled_at: null,
      start_at: body.start_at ?? null,
      participants: [],
    };
    state.tournaments.set(id, t);
    return HttpResponse.json(t, { status: 201 });
  }),

  http.get(`${API}/tournaments/:id`, ({ params }) => {
    const t = state.tournaments.get(params.id);
    if (!t) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    return HttpResponse.json(t);
  }),

  http.patch(`${API}/tournaments/:id`, async ({ params, request }) => {
    const t = state.tournaments.get(params.id);
    if (!t) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    if (t.state !== "draft" && t.state !== "open") {
      return HttpResponse.json({ detail: "locked" }, { status: 409 });
    }
    const body = await request.json();
    if (body.name) t.name = body.name;
    if (body.format) t.format = body.format;
    return HttpResponse.json(t);
  }),

  http.post(`${API}/tournaments/:id/open`, ({ params }) => {
    const t = state.tournaments.get(params.id);
    if (!t) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    t.state = "open";
    return HttpResponse.json(t);
  }),

  http.post(`${API}/tournaments/:id/cancel`, ({ params }) => {
    const t = state.tournaments.get(params.id);
    if (!t) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    if (t.state === "finished" || t.state === "cancelled") {
      return HttpResponse.json({ detail: "terminal" }, { status: 409 });
    }
    t.state = "cancelled";
    t.cancelled_at = new Date().toISOString();
    return HttpResponse.json(t);
  }),

  http.post(`${API}/tournaments/:id/start`, ({ params }) => {
    const t = state.tournaments.get(params.id);
    if (!t) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    if ((t.participants || []).length < 2) {
      return HttpResponse.json({ detail: "need at least 2" }, { status: 409 });
    }
    t.state = "active";
    t.started_at = new Date().toISOString();
    return HttpResponse.json(t);
  }),

  http.post(`${API}/tournaments/:id/invitations`, async ({ params, request }) => {
    const body = await request.json();
    const id = crypto.randomUUID();
    const inv = {
      id,
      tournament_id: params.id,
      invited_user_id: body.invited_user_id,
      inviter_user_id: "__organizer__",
      state: "pending",
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 48 * 3600 * 1000).toISOString(),
      responded_at: null,
    };
    state.invitations.set(id, inv);
    return HttpResponse.json(inv, { status: 201 });
  }),

  http.get(`${API}/tournaments/:id/invitations`, ({ params }) => {
    const list = [...state.invitations.values()].filter((i) => i.tournament_id === params.id);
    return HttpResponse.json(list);
  }),

  http.post(`${API}/tournaments/:id/invitations/:iid/cancel`, ({ params }) => {
    const inv = state.invitations.get(params.iid);
    if (!inv) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    inv.state = "cancelled";
    return HttpResponse.json(inv);
  }),

  http.get(`${API}/invitations`, ({ request }) => {
    const url = new URL(request.url);
    const stateFilter = url.searchParams.get("state");
    let list = [...state.invitations.values()];
    if (stateFilter) list = list.filter((i) => i.state === stateFilter);
    return HttpResponse.json(list);
  }),

  http.post(`${API}/invitations/:iid/accept`, ({ params }) => {
    const inv = state.invitations.get(params.iid);
    if (!inv) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    inv.state = "accepted";
    return HttpResponse.json(inv);
  }),

  http.post(`${API}/invitations/:iid/reject`, ({ params }) => {
    const inv = state.invitations.get(params.iid);
    if (!inv) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    inv.state = "rejected";
    return HttpResponse.json(inv);
  }),

  http.delete(`${API}/tournaments/:id/participants/:pid`, ({ params }) => {
    const t = state.tournaments.get(params.id);
    if (!t) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    t.participants = (t.participants || []).filter((p) => p.id !== params.pid);
    return new HttpResponse(null, { status: 204 });
  }),

  http.get(`${API}/tournaments/:id/schedule`, ({ params }) => {
    const matches = [...state.matches.values()].filter((m) => m.tournament_id === params.id);
    const t = state.tournaments.get(params.id);
    if (!t) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    const byRound = new Map();
    for (const m of matches) {
      if (!byRound.has(m.round_number)) byRound.set(m.round_number, []);
      byRound.get(m.round_number).push(m);
    }
    const rounds = [...byRound.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([number, ms]) => ({ number, matches: ms }));
    return HttpResponse.json({ format: t.format, rounds });
  }),

  http.get(`${API}/tournaments/:id/standings`, ({ params }) => {
    const t = state.tournaments.get(params.id);
    if (!t || t.format !== "round_robin") {
      return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    }
    return HttpResponse.json([]);
  }),

  http.get(`${API}/tournaments/:id/bracket`, ({ params }) => {
    const t = state.tournaments.get(params.id);
    if (!t || t.format !== "single_elim") {
      return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    }
    return HttpResponse.json({ format: "single_elim", rounds: [] });
  }),

  http.get(`${API}/notifications`, () => {
    return HttpResponse.json(state.notifications);
  }),

  http.patch(`${API}/notifications/:id/read`, ({ params }) => {
    const notif = state.notifications.find((n) => n.id === params.id);
    if (!notif) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    notif.read_at = new Date().toISOString();
    return HttpResponse.json(notif);
  }),
];
