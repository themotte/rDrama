import React from "react";
import { useChat } from "../../hooks";
import "./UsersTyping.css";

export function UsersTyping() {
  const { typing } = useChat();
  const [first, second, third, ...rest] = typing;

  return (
    <div className="UsersTyping">
      {(() => {
        if (rest.length > 0) {
          return `${first}, ${second}, ${third} and ${rest.length} more are typing...`;
        }

        if (first && second && third) {
          return `${first}, ${second} and ${third} are typing...`;
        }

        if (first && second) {
          return `${first} and ${second} are typing...`;
        }

        if (first) {
          return `${first} is typing...`;
        }

        return null;
      })()}
    </div>
  );
}
