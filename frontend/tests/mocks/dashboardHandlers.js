import { http, HttpResponse } from "msw";

const API = "http://localhost:8000";

const DEFAULT_RESPONSE = {
  greeting: "Hola, Org",
  subtitle: "Tu centro de operaciones competitivo",
  stats: {
    active_tournaments: { count: 0, weekly_delta: null },
    total_wins: { wins: 0, games_played: 0, winrate: null },
    best_streak: { best: 0, tournament_id: null, tournament_name: null },
    friends_count: 0,
  },
  my_tournaments: [],
  activity: [],
};

let response = DEFAULT_RESPONSE;

export function resetDashboardState() {
  response = DEFAULT_RESPONSE;
}

export function seedDashboard(partial) {
  response = {
    ...DEFAULT_RESPONSE,
    ...partial,
    stats: { ...DEFAULT_RESPONSE.stats, ...(partial?.stats ?? {}) },
  };
}

export const dashboardHandlers = [
  http.get(`${API}/api/dashboard`, () => HttpResponse.json(response)),
];
