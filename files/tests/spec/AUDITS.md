# Open behavior audits

Behaviors the spec has not yet decided on purpose. Each needs a decision from the site owner, then tests pinning it (and fixes where the decision differs from today).

## Suspension

Decided and pinned in `users/test_suspended.py`: while suspended (permanently, or until `unban_utc`), a user can't change anything other users see (their content, their public profile, following). Deleting own content, saving, subscribing, unfollowing, removing followers, blocking and private preferences still work.

Decided and pinned in `votes/test_vote.py`: voting is refused only while permanently suspended; temporarily suspended users vote normally.

Decided and pinned in `notifications/test_messages.py` and `notifications/test_replies.py`: while suspended (temporarily or permanently), a user can't send messages or reply in conversations, except in modmail threads they started, so they can appeal; the contact form stays open. A suspended admin can't answer other users' modmail.

Decided and pinned in `api/test_requests.py` and `api/test_owner.py`: while suspended (temporarily or permanently), a user can't request API apps or edit theirs, whose names and descriptions others see; deleting their apps, re-keying them, authorizing apps and withdrawing authorizations still work.

Decided and pinned in `reporting/test_reports.py`: reports by permanently suspended (or shadowbanned) users are stored but never bring the item to the moderators, posts and comments alike, nor make a comment one volunteers are given; temporarily suspended users report normally.

Decided and pinned in `volunteer/test_duty.py` and `volunteer/test_ratings.py`: suspended users (temporarily or permanently) and shadowbanned users are given no volunteer duty, and suspended users can't rate comments they were given before; a shadowbanned user's ratings are stored but count for nothing.

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

## The nightly volunteer recalc

Pinned as they are in `volunteer/test_nightly_recalc.py`, not decided on purpose: a comment the moderators removed still teaches the volunteers who rated it (only comments their author deleted are left out); a distinguished reply counts toward the moderators' verdict even after it was deleted; a suspended volunteer's ratings still count; a comment whose author was shadowbanned since still teaches, though it's no longer given out to rate. Ratings stored before rating rules the site enforces now (an hour from the assignment, and none once a moderator's distinguished reply is in) still count. Admins weigh a fixed 4 in the estimates that score volunteers, but by their accuracy, like anyone, in a comment's badness.

## Notices

Pinned as they are in `notifications/test_notices.py`, not decided on purpose: a notice reused by its text keeps the rendering it was first stored with, so a mention in it goes on linking the user it named then (a username given up and taken by someone else keeps linking the earlier user); notices stored before notices carried their text are never reused, so a user who already had one gets it again, once, the next time it's sent.

## Rendering

Pinned as they are in `rendering/test_text.py`, not decided on purpose: the address rewrites apply to the whole rendering, so prose naming "nitter.net" reads "twitter.com" and becomes a link; an address with another scheme, such as ftp://, keeps its scheme as text and links the rest with http://; mail addresses aren't linked. Raw HTML that HTML doesn't allow where it stands, such as text directly inside a table, may lose that text.

Also pinned there as they are, not decided on purpose: a dropped element's text runs on into its neighbours' (`<details><summary>a</summary>b</details>` reads "ab"), except around some block elements such as `<dl>`, which leave a line break; a table's `<caption>` text moves before the table and its `<tfoot>` rows into another `<tbody>`; an image's alt text is lost, and the text of a `<script>`, `<style>` or `<textarea>` shows as text; relative addresses other than those starting with "/" (`foo`, `#f`, `?q`) count as leaving the site; the rewrites that name "https://" leave http:// addresses alone, "https://www.youtube.com/shorts/x" keeps "/shorts/" because that rule comes before "www." is dropped, and a host that merely ends in a rewritten name (xnitter.net) is rewritten too.
