INSERT INTO public.users
    (id, username, passhash, 
        created_utc, admin_level, over_18, is_activated, is_banned, is_private, login_nonce,
        defaultsorting, defaultsortingcomments, namecolor, titlecolor, theme, themecolor, 
        dramacoins, original_username)
VALUES 
-- admin:admin
    (1, 'admin', 'pbkdf2:sha256:150000$z6kifBOp$1ee4ab0b1d565d541715d128d4d00dee2800f157ac3865546efed28bbb726dac', 
        0, 6, false, false, 0, false, 0, 
        'hot', 'top', 'ff66ac', 'ff66ac', 'dark', 'ff66ac', 
        0, 'admin');

INSERT INTO public.badge_defs VALUES (6, 'Beta User', 'Joined Drama during open beta', 'beta.png', 4, 3, NULL);
