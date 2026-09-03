import { http, HttpResponse } from "msw";

const API = "http://localhost:8000";

// Shared match registry with tournamentHandlers — we re-expose via its state
// through a local map; tests can seed using seedMatchStandalone() below.
const matchState = {
  matches: new Map(),
};

export function resetMatchState() {
  matchState.matches.clear();
}

export function seedMatchStandalone(match) {
  matchState.matches.set(match.id, {
    id: match.id,
    tournament_id: match.tournament_id,
    round_number: match.round_number,
    bracket_position: match.bracket_position ?? null,
    player1_id: match.player1_id,
    player2_id: match.player2_id ?? null,
    is_bye: match.is_bye ?? false,
    tournament_code: match.tournament_code ?? null,
    code_created_at: match.code_created_at ?? null,
    state: match.state || "pending",
    winner_participant_id: match.winner_participant_id ?? null,
    resolved_at: match.resolved_at ?? null,
    ...match,
  });
}

export const matchHandlers = [
  http.get(`${API}/matches/:id`, ({ params }) => {
    const m = matchState.matches.get(params.id);
    if (!m) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    return HttpResponse.json(m);
  }),

  http.post(`${API}/matches/:id/manual-result`, async ({ params, request }) => {
    const body = await request.json();
    const m = matchState.matches.get(params.id);
    if (!m) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    if (m.state !== "pending") {
      return HttpResponse.json({ detail: "already resolved" }, { status: 409 });
    }
    m.state = "manual";
    m.winner_participant_id = body.winner_participant_id;
    m.resolved_at = new Date().toISOString();
    return HttpResponse.json(m);
  }),
];
