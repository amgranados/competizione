import { request } from "./authApi.js";

export const friendsApi = {
  getFriends: () => request("/api/friends"),
  searchUsers: (q) =>
    request(`/api/friends/search?q=${encodeURIComponent(q)}`),
  getReceivedRequests: () => request("/api/friends/requests"),
  getInvitable: () => request("/api/friends/invitable"),
  sendRequest: (userId) =>
    request(`/api/friends/request/${userId}`, { method: "POST" }),
  acceptRequest: (requestId) =>
    request(`/api/friends/request/${requestId}/accept`, { method: "POST" }),
  rejectRequest: (requestId) =>
    request(`/api/friends/request/${requestId}/reject`, { method: "POST" }),
  cancelRequest: (requestId) =>
    request(`/api/friends/request/${requestId}`, { method: "DELETE" }),
  removeFriend: (userId) =>
    request(`/api/friends/${userId}`, { method: "DELETE" }),
};
