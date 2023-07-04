import React, {
  ChangeEvent,
  KeyboardEvent,
  FormEvent,
  useCallback,
  useRef,
  useMemo,
  useState,
  useEffect,
} from "react";
import cx from "classnames";
import { useChat } from "../../hooks";
import "./UserInput.css";

interface Props {
  large?: boolean;
  onFocus(): void;
  onBlur(): void;
}

export function UserInput({ large = false, onFocus, onBlur }: Props) {
  const { draft, userToDm, sendMessage, updateDraft } = useChat();
  const builtChatInput = useRef<HTMLTextAreaElement>(null);
  const form = useRef<HTMLFormElement>(null);
  const [typingOffset, setTypingOffset] = useState(0);
  const handleChange = useCallback(
    (event: ChangeEvent<HTMLTextAreaElement>) => {
      const input = event.target.value;
      updateDraft(input);
    },
    []
  );
  const handleSendMessage = useCallback(
    (event?: FormEvent<HTMLFormElement>) => {
      event?.preventDefault();
      sendMessage();
    },
    [sendMessage]
  );
  const handleKeyUp = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === "Enter" && !event.shiftKey) {
        handleSendMessage();
      }
    },
    [handleSendMessage]
  );
  const handleFocus = useCallback(() => {
    builtChatInput.current?.scrollIntoView({ behavior: "smooth" });
    onFocus();
  }, [onFocus]);

  useEffect(() => {
    if (userToDm) {
      builtChatInput.current?.focus();
    }
  }, [userToDm])

  return (
    <form ref={form} className="UserInput" onSubmit={handleSendMessage}>
      <textarea
        ref={builtChatInput}
        id="builtChatInput"
        className={cx("UserInput-input form-control", {
          "UserInput-input__large": large
        })}
        minLength={1}
        maxLength={1000}
        rows={1}
        onChange={handleChange}
        onKeyUp={handleKeyUp}
        onFocus={handleFocus}
        onBlur={onBlur}
        placeholder="Message"
        autoComplete="off"
        value={draft}
      />
      <button
        className="btn btn-secondary"
        disabled={draft.length === 0}
        onClick={sendMessage}
      >
        <i className="UserInput-emoji fas fa-reply" />
      </button>
    </form>
  );
}
