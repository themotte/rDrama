INSERT INTO public.boards 
    (id, name, has_banner, has_profile, 
        created_utc, profile_nonce, banner_nonce)
VALUES 
    (1, 'main', false, false, 
        0, 0, 0);

INSERT INTO public.users
    (id, username, passhash, 
        created_utc, admin_level, has_banner, over_18, creation_ip, hide_offensive, is_activated, is_banned,
        is_nsfw, is_private, karma, comment_karma, is_deleted, filter_nsfw,
        profile_nonce, banner_nonce, login_nonce,
        defaultsorting, defaultsortingcomments, namecolor, titlecolor, theme, themecolor)
VALUES 
-- admin:admin
    (1, 'admin', 'pbkdf2:sha256:150000$z6kifBOp$1ee4ab0b1d565d541715d128d4d00dee2800f157ac3865546efed28bbb726dac', 
        0, 6, false, false, '127.0.0.1', false, true, 0,
        false, false, 0, 0, false, false,
        0, 0, 0, 
        'hot', 'top', 'ff66ac', 'ff66ac', 'dark', 'ff66ac');

INSERT INTO public.badge_defs VALUES (6, 'Beta User', 'Joined Drama during open beta', 'beta.png', 4, 3, NULL);
