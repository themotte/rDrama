INSERT INTO public.users (username, passhash, created_utc, admin_level, over_18, is_activated, bio, bio_html, login_nonce, is_private,
	unban_utc, original_username, customtitle, defaultsorting, defaultsortingcomments, defaulttime, namecolor, titlecolor,
	customtitleplain, theme, themecolor, changelogsub, reddit, css, profilecss, coins, agendaposter,
	post_count, comment_count, background, verified, truecoins, cardview
) VALUES ('System', '', extract(epoch from now()), 0, true, true, '', '', 0, false, 
			0, 'System', '', 'hot', 'top', 'day', 'ff66ac', 'ff66ac',
			'', 'dark', 'ff66ac', false, 'old.reddit.com', '', '', 0, 0,
			0, 0, '', 'Verified', 0, false),
		 ('AutoJanny', '', extract(epoch from now()), 0, true, true, '', '', 0, false, 
			0, 'AutoJanny', '', 'hot', 'top', 'day', 'ff66ac', 'ff66ac',
			'', 'dark', 'ff66ac', false, 'old.reddit.com', '', '', 0, 0,
			0, 0, '', 'Verified', 0, false),
		 ('Snappy', '', extract(epoch from now()), 0, true, true, '', '', 0, false, 
			0, 'Snappy', '', 'hot', 'top', 'day', '62ca56', 'e4432d',
			'', 'dark', '30409f', false, 'old.reddit.com', '', '', 0, 0,
			0, 0, '', 'Verified', 0, false),
		 ('longpostbot', '', extract(epoch from now()), 0, true, true, '', '', 0, false, 
			0, 'longpostbot', '', 'hot', 'top', 'day', '62ca56', 'e4432d',
			'', 'dark', '30409f', false, 'old.reddit.com', '', '', 0, 0,
			0, 0, '', 'Verified', 0, false),
		 ('zozbot', '', extract(epoch from now()), 0, true, true, '', '', 0, false, 
			0, 'zozbot', '', 'hot', 'top', 'day', '62ca56', 'e4432d',
			'', 'dark', '30409f', false, 'old.reddit.com', '', '', 0, 0,
			0, 0, '', 'Verified', 0, false),
		 ('AutoPoller', '', extract(epoch from now()), 0, true, true, '', '', 0, false, 
			0, 'AutoPoller', '', 'hot', 'top', 'day', '62ca56', 'e4432d',
			'', 'dark', '30409f', false, 'old.reddit.com', '', '', 0, 0,
			0, 0, '', 'Verified', 0, false),
		 ('AutoBetter', '', extract(epoch from now()), 0, true, true, '', '', 0, false, 
			0, 'AutoBetter', '', 'hot', 'top', 'day', '62ca56', 'e4432d',
			'', 'dark', '30409f', false, 'old.reddit.com', '', '', 0, 0,
			0, 0, '', 'Verified', 0, false),
		 ('AutoChoice', '', extract(epoch from now()), 0, true, true, '', '', 0, false, 
			0, 'AutoChoice', '', 'hot', 'top', 'day', '62ca56', 'e4432d',
			'', 'dark', '30409f', false, 'old.reddit.com', '', '', 0, 0,
			0, 0, '', 'Verified', 0, false);

INSERT INTO public.badge_defs VALUES
(1,'Alpha User','Joined during open alpha'),
(2,'Verified Email','Verified Email'),
(3,'Code Contributor','Contributed to the site''s source code'),
(4,'White Hat','Responsibly reported a security issue'),
(6,'Beta User','Joined during open beta'),
(7,'Bug Chaser','Found a bug'),
(10,'Bronze Recruiter','Recruited 1 friend to join the site'),
(11,'Silver Recruiter','Recruited 10 friends to join the site'),
(12,'Gold Recruiter','Recruited 100 friends to join the site'),
(15,'Idea Maker','Had a good idea for the site which was implemented by the developers'),
(18,'Artisan','Contributed to site artwork'),
(21,'Patron I','Contributed at least $5'),
(22,'Patron II','Contributed at least $10'),
(23,'Patron III','Contributed at least $20'),
(24,'Patron IV','Contributed at least $50'),
(25,'Patron V','Contributed at least $100'),
(26,'Patron VI','Contributed at least $250'),
(27,'Patron VII','Contributed at least $500');
