import React, { useCallback } from "react";
import { useChat, useDrawer } from "../../hooks";
import { UserList } from "./UserList";
import "./ChatHeading.css";

export function ChatHeading() {
  const { open, hide, reveal } = useDrawer();
  const { online } = useChat();
  const handleToggleUserListDrawer = useCallback(() => {
    if (open) {
      hide();
    } else {
      reveal({
        title: "Users in chat",
        content: <UserList fluid={true} />,
      });
    }
  }, [open]);

  return (
    <div className="ChatHeading">
      <div />
      <div>
        {open ? (
          <button
            className="btn btn-secondary"
            onClick={handleToggleUserListDrawer}
          >Close</button>
        ) : (
          <>
            <i
              role="button"
              className="far fa-user"
              onClick={handleToggleUserListDrawer}
            />
            <em>{online.length} users online</em>
          </>
        )}
      </div>
    </div>
  );
}
