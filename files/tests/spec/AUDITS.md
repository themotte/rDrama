# Open behavior audits

Behaviors the spec has not yet decided on purpose. Each needs a decision from the site owner, then tests pinning it (and fixes where the decision differs from today).

## Suspension

Decided and pinned in `users/test_suspended.py`: while suspended (permanently, or until `unban_utc`), a user can't change anything other users see (their content, their public profile, following). Deleting own content, saving, subscribing, unfollowing, removing followers, blocking and private preferences still work.

Decided and pinned in `votes/test_vote.py`: voting is refused only while permanently suspended; temporarily suspended users vote normally.

Decided and pinned in `notifications/test_messages.py` and `notifications/test_replies.py`: while suspended (temporarily or permanently), a user can't send messages or reply in conversations, except in modmail threads they started, so they can appeal; the contact form stays open. A suspended admin can't answer other users' modmail.

Decided and pinned in `api/test_requests.py` and `api/test_owner.py`: while suspended (temporarily or permanently), a user can't request API apps or edit theirs, whose names and descriptions others see; deleting their apps, re-keying them, authorizing apps and withdrawing authorizations still work.

Decided and pinned in `reporting/test_reports.py`: reports by permanently suspended (or shadowbanned) users are stored but never bring the item to the moderators, posts and comments alike, nor make a comment one volunteers are given; temporarily suspended users report normally.

Decided and pinned in `users/test_ban_expiry.py`: a temporary ban that ran out ends (with a "You have been unbanned!" notification and `ban_evade` reset) on the user's next request to any page, not only the front page.

Not yet audited. The app today has three different notions of "banned", and the routes below pick among them inconsistently:
- `is_suspended`: banned and the ban hasn't run out;
- `is_suspended_permanently`: banned with no end time;
- raw `is_banned`: set, even after a temporary ban ran out, until the user's next request ends it.

What to decide, case by case:
- **Admin actions by a suspended admin**: nothing checks suspension on admin routes.
- **Notifications a suspended user causes**: unfollowing and removing a follower still notify the other user (allowed by the current rule; confirm).
- **Chat** (outside the spec): the page and `can_access_chat` refuse only permanent suspensions, while sending and reading messages over the socket refuse on raw `is_banned`, so any temporary ban, even one that ran out, blocks them until the user's next page request ends it.
- **Ban evasion**: detection at login counts only permanent bans.
- **Templates**: the mobile comment admin menu chooses Ban/Unban on raw `is_banned`; every other menu uses `is_suspended`.
