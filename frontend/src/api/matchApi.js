import { request } from "./authApi.js";

export const matchApi = {
  getById: (id) => request(`/matches/${id}`),
  registerManualResult: (id, winnerParticipantId) =>
    request(`/matches/${id}/manual-result`, {
      method: "POST",
      body: { winner_participant_id: winnerParticipantId },
    }),
};
