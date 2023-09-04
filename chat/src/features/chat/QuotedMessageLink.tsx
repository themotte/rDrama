import React, { useCallback, useMemo } from "react";
import { useRootContext } from "../../hooks";
import "./QuotedMessageLink.css";

const SCROLL_TO_QUOTED_OVERFLOW = 250;
const QUOTED_MESSAGE_CONTEXTUAL_HIGHLIGHTING_DURATION = 2500;
const QUOTED_MESSAGE_CONTEXTUAL_SNIPPET_LENGTH = 30;

export function QuotedMessageLink({ message }: { message: IChatMessage }) {
  const { themeColor } = useRootContext();
  const handleLinkClick = useCallback(() => {
    const element = document.getElementById(message.id);

    if (element) {
      element.scrollIntoView();
      element.style.background = `#${themeColor}33`;

      setTimeout(() => {
        element.style.background = "unset";
      }, QUOTED_MESSAGE_CONTEXTUAL_HIGHLIGHTING_DURATION);

      const [appContent] = Array.from(
        document.getElementsByClassName("App-content")
      );

      if (appContent) {
        appContent.scrollTop -= SCROLL_TO_QUOTED_OVERFLOW;
      }
    }
  }, []);
  const replyText = useMemo(() => {
    const textToUse = message.text;
    const slicedText = textToUse.slice(
      0,
      QUOTED_MESSAGE_CONTEXTUAL_SNIPPET_LENGTH
    );

    return textToUse.length >= QUOTED_MESSAGE_CONTEXTUAL_SNIPPET_LENGTH
      ? `${slicedText}...`
      : slicedText;
  }, [message]);

  return (
    <a className="QuotedMessageLink" href="#" onClick={handleLinkClick}>
      <i className="fas fa-reply" /> @{message.username}:{" "}
      <em>"{replyText}"</em>
    </a>
  );
}
