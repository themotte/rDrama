INSERT INTO public.users
    (id, username, passhash, 
        created_utc, admin_level, over_18, is_activated, is_banned,
        is_private, login_nonce, dramacoins, original_username, bio, 
        defaultsorting, defaultsortingcomments, namecolor, titlecolor, theme, themecolor)
VALUES 
-- admin:admin
    (1, 'admin', 'pbkdf2:sha256:150000$z6kifBOp$1ee4ab0b1d565d541715d128d4d00dee2800f157ac3865546efed28bbb726dac', 
        0, 6, false, true, 0,
        false, 0, 0, 'admin', '',
        'hot', 'top', 'ff66ac', 'ff66ac', 'dark', 'ff66ac');

INSERT INTO public.users
    (id, username, passhash, 
        created_utc, admin_level, over_18, is_activated, is_banned,
        is_private, login_nonce, dramacoins, original_username, bio, 
        defaultsorting, defaultsortingcomments, namecolor, titlecolor, theme, themecolor)
VALUES 
-- user:user
    (2, 'user', 'pbkdf2:sha256:150000$gB7i3Vsj$7e78baba3b3eb8030bef8850f7016369221152488b27b50f48432bd7713a7e31', 
        0, 0, false, true, 0,
        false, 0, 0, 'user', '',
        'hot', 'top', 'ff66ac', 'ff66ac', 'dark', 'ff66ac');

INSERT INTO public.badge_defs VALUES (6, 'Beta User', 'Joined Drama during open beta', 'beta.png', 4, 3, NULL);

SELECT pg_catalog.setval('public.users_id_seq', 2, true);
