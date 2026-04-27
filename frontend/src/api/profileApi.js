import { request } from "./authApi.js";

export const profileApi = {
  getProfile: () => request("/api/profile"),
  updateNickname: (nickname) =>
    request("/api/profile/nickname", { method: "PATCH", body: { nickname } }),
  updatePassword: ({ current_password, new_password }) =>
    request("/api/profile/password", {
      method: "PATCH",
      body: { current_password, new_password },
    }),
  updateAvatar: (avatar_url) =>
    request("/api/profile/avatar", { method: "PATCH", body: { avatar_url } }),
  linkLoL: ({ game_name, tag_line, region }) =>
    request("/api/profile/link/lol", {
      method: "POST",
      body: { game_name, tag_line, region },
    }),
  unlinkLoL: () => request("/api/profile/link/lol", { method: "DELETE" }),
  deleteAccount: (confirmation) =>
    request("/api/profile/me", { method: "DELETE", body: { confirmation } }),
};
