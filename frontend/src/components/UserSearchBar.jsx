import { useCallback, useEffect, useRef, useState } from "react";
import { friendsApi } from "../api/friendsApi.js";
import { ApiError } from "../api/authApi.js";
import Input from "./ui/Input.jsx";
import { T } from "../styles/theme.js";
import UserSearchResult from "./UserSearchResult.jsx";

const DEBOUNCE_MS = 300;

/**
 * Search bar with a debounced request to /api/friends/search and a dropdown
 * of UserSearchResult rows. Each row has its own FriendshipButton whose
 * state is computed by the backend (HD-1). After any friendship action,
 * the parent refetches the search to keep status fresh.
 */
export default function UserSearchBar({ inline = false }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | loaded | error
  const [open, setOpen] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const debounceRef = useRef(null);
  const lastQueryRef = useRef("");

  const runSearch = useCallback(async (q) => {
    lastQueryRef.current = q;
    if (!q.trim()) {
      setResults([]);
      setStatus("idle");
      return;
    }
    setStatus("loading");
    try {
      const data = await friendsApi.searchUsers(q);
      // Avoid stale responses if the user kept typing.
      if (lastQueryRef.current === q) {
        setResults(data);
        setStatus("loaded");
      }
    } catch (err) {
      if (lastQueryRef.current === q) {
        setStatus("error");
      }
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => runSearch(query), DEBOUNCE_MS);
    return () => clearTimeout(debounceRef.current);
  }, [query, runSearch]);

  const handleAction = async (verb, target) => {
    setErrorMsg(null);
    try {
      if (verb === "send") {
        await friendsApi.sendRequest(target.id);
      } else if (verb === "accept" && target.pending_request_id) {
        await friendsApi.acceptRequest(target.pending_request_id);
      } else if (verb === "reject" && target.pending_request_id) {
        await friendsApi.rejectRequest(target.pending_request_id);
      } else if (verb === "cancel" && target.pending_request_id) {
        await friendsApi.cancelRequest(target.pending_request_id);
      } else if (verb === "remove") {
        await friendsApi.removeFriend(target.id);
      }
      // Refetch with the current query so the row reflects the new status.
      runSearch(query);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Operación fallida.";
      setErrorMsg(typeof detail === "string" ? detail : "Operación fallida.");
    }
  };

  const dropdownVisible = open && query.trim().length > 0;

  return (
    <div
      style={{
        position: "relative",
        width: inline ? "100%" : 320,
      }}
    >
      <Input
        type="search"
        placeholder="Buscar usuarios…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        aria-label="Buscar usuarios"
      />
      {dropdownVisible && (
        <div
          role="listbox"
          aria-label="Resultados de búsqueda"
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            left: 0,
            right: 0,
            background: T.s1,
            border: `1px solid ${T.bd}`,
            borderRadius: T.r,
            zIndex: 30,
            maxHeight: 320,
            overflowY: "auto",
          }}
        >
          {status === "loading" && (
            <div style={{ padding: 10, color: T.tx2, fontSize: 12 }}>
              Buscando…
            </div>
          )}
          {status === "error" && (
            <div role="alert" style={{ padding: 10, color: T.ac, fontSize: 12 }}>
              No se pudo realizar la búsqueda.
            </div>
          )}
          {status === "loaded" && results.length === 0 && (
            <div style={{ padding: 10, color: T.tx2, fontSize: 12 }}>
              No hay resultados
            </div>
          )}
          {status === "loaded" && results.length > 0 && (
            <>
              {results.map((u) => (
                <UserSearchResult
                  key={u.id}
                  user={u}
                  onSendRequest={() => handleAction("send", u)}
                  onAccept={() => handleAction("accept", u)}
                  onReject={() => handleAction("reject", u)}
                  onCancel={() => handleAction("cancel", u)}
                  onRemove={() => handleAction("remove", u)}
                />
              ))}
            </>
          )}
          {errorMsg && (
            <div role="alert" style={{ padding: 10, color: T.ac, fontSize: 12 }}>
              {errorMsg}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
