INSERT INTO public.badge_defs VALUES (12, 'Gold Recruiter', 'Recruited 100 friends to join Drama', 'recruit-100.gif', 1, 1, 'v.referral_count>=100 and v.referral_count <=999');
INSERT INTO public.badge_defs VALUES (11, 'Silver Recruiter', 'Recruited 10 friends to join Drama', 'recruit-10.gif', 1, 1, 'v.referral_count>=10 and v.referral_count <= 99');
INSERT INTO public.badge_defs VALUES (10, 'Bronze Recruiter', 'Recruited 1 friend to join Drama', 'recruit-1.gif', 1, 1, 'v.referral_count>=1 and v.referral_count<9');
INSERT INTO public.badge_defs VALUES (58, 'Diamond Recruiter', 'Recruited 1000 friends to join Drama', 'recruit-1000.gif', 1, 1, 'v.referral_count >= 1000');
INSERT INTO public.badge_defs VALUES (25, 'Footpig', 'Contributed at least $100/month', 'patron-5.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (61, 'Lab Rat', 'Helped test features in development', 'labrat.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (63, 'Balls', 'I wrote carp on my balls as a sign of submission', 'carpballs.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (4, 'White Hat', 'Responsibly reported a security issue', 'whitehat.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (2, 'Verified Email', 'Verified Email', 'mail.gif', 1, 1, NULL);
INSERT INTO public.badge_defs VALUES (6, 'Beta User', 'Joined during open beta', 'beta.gif', 4, 1, NULL);
INSERT INTO public.badge_defs VALUES (15, 'Idea Maker', 'Had a good idea for Drama which was implemented by the developers', 'idea.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (3, 'Code Contributor', 'Contributed to Drama source code', 'git.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (1, 'Alpha User', 'Joined during open alpha', 'alpha.gif', 4, 1, NULL);
INSERT INTO public.badge_defs VALUES (18, 'Artisan', 'Contributed to Drama artwork', 'art.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (27, 'Lolcow', 'Beautiful and valid milk provider', 'lolcow.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (21, 'Paypig', 'Contributed at least $5/month', 'patron-1.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (22, 'Renthog', 'Contributed at least $10/month', 'patron-2.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (23, 'Landchad', 'Contributed at least $20/month', 'patron-3.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (24, 'Terminally online turboautist', 'Contributed at least $50/month', 'patron-4.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (28, 'Rich Bich', 'Contributed $500', 'patron-8.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (7, 'Bug Finder', 'Found a bug', 'sitebreaker.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (60, 'Unironically Retarded', 'Demonstrated a wholesale inability to read the room', 'retarded.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (26, 'Agendaposter', 'Forced to use the agendaposter theme', 'agendaposter.gif', 1, 1, NULL);
INSERT INTO public.badge_defs VALUES (17, 'Marsey Artisan', 'Contributed a Marsey emoji ✨', 'marseybadge-1.gif', 3, 1, NULL);
INSERT INTO public.badge_defs VALUES (16, 'Marsey Master', 'Contributed 10 (or more!!!!) Marsey emojis ✨', 'marseybadge-2.gif', 3, 1, NULL);

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
			0, 0, '', true, 0);


SELECT pg_catalog.setval('public.users_id_seq', 5, true);