import { http, HttpResponse } from "msw";

const API = "http://localhost:8000";

const state = {
  // Map of nickname -> public profile payload (HD-1)
  publicProfiles: {},
  // Search fixtures: a list of users matched against the q parameter
  searchUsers: [],
  // Pending received requests (panel principal data)
  receivedRequests: [],
  // Accepted friends (GET /api/friends)
  friends: [],
  // Last action recorded — useful in tests
  lastAction: null,
};

export function resetFriendsMockState() {
  state.publicProfiles = {};
  state.searchUsers = [];
  state.receivedRequests = [];
  state.friends = [];
  state.lastAction = null;
}

export function seedFriends(friends) {
  state.friends = friends;
}

export function seedSearchUsers(users) {
  state.searchUsers = users;
}

export function seedPublicProfile(nickname, profile) {
  state.publicProfiles[nickname] = profile;
}

export function seedReceivedRequests(requests) {
  state.receivedRequests = requests;
}

export function getLastAction() {
  return state.lastAction;
}

function setRelationshipStatusByUserId(userId, newStatus, requestId = null) {
  // Update both the search list and any seeded profile so the UI sees
  // the new status after refetch.
  state.searchUsers = state.searchUsers.map((u) =>
    u.id === userId
      ? { ...u, relationship_status: newStatus, pending_request_id: requestId }
      : u,
  );
  for (const nick of Object.keys(state.publicProfiles)) {
    const profile = state.publicProfiles[nick];
    if (profile.id === userId) {
      state.publicProfiles[nick] = {
        ...profile,
        relationship_status: newStatus,
        pending_request_id: requestId,
      };
    }
  }
}

export const friendsHandlers = [
  http.get(`${API}/api/friends`, () => {
    return HttpResponse.json(state.friends);
  }),

  http.get(`${API}/api/friends/search`, ({ request }) => {
    const url = new URL(request.url);
    const q = (url.searchParams.get("q") ?? "").trim().toLowerCase();
    if (!q) {
      return HttpResponse.json([]);
    }
    const filtered = state.searchUsers.filter((u) =>
      u.nickname.toLowerCase().includes(q),
    );
    return HttpResponse.json(filtered.slice(0, 20));
  }),

  http.get(`${API}/api/friends/requests`, () => {
    return HttpResponse.json(state.receivedRequests);
  }),

  http.post(`${API}/api/friends/request/:userId`, ({ params }) => {
    const userId = params.userId;
    if (userId === "self") {
      return HttpResponse.json(
        { detail: "No puedes enviarte una solicitud a ti mismo." },
        { status: 400 },
      );
    }
    if (userId === "unknown") {
      return HttpResponse.json(
        { detail: "Usuario no encontrado." },
        { status: 404 },
      );
    }
    if (userId === "conflict") {
      return HttpResponse.json(
        {
          detail:
            "Este usuario ya te ha enviado una solicitud; acéptala desde tu panel.",
        },
        { status: 409 },
      );
    }
    state.lastAction = { type: "send", userId };
    const requestId = `req-${userId}`;
    setRelationshipStatusByUserId(userId, "PENDIENTE_ENVIADA", requestId);
    return HttpResponse.json(
      {
        id: requestId,
        requester_id: "00000000-0000-0000-0000-000000000099",
        addressee_id: userId,
        requester_nickname: "self",
        requester_avatar_url: null,
        created_at: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),

  http.post(`${API}/api/friends/request/:requestId/accept`, ({ params }) => {
    state.lastAction = { type: "accept", requestId: params.requestId };
    const accepted = state.receivedRequests.find((r) => r.id === params.requestId);
    if (accepted) {
      state.friends = [
        ...state.friends,
        {
          id: accepted.requester_id ?? `u-${accepted.id}`,
          nickname: accepted.requester_nickname,
          avatar_url: accepted.requester_avatar_url ?? null,
          relationship_status: "AMIGO",
          pending_request_id: null,
        },
      ];
    }
    state.receivedRequests = state.receivedRequests.filter((r) => r.id !== params.requestId);
    // Try to flip a row whose pending_request_id matches.
    for (const u of state.searchUsers) {
      if (u.pending_request_id === params.requestId) {
        setRelationshipStatusByUserId(u.id, "AMIGO", null);
      }
    }
    for (const nick of Object.keys(state.publicProfiles)) {
      const p = state.publicProfiles[nick];
      if (p.pending_request_id === params.requestId) {
        setRelationshipStatusByUserId(p.id, "AMIGO", null);
      }
    }
    return HttpResponse.json({
      request_id: params.requestId,
      action: "accepted",
      relationship_status: "AMIGO",
    });
  }),

  http.post(`${API}/api/friends/request/:requestId/reject`, ({ params }) => {
    state.lastAction = { type: "reject", requestId: params.requestId };
    state.receivedRequests = state.receivedRequests.filter((r) => r.id !== params.requestId);
    for (const u of state.searchUsers) {
      if (u.pending_request_id === params.requestId) {
        setRelationshipStatusByUserId(u.id, "SIN_RELACION", null);
      }
    }
    for (const nick of Object.keys(state.publicProfiles)) {
      const p = state.publicProfiles[nick];
      if (p.pending_request_id === params.requestId) {
        setRelationshipStatusByUserId(p.id, "SIN_RELACION", null);
      }
    }
    return HttpResponse.json({
      request_id: params.requestId,
      action: "rejected",
      relationship_status: "SIN_RELACION",
    });
  }),

  http.delete(`${API}/api/friends/request/:requestId`, ({ params }) => {
    state.lastAction = { type: "cancel", requestId: params.requestId };
    for (const u of state.searchUsers) {
      if (u.pending_request_id === params.requestId) {
        setRelationshipStatusByUserId(u.id, "SIN_RELACION", null);
      }
    }
    for (const nick of Object.keys(state.publicProfiles)) {
      const p = state.publicProfiles[nick];
      if (p.pending_request_id === params.requestId) {
        setRelationshipStatusByUserId(p.id, "SIN_RELACION", null);
      }
    }
    return new HttpResponse(null, { status: 204 });
  }),

  http.delete(`${API}/api/friends/:userId`, ({ params }) => {
    state.lastAction = { type: "remove", userId: params.userId };
    state.friends = state.friends.filter((f) => f.id !== params.userId);
    setRelationshipStatusByUserId(params.userId, "SIN_RELACION", null);
    return new HttpResponse(null, { status: 204 });
  }),

  // Public profile (also used by GET /api/profile/{nickname})
  http.get(`${API}/api/profile/:nickname`, ({ params }) => {
    const profile = state.publicProfiles[params.nickname];
    if (!profile) {
      return HttpResponse.json(
        { detail: "Usuario no encontrado." },
        { status: 404 },
      );
    }
    return HttpResponse.json(profile);
  }),
];
