import { request } from "./authApi.js";

export const tournamentApi = {
  listMine: (state) => request(`/tournaments${state ? `?state=${state}` : ""}`),
  create: ({ name, format, start_at }) =>
    request("/tournaments", { method: "POST", body: { name, format, start_at } }),
  update: (id, payload) => request(`/tournaments/${id}`, { method: "PATCH", body: payload }),
  getById: (id) => request(`/tournaments/${id}`),
  openRegistration: (id) => request(`/tournaments/${id}/open`, { method: "POST" }),
  start: (id) => request(`/tournaments/${id}/start`, { method: "POST" }),
  cancel: (id) => request(`/tournaments/${id}/cancel`, { method: "POST" }),
  invite: (id, invitedUserId) =>
    request(`/tournaments/${id}/invitations`, {
      method: "POST",
      body: { invited_user_id: invitedUserId },
    }),
  listInvitations: (id) => request(`/tournaments/${id}/invitations`),
  cancelInvitation: (tournamentId, invitationId) =>
    request(`/tournaments/${tournamentId}/invitations/${invitationId}/cancel`, {
      method: "POST",
    }),
  listMyInvitations: (state) =>
    request(`/invitations${state ? `?state=${state}` : ""}`),
  acceptInvitation: (invitationId) =>
    request(`/invitations/${invitationId}/accept`, { method: "POST" }),
  rejectInvitation: (invitationId) =>
    request(`/invitations/${invitationId}/reject`, { method: "POST" }),
  removeParticipant: (tournamentId, participantId) =>
    request(`/tournaments/${tournamentId}/participants/${participantId}`, {
      method: "DELETE",
    }),
  getSchedule: (id) => request(`/tournaments/${id}/schedule`),
  getStandings: (id) => request(`/tournaments/${id}/standings`),
  getBracket: (id) => request(`/tournaments/${id}/bracket`),
};
