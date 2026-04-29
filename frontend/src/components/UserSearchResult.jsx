import { Link } from "react-router-dom";
import Ava from "./ui/Ava.jsx";
import { T } from "../styles/theme.js";
import FriendshipButton from "./FriendshipButton.jsx";

/**
 * One row of /api/friends/search results. Includes an inline FriendshipButton
 * whose state comes from the backend (HD-1). The handlers are passed by the
 * parent so it can refetch the search after each action.
 */
export default function UserSearchResult({
  user,
  onSendRequest,
  onAccept,
  onReject,
  onCancel,
  onRemove,
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 10px",
        borderBottom: `1px solid ${T.bd}`,
      }}
    >
      <Link
        to={`/users/${encodeURIComponent(user.nickname)}`}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          textDecoration: "none",
          color: T.tx,
          flex: 1,
          minWidth: 0,
        }}
      >
        <Ava name={user.nickname} src={user.avatar_url} size={28} />
        <span
          style={{
            fontFamily: T.fB,
            fontSize: 13,
            fontWeight: 500,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {user.nickname}
        </span>
      </Link>
      <FriendshipButton
        status={user.relationship_status}
        onSendRequest={() => onSendRequest?.(user)}
        onAccept={() => onAccept?.(user)}
        onReject={() => onReject?.(user)}
        onCancel={() => onCancel?.(user)}
        onRemove={() => onRemove?.(user)}
      />
    </div>
  );
}
