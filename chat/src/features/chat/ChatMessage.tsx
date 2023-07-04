import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import cx from "classnames";
import key from "weak-key";
import humanizeDuration from "humanize-duration";
import cloneDeep from "lodash.clonedeep";
import { Username } from "./Username";
import {
  DIRECT_MESSAGE_ID,
  OPTIMISTIC_MESSAGE_ID,
  useChat,
  useRootContext,
} from "../../hooks";
import { QuotedMessageLink } from "./QuotedMessageLink";
import "./ChatMessage.css";

interface ChatMessageProps {
  message: IChatMessage;
  timestampUpdates: number;
  showUser?: boolean;
  actionsOpen: boolean;
  onToggleActions(messageId: string): void;
}

const TIMESTAMP_UPDATE_INTERVAL = 20000;

export function ChatMessage({
  message,
  showUser = true,
  timestampUpdates,
  actionsOpen,
  onToggleActions,
}: ChatMessageProps) {
  const {
    id,
    user_id,
    avatar,
    username,
    text,
    text_html,
    time,
    quotes,
    dm,
  } = message;
  const {
    id: userId,
    username: userUsername,
    admin,
    themeColor,
  } = useRootContext();
  const {
    messageLookup,
    userToDm,
    quote,
    deleteMessage,
    quoteMessage,
    updateUserToDm,
  } = useChat();
  const [confirmedDelete, setConfirmedDelete] = useState(false);
  const quotedMessage = messageLookup[quotes];
  const content = text_html;
  const isMention =
    quotedMessage?.username === userUsername ||
    (text_html.includes(`/id/${userId}`) &&
      userUsername &&
      username !== userUsername);
  const isDirect = id === DIRECT_MESSAGE_ID;
  const isOptimistic = id === OPTIMISTIC_MESSAGE_ID;
  const timestamp = useMemo(
    () => formatTimeAgo(time),
    [time, timestampUpdates]
  );
  const handleDeleteMessage = useCallback(() => {
    if (confirmedDelete) {
      deleteMessage(text);
    } else {
      setConfirmedDelete(true);
    }
  }, [text, confirmedDelete]);
  const handleQuoteMessageAction = useCallback(() => {
    updateUserToDm(null);
    quoteMessage(message);
    onToggleActions(message.id);
  }, [message, onToggleActions]);
  const handleDirectMessage = useCallback(
    (toggle?: boolean) => {
      const userId = message.user_id ?? "";

      if (userToDm && userToDm.id === userId) {
        updateUserToDm(null);
      } else if (userId) {
        updateUserToDm({
          id: userId,
          username: message.username,
        });

        quoteMessage(null);

        if (toggle) {
          onToggleActions(message.id);
        }
      }
    },
    [userToDm, message.id, message.user_id, message.username]
  );

  useEffect(() => {
    if (!actionsOpen) {
      setConfirmedDelete(false);
    }
  }, [actionsOpen]);

  return (
    <div
      className={cx("ChatMessage", {
        ChatMessage__isDm: dm,
        ChatMessage__isOptimistic: isOptimistic,
      })}
      id={id}
      style={
        isMention && !dm
          ? {
              background: `#${themeColor}25`,
              borderLeft: `1px solid #${themeColor}`,
            }
          : {}
      }
    >
      {!isDirect && !isOptimistic && !actionsOpen && (
        <div className="ChatMessage-actions-button">
          <button
            className="btn btn-secondary"
            onClick={() => {
              updateUserToDm(null);
              quoteMessage(quote ? null : message);
            }}
          >
            <i className="fas fa-reply" />
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => onToggleActions(id)}
          >
            ...
          </button>
        </div>
      )}
      {!isDirect && !isOptimistic && actionsOpen && (
        <div className="ChatMessage-actions">
          {userId && parseInt(userId) !== parseInt(user_id) && (
            <button
              className="btn btn-secondary ChatMessage-button"
              onClick={() => handleDirectMessage(true)}
            >
              📨 DM @{message.username}
            </button>
          )}
          <button
            className="btn btn-secondary ChatMessage-button"
            onClick={handleQuoteMessageAction}
          >
            <i className="fas fa-reply" /> Reply
          </button>
          {admin && (
            <button
              className={cx("btn btn-secondary ChatMessage-button", {
                "ChatMessage-button__confirmed": confirmedDelete,
              })}
              onClick={handleDeleteMessage}
            >
              <i className="fas fa-trash-alt" />{" "}
              {confirmedDelete ? "Are you sure?" : "Delete"}
            </button>
          )}
          <button
            className="btn btn-secondary ChatMessage-button"
            onClick={() => onToggleActions(id)}
          >
            <i>X</i> Close
          </button>
        </div>
      )}
      {showUser && (
        <div className="ChatMessage-top">
          <Username
            avatar={avatar}
            name={username}
            color="#000"
          />
          <div className="ChatMessage-timestamp">{timestamp}</div>
        </div>
      )}
      {quotes && quotedMessage && (
        <div className="ChatMessage-quoted-link">
          <QuotedMessageLink message={quotedMessage} />
        </div>
      )}
      {!isDirect && dm && (
        <small className="ChatMessage-quoted-link text-primary">
          <em>(Sent only to you)</em>
        </small>
      )}
      <div className="ChatMessage-bottom">
        <div>
          <span
            className="ChatMessage-content"
            title={content}
            dangerouslySetInnerHTML={{
              __html: content,
            }}
          />
        </div>
      </div>
    </div>
  );
}

export function ChatMessageList() {
  const listRef = useRef<HTMLDivElement>(null);
  const { messages } = useChat();
  const [timestampUpdates, setTimestampUpdates] = useState(0);
  const groupedMessages = useMemo(() => groupMessages(messages), [messages]);
  const [actionsOpenForMessage, setActionsOpenForMessage] = useState<
    string | null
  >(null);
  const handleToggleActionsForMessage = useCallback(
    (messageId: string) =>
      setActionsOpenForMessage(
        messageId === actionsOpenForMessage ? null : messageId
      ),
    [actionsOpenForMessage]
  );

  useEffect(() => {
    const updatingTimestamps = setInterval(
      () => setTimestampUpdates((prev) => prev + 1),
      TIMESTAMP_UPDATE_INTERVAL
    );

    return () => {
      clearInterval(updatingTimestamps);
    };
  }, []);

  useLayoutEffect(() => {
    const images = Array.from(
      listRef.current.getElementsByTagName("img")
    ).filter((image) => image.dataset.src);

    for (const image of images) {
      image.src = image.dataset.src;
    }
  }, [messages]);

  return (
    <div className="ChatMessageList" ref={listRef}>
      {groupedMessages.map((group) => (
        <div key={key(group)} className="ChatMessageList-group">
          {group.map((message, index) => (
            <ChatMessage
              key={key(message)}
              message={message}
              timestampUpdates={timestampUpdates}
              showUser={index === 0}
              actionsOpen={actionsOpenForMessage === message.id}
              onToggleActions={handleToggleActionsForMessage}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function formatTimeAgo(time: number) {
  const shortEnglishHumanizer = humanizeDuration.humanizer({
    language: "shortEn",
    languages: {
      shortEn: {
        y: () => "y",
        mo: () => "mo",
        w: () => "w",
        d: () => "d",
        h: () => "h",
        m: () => "m",
        s: () => "s",
        ms: () => "ms",
      },
    },
    round: true,
    units: ["h", "m", "s"],
    largest: 2,
    spacer: "",
    delimiter: ", ",
  });
  const now = new Date().getTime();
  const humanized = `${shortEnglishHumanizer(time * 1000 - now)} ago`;

  return humanized === "0s ago" ? "just now" : humanized;
}

function groupMessages(messages: IChatMessage[]) {
  const grouped: IChatMessage[][] = [];
  let lastUsername = "";
  let temp: IChatMessage[] = [];

  for (const message of messages) {
    if (!lastUsername) {
      lastUsername = message.username;
    }

    if (message.username === lastUsername) {
      temp.push(message);
    } else {
      grouped.push(cloneDeep(temp));
      lastUsername = message.username;
      temp = [message];
    }
  }

  if (temp.length > 0) {
    grouped.push(cloneDeep(temp));
  }

  return grouped;
}
