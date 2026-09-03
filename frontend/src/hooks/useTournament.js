import { useCallback } from "react";
import { usePolling } from "./usePolling.js";
import { tournamentApi } from "../api/tournamentApi.js";

export function useTournament(tournamentId, intervalMs = 10000) {
  const fetcher = useCallback(() => tournamentApi.getById(tournamentId), [tournamentId]);
  return usePolling(fetcher, intervalMs);
}

export function useTournamentSchedule(tournamentId, intervalMs = 10000) {
  const fetcher = useCallback(() => tournamentApi.getSchedule(tournamentId), [tournamentId]);
  return usePolling(fetcher, intervalMs);
}
