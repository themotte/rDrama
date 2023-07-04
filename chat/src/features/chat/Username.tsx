import React from "react";
import "./Username.css";

interface UsernameProps {
  avatar: string;
  color: string;
  name: string;
}

export function Username({ avatar, color, name, hat = "" }: UsernameProps) {
  return (
    <div className="Username">
      <div className="profile-pic-20-wrapper">
        <img alt={name} src={avatar} className="pp20" />
      </div>
      <a
        className="userlink"
        style={{ color: `#${color}` }}
        target="_blank"
        href={`/@${name}`}
        rel="nofollow noopener"
      >
        {name}
      </a>
    </div>
  );
}
