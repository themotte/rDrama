import React from "react";
import cx from 'classnames'
import { useDrawer } from "../../hooks";
import "./ActivityList.css";

const ACTIVITIES = [
  {
    game: "Poker",
    description: "Know when to hold 'em.",
    icon: "fas fa-cards",
  },
  {
    game: "Roulette",
    description: "Table go brrrr.",
    icon: "fas fa-circle",
  },
  {
    game: "Slots",
    description: "Is today your lucky day?",
    icon: "fas fa-dollar-sign",
  },
  {
    game: "Blackjack",
    description: "Twenty one ways to change your life.",
    icon: "fas fa-cards",
  },
  {
    game: "Racing",
    description: "Look at 'em go.",
    icon: "fas fa-cards",
  },
  {
    game: "Crossing",
    description: "A simple life.",
    icon: "fas fa-cards",
  },
  {
    game: "Lottershe",
    description: "Can't win if you don't play.",
    icon: "fas fa-ticket",
  },
];

export function ActivityList() {
  const { toggle } = useDrawer();

  return (
    <div className="ActivityList">
      <h4>
        <hr />
        <span>Activities</span>
      </h4>
      <section>
        {ACTIVITIES.map(({ game, description, icon }) => (
          <div key={game} role="button" onClick={toggle}>
            <div className="ActivityList-activity">
              <div className="ActivityList-activity">
                <i className={cx("ActivityList-activity-icon", icon)} />
                <h5>{game}<br /><small>{description}</small></h5>
              </div>

              <small><i className="far fa-user fa-sm" /> 0</small>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
