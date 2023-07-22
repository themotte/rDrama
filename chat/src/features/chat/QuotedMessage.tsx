import React from "react";
import { useChat } from "../../hooks";
import "./QuotedMessage.css";
import { QuotedMessageLink } from "./QuotedMessageLink";

export function QuotedMessage() {
  const { quote, quoteMessage } = useChat();

  return (
    <div className="QuotedMessage">
      <QuotedMessageLink message={quote} />
      <button
        type="button"
        className="btn btn-secondary"
        onClick={() => quoteMessage(null)}
      >
        Cancel
      </button>
    </div>
  );
}
