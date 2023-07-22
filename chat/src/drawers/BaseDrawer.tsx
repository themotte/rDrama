import React, { PropsWithChildren, useEffect } from "react";
import "./BaseDrawer.css";

interface Props extends PropsWithChildren {
  onClose?(): void;
}

export function BaseDrawer({ onClose, children }: Props) {
  return <div className="BaseDrawer">{children}</div>;
}
