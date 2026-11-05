# Open behavior audits

Behaviors the spec has not yet decided on purpose. Each needs a decision from the site owner, then tests pinning it (and fixes where the decision differs from today).

## Suspension

Decided and pinned in `users/test_suspended.py`: while suspended (permanently, or until `unban_utc`), a user can't change anything other users see (their content, their public profile, following). Deleting own content, saving, subscribing, unfollowing, removing followers, blocking and private preferences still work.

Not yet audited. The app today has three different notions of "banned", and the routes below pick among them inconsistently:
- `is_suspended`: banned and the ban hasn't run out;
- `is_suspended_permanently`: banned with no end time;
- raw `is_banned`: set, even after a temporary ban ran out, until the lazy unban runs (on the viewer's next front-page load, `routes/front.py`).

What to decide, case by case:
- **Voting** (`/vote/post`, `/vote/comment`): refused only when permanently suspended (`is_not_permabanned`); a temporarily suspended user votes normally. The handlers' own "permabanned votes aren't real" branch is unreachable behind that wrapper.
- **Reporting** (`/report/post`, `/report/comment`): a permanently suspended user's post report is stored but doesn't mark the post reported; their comment report is silently dropped (as is a shadowbanned user's). Temporarily suspended users report normally.
- **Admin actions by a suspended admin**: nothing checks suspension on admin routes.
- **Notifications a suspended user causes**: unfollowing and removing a follower still notify the other user (allowed by the current rule; confirm).
- **Messaging** (`/@<username>/message`, `/reply`): refused only when permanently suspended. Belongs to the messages area.
- **Chat** (outside the spec): the page and `can_access_chat` refuse only permanent suspensions, while sending and reading messages over the socket refuse on raw `is_banned`, so any temporary ban, even one that ran out, blocks them until the lazy unban runs.
- **API keys and apps** (`/api_keys`, `/edit_app`): refused only when permanently suspended.
- **Lazy unban**: an expired temporary ban is cleared (with a "You have been unbanned!" notification and `ban_evade` reset) only when the user loads the front page; until then raw-`is_banned` checks still treat them as banned. (Ban-evasion detection at login counts only permanent bans.)
- **Templates**: the mobile comment admin menu chooses Ban/Unban on raw `is_banned`; every other menu uses `is_suspended`.
