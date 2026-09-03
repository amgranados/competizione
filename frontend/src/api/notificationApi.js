import { request } from "./authApi.js";

export const notificationApi = {
  list: (unread = false) => request(`/notifications${unread ? "?unread=true" : ""}`),
  markRead: (id) => request(`/notifications/${id}/read`, { method: "PATCH" }),
};
