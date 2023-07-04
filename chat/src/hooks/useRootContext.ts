import { useEffect, useState } from "react";

export function useRootContext() {
  const [
    {
      admin,
      id,
      username,
      themeColor,
      siteName,
      avatar,
    },
    setContext,
  ] = useState({
    id: "",
    username: "",
    admin: false,
    themeColor: "#ff66ac",
    siteName: "",
    avatar: "",
  });

  useEffect(() => {
    const root = document.getElementById("root");

    setContext({
      id: root.dataset.id,
      username: root.dataset.username,
      admin: root.dataset.admin === "True",
      themeColor: root.dataset.themecolor,
      siteName: root.dataset.sitename,
      avatar: root.dataset.avatar,
    });
  }, []);

  return {
    id,
    admin,
    username,
    themeColor,
    siteName,
    avatar,
  };
}
