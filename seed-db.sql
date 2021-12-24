insert into public.award_relationships(id,user_id,kind) values(1,1,'shit');

INSERT INTO public.users (
	id, username, passhash, created_utc, admin_level, over_18, is_activated, bio, bio_html, login_nonce, is_private,
	unban_utc, original_username, customtitle, defaultsorting, defaultsortingcomments, defaulttime, namecolor, titlecolor, profileurl, bannerurl,
	customtitleplain, theme, themecolor, changelogsub, oldreddit, css, profilecss, coins, agendaposter, suicide_utc,
	post_count, comment_count, background, verified, truecoins
) VALUES (1, 'Drama', '', 0, 0, true, true, '', '', 0, false, 
			0, 'Drama', '', 'hot', 'top', 'day', 'ff66ac', 'ff66ac', '', '',
			'', 'dark', 'ff66ac', false, false, '', '', 0, false, 0, 
			0, 0, '', true, 0),
		 (2, 'AutoJanny', '', 0, 0, true, true, '', '', 0, false, 
			0, 'AutoJanny', '', 'hot', 'top', 'day', 'ff66ac', 'ff66ac', '', '',
			'', 'dark', 'ff66ac', false, false, '', '', 0, false, 0, 
			0, 0, '', true, 0),
		 (3, 'Snappy', '', 0, 0, true, true, '', '', 0, false, 
			0, 'Snappy', '', 'hot', 'top', 'day', '62ca56', 'e4432d', '', '',
			'', 'dark', '30409f', false, false, '', '', 0, false, 0, 
			0, 0, '', true, 0),
		 (4, 'longpostbot', '', 0, 0, true, true, '', '', 0, false, 
			0, 'longpostbot', '', 'hot', 'top', 'day', '62ca56', 'e4432d', '', '',
			'', 'dark', '30409f', false, false, '', '', 0, false, 0, 
			0, 0, '', true, 0),
		 (5, 'zozbot', '', 0, 0, true, true, '', '', 0, false, 
			0, 'zozbot', '', 'hot', 'top', 'day', '62ca56', 'e4432d', '', '',
			'', 'dark', '30409f', false, false, '', '', 0, false, 0, 
			0, 0, '', true, 0),
		 (6, 'AutoPoller', '', 0, 0, true, true, '', '', 0, false, 
			0, 'AutoPoller', '', 'hot', 'top', 'day', '62ca56', 'e4432d', '', '',
			'', 'dark', '30409f', false, false, '', '', 0, false, 0, 
			0, 0, '', true, 0);
		 (7, 'AutoBetter', '', 0, 0, true, true, '', '', 0, false, 
			0, 'AutoBetter', '', 'hot', 'top', 'day', '62ca56', 'e4432d', '', '',
			'', 'dark', '30409f', false, false, '', '', 0, false, 0, 
			0, 0, '', true, 0);

SELECT pg_catalog.setval('public.users_id_seq', 7, true);