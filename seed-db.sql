INSERT INTO public.badge_defs VALUES (6, 'Beta User', 'Joined during open beta', 'beta.gif', 3, NULL);

INSERT INTO public.users (
    id, username, passhash, created_utc, admin_level, over_18, is_activated, bio, bio_html, login_nonce, is_private,
    unban_utc, original_username, customtitle, defaultsorting, defaulttime, namecolor, titlecolor, profileurl, bannerurl,
    customtitleplain, themecolor, changelogsub, oldreddit, css, profilecss, coins, agendaposter, suicide_utc,
    post_count, comment_count, background, verified 
) VALUES (1, 'Drama', '', 0, 0, true, true, '', '', 0, false, 
            0, 'Drama', '', 'hot', 'day', 'ff66ac', 'ff66ac', '', '',
            '', 'ff66ac', false, false, '', '', 0, false, 0, 
            0, 0, '', true);

insert into public.award_relationships(id,user_id,kind) values(1,1,'shit');

INSERT INTO public.users (
    id, username, passhash, created_utc, admin_level, over_18, is_activated, bio, bio_html, login_nonce, is_private,
    unban_utc, original_username, customtitle, defaultsorting, defaulttime, namecolor, titlecolor, profileurl, bannerurl,
    customtitleplain, themecolor, changelogsub, oldreddit, css, profilecss, coins, agendaposter, suicide_utc,
    post_count, comment_count, background, verified 
) VALUES (2, 'AutoJanny', '', 0, 0, true, true, '', '', 0, false, 
            0, 'AutoJanny', '', 'hot', 'day', 'ff66ac', 'ff66ac', '', '',
            '', 'ff66ac', false, false, '', '', 0, false, 0, 
            0, 0, '', true);

INSERT INTO public.users (
    id, username, passhash, created_utc, admin_level, over_18, is_activated, bio, bio_html, login_nonce, is_private,
    unban_utc, original_username, customtitle, defaultsorting, defaulttime, namecolor, titlecolor, profileurl, bannerurl,
    customtitleplain, themecolor, changelogsub, oldreddit, css, profilecss, coins, agendaposter, suicide_utc,
    post_count, comment_count, background, verified 
) VALUES (3, 'Snappy', '', 0, 0, true, true, '', '', 0, false, 
            0, 'Snappy', '', 'hot', 'day', '62ca56', 'e4432d', '', '',
            '', '30409f', false, false, '', '', 0, false, 0, 
            0, 0, '', true);

INSERT INTO public.users (
    id, username, passhash, created_utc, admin_level, over_18, is_activated, bio, bio_html, login_nonce, is_private,
    unban_utc, original_username, customtitle, defaultsorting, defaulttime, namecolor, titlecolor, profileurl, bannerurl,
    customtitleplain, themecolor, changelogsub, oldreddit, css, profilecss, coins, agendaposter, suicide_utc,
    post_count, comment_count, background, verified 
) VALUES (4, 'longpostbot', '', 0, 0, true, true, '', '', 0, false, 
            0, 'longpostbot', '', 'hot', 'day', '62ca56', 'e4432d', '', '',
            '', '30409f', false, false, '', '', 0, false, 0, 
            0, 0, '', true);

INSERT INTO public.users (
    id, username, passhash, created_utc, admin_level, over_18, is_activated, bio, bio_html, login_nonce, is_private,
    unban_utc, original_username, customtitle, defaultsorting, defaulttime, namecolor, titlecolor, profileurl, bannerurl,
    customtitleplain, themecolor, changelogsub, oldreddit, css, profilecss, coins, agendaposter, suicide_utc,
    post_count, comment_count, background, verified 
) VALUES (5, 'zozbot', '', 0, 0, true, true, '', '', 0, false, 
            0, 'zozbot', '', 'hot', 'day', '62ca56', 'e4432d', '', '',
            '', '30409f', false, false, '', '', 0, false, 0, 
            0, 0, '', true);


SELECT pg_catalog.setval('public.users_id_seq', 5, true);