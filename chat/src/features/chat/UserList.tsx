import React from "react";
import cx from "classnames";
import { useChat } from "../../hooks";
import "./UserList.css";

interface Props {
  fluid?: boolean;
}

export function UserList({ fluid = false }: Props) {
  const { online } = useChat();

  return (
    <div className="UserList">
      <div className="UserList-heading">
        <h5>Users Online</h5>
        <div className="Chat-online">
          <i className="far fa-user fa-sm" /> {online.length}
        </div>
      </div>
      <ul className={cx({ fluid })}>
        {online.map((user) => (
          <li key={user}>
            <a href={`/@${user}`}>@{user}</a>
          </li>
        ))}
      </ul>
    </div>
  );
}
