--
-- PostgreSQL database dump
--

-- Dumped from database version 12.7 (Ubuntu 12.7-0ubuntu0.20.04.1)
-- Dumped by pg_dump version 12.7 (Ubuntu 12.7-0ubuntu0.20.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE ONLY public.users DROP CONSTRAINT users_title_fkey;
ALTER TABLE ONLY public.reports DROP CONSTRAINT reports_post_id_fkey;
ALTER TABLE ONLY public.postrels DROP CONSTRAINT postrels_post_id_fkey;
ALTER TABLE ONLY public.notifications DROP CONSTRAINT notifications_comment_id_fkey;
ALTER TABLE ONLY public.flags DROP CONSTRAINT flags_post_id_fkey;
ALTER TABLE ONLY public.commentflags DROP CONSTRAINT commentflags_comment_id_fkey;
ALTER TABLE ONLY public.badges DROP CONSTRAINT badges_badge_id_fkey;
DROP INDEX public.votes_type_index;
DROP INDEX public.votes_submission_id_index;
DROP INDEX public.vote_user_index;
DROP INDEX public.vote_created_idx;
DROP INDEX public.users_username_trgm_idx;
DROP INDEX public.users_unbanutc_idx;
DROP INDEX public.users_title_idx;
DROP INDEX public.users_subs_idx;
DROP INDEX public.users_premium_idx;
DROP INDEX public.users_premium_expire_utc_idx;
DROP INDEX public.users_original_username_trgm_idx;
DROP INDEX public.users_neg_idx;
DROP INDEX public.users_karma_idx;
DROP INDEX public.users_created_utc_index;
DROP INDEX public.users_coin_idx;
DROP INDEX public.userblocks_both_idx;
DROP INDEX public.user_private_idx;
DROP INDEX public.user_privacy_idx;
DROP INDEX public.user_ip_idx;
DROP INDEX public.user_del_idx;
DROP INDEX public.user_creation_ip_idx;
DROP INDEX public.user_banned_idx;
DROP INDEX public.trending_all_idx;
DROP INDEX public.subscription_user_index;
DROP INDEX public.subscription_board_index;
DROP INDEX public.submissions_title_trgm_idx;
DROP INDEX public.submissions_sticky_index;
DROP INDEX public.submissions_score_idx;
DROP INDEX public.submissions_over18_index;
DROP INDEX public.submissions_offensive_index;
DROP INDEX public.submissions_created_utc_desc_idx;
DROP INDEX public.submissions_aux_title_idx;
DROP INDEX public.submissions_aux_id_idx;
DROP INDEX public.submissions_author_index;
DROP INDEX public.submission_purge_idx;
DROP INDEX public.submission_pinned_idx;
DROP INDEX public.submission_original_board_id_idx;
DROP INDEX public.submission_new_sort_idx;
DROP INDEX public.submission_isdeleted_idx;
DROP INDEX public.submission_isbanned_idx;
DROP INDEX public.submission_ip_idx;
DROP INDEX public.submission_hot_sort_idx;
DROP INDEX public.submission_domainref_index;
DROP INDEX public.submission_disputed_sort_idx;
DROP INDEX public.submission_best_only_idx;
DROP INDEX public.submission_aux_url_trgm_idx;
DROP INDEX public.submission_aux_url_idx;
DROP INDEX public.subimssion_binary_group_idx;
DROP INDEX public.sub_user_index;
DROP INDEX public.sub_active_index;
DROP INDEX public.reports_post_index;
DROP INDEX public.promocode_code_idx;
DROP INDEX public.promocode_active_idx;
DROP INDEX public.post_public_idx;
DROP INDEX public.post_offensive_index;
DROP INDEX public.post_author_index;
DROP INDEX public.post_app_id_idx;
DROP INDEX public.post_18_index;
DROP INDEX public.paypaltxn_status_idx;
DROP INDEX public.paypal_txn_user_id_idx;
DROP INDEX public.paypal_txn_paypalid_idx;
DROP INDEX public.paypal_txn_created_idx;
DROP INDEX public.notifs_user_read_idx;
DROP INDEX public.notifications_user_index;
DROP INDEX public.notifications_comment_idx;
DROP INDEX public.notification_read_idx;
DROP INDEX public.modaction_pid_idx;
DROP INDEX public.modaction_id_idx;
DROP INDEX public.modaction_cid_idx;
DROP INDEX public.modaction_action_idx;
DROP INDEX public.message_user_idx;
DROP INDEX public.ips_until_idx;
DROP INDEX public.follow_user_id_index;
DROP INDEX public.follow_target_id_index;
DROP INDEX public.flags_post_index;
DROP INDEX public.flag_user_idx;
DROP INDEX public.domains_domain_trgm_idx;
DROP INDEX public.domain_ref_idx;
DROP INDEX public.discord_id_idx;
DROP INDEX public.cvote_user_index;
DROP INDEX public.cvote_created_idx;
DROP INDEX public.contributors_user_index;
DROP INDEX public.contributors_board_index;
DROP INDEX public.contrib_board_index;
DROP INDEX public.contrib_active_index;
DROP INDEX public.commentvotes_comments_type_index;
DROP INDEX public.commentvotes_comments_id_index;
DROP INDEX public.commentsaux_body_idx;
DROP INDEX public.comments_user_index;
DROP INDEX public.comments_score_top_idx;
DROP INDEX public.comments_score_hot_idx;
DROP INDEX public.comments_score_disputed_idx;
DROP INDEX public.comments_parent_id_idx;
DROP INDEX public.comments_original_board_id_idx;
DROP INDEX public.comments_loader_idx;
DROP INDEX public.comments_aux_id_idx;
DROP INDEX public.commentflag_comment_index;
DROP INDEX public.comment_purge_idx;
DROP INDEX public.comment_post_id_index;
DROP INDEX public.comment_parent_index;
DROP INDEX public.comment_ip_idx;
DROP INDEX public.comment_body_trgm_idx;
DROP INDEX public.comment_body_idx;
DROP INDEX public.client_refresh_token_idx;
DROP INDEX public.client_access_token_idx;
DROP INDEX public.cflag_user_idx;
DROP INDEX public.block_user_idx;
DROP INDEX public.block_target_idx;
DROP INDEX public.badpics_phash_index;
DROP INDEX public.badpic_phash_trgm_idx;
DROP INDEX public.badpic_phash_idx;
DROP INDEX public.badlink_link_idx;
DROP INDEX public.badges_user_index;
DROP INDEX public.badges_badge_id_idx;
DROP INDEX public.badgedef_qual_idx;
DROP INDEX public.award_user_idx;
DROP INDEX public.award_post_idx;
DROP INDEX public.award_comment_idx;
DROP INDEX public.alts_user2_idx;
DROP INDEX public.alts_user1_idx;
ALTER TABLE ONLY public.votes DROP CONSTRAINT votes_pkey;
ALTER TABLE ONLY public.viewers DROP CONSTRAINT viewers_pkey;
ALTER TABLE ONLY public.users DROP CONSTRAINT users_username_key;
ALTER TABLE ONLY public.users DROP CONSTRAINT users_pkey;
ALTER TABLE ONLY public.users DROP CONSTRAINT users_original_username_key;
ALTER TABLE ONLY public.users DROP CONSTRAINT users_email_key;
ALTER TABLE ONLY public.alts DROP CONSTRAINT userpair;
ALTER TABLE ONLY public.userflags DROP CONSTRAINT userflags_pkey;
ALTER TABLE ONLY public.userblocks DROP CONSTRAINT userblocks_pkey;
ALTER TABLE ONLY public.useragents DROP CONSTRAINT useragents_pkey;
ALTER TABLE ONLY public.useragents DROP CONSTRAINT useragents_kwd_key;
ALTER TABLE ONLY public.badges DROP CONSTRAINT user_badge_constraint;
ALTER TABLE ONLY public.oauth_apps DROP CONSTRAINT unique_secret;
ALTER TABLE ONLY public.client_auths DROP CONSTRAINT unique_refresh;
ALTER TABLE ONLY public.paypal_txns DROP CONSTRAINT unique_paypalid;
ALTER TABLE ONLY public.oauth_apps DROP CONSTRAINT unique_id;
ALTER TABLE ONLY public.client_auths DROP CONSTRAINT unique_code;
ALTER TABLE ONLY public.client_auths DROP CONSTRAINT unique_access;
ALTER TABLE ONLY public.titles DROP CONSTRAINT titles_pkey;
ALTER TABLE ONLY public.subscriptions DROP CONSTRAINT subscriptions_pkey;
ALTER TABLE ONLY public.submissions DROP CONSTRAINT submissions_pkey;
ALTER TABLE ONLY public.submissions_aux DROP CONSTRAINT submissions_aux_pkey;
ALTER TABLE ONLY public.save_relationship DROP CONSTRAINT save_relationship_pkey;
ALTER TABLE ONLY public.save_relationship DROP CONSTRAINT save_constraint;
ALTER TABLE ONLY public.reports DROP CONSTRAINT reports_pkey;
ALTER TABLE ONLY public.promocodes DROP CONSTRAINT promocodes_pkey;
ALTER TABLE ONLY public.postrels DROP CONSTRAINT postrels_pkey;
ALTER TABLE ONLY public.postrels DROP CONSTRAINT postrel_unique;
ALTER TABLE ONLY public.paypal_txns DROP CONSTRAINT paypal_txns_pkey;
ALTER TABLE ONLY public.votes DROP CONSTRAINT onevote;
ALTER TABLE ONLY public.commentvotes DROP CONSTRAINT onecvote;
ALTER TABLE ONLY public.notifications DROP CONSTRAINT one_notif;
ALTER TABLE ONLY public.users DROP CONSTRAINT one_discord_account;
ALTER TABLE ONLY public.oauth_apps DROP CONSTRAINT oauth_apps_pkey;
ALTER TABLE ONLY public.notifications DROP CONSTRAINT notifications_pkey;
ALTER TABLE ONLY public.modactions DROP CONSTRAINT modactions_pkey;
ALTER TABLE ONLY public.messages DROP CONSTRAINT messages_pkey;
ALTER TABLE ONLY public.message_notifications DROP CONSTRAINT message_notifications_pkey;
ALTER TABLE ONLY public.ips DROP CONSTRAINT ips_pkey;
ALTER TABLE ONLY public.ips DROP CONSTRAINT ips_addr_key;
ALTER TABLE ONLY public.images DROP CONSTRAINT images_pkey;
ALTER TABLE ONLY public.contributors DROP CONSTRAINT id_const;
ALTER TABLE ONLY public.subscriptions DROP CONSTRAINT guild_membership_unique;
ALTER TABLE ONLY public.follows DROP CONSTRAINT follows_pkey;
ALTER TABLE ONLY public.follows DROP CONSTRAINT follow_membership_unique;
ALTER TABLE ONLY public.flags DROP CONSTRAINT flags_pkey;
ALTER TABLE ONLY public.domains DROP CONSTRAINT domains_pkey;
ALTER TABLE ONLY public.domains DROP CONSTRAINT domains_domain_key;
ALTER TABLE ONLY public.dms DROP CONSTRAINT dms_pkey;
ALTER TABLE ONLY public.convo_member DROP CONSTRAINT convo_member_pkey;
ALTER TABLE ONLY public.conversations DROP CONSTRAINT conversations_pkey;
ALTER TABLE ONLY public.contributors DROP CONSTRAINT contribs_unique_constraint;
ALTER TABLE ONLY public.commentvotes DROP CONSTRAINT commentvotes_pkey;
ALTER TABLE ONLY public.comments DROP CONSTRAINT comments_pkey;
ALTER TABLE ONLY public.comments_aux DROP CONSTRAINT comments_aux_pkey;
ALTER TABLE ONLY public.commentflags DROP CONSTRAINT commentflags_pkey;
ALTER TABLE ONLY public.client_auths DROP CONSTRAINT client_auths_pkey;
ALTER TABLE ONLY public.chatbans DROP CONSTRAINT chatbans_pkey;
ALTER TABLE ONLY public.badwords DROP CONSTRAINT badwords_pkey;
ALTER TABLE ONLY public.badwords DROP CONSTRAINT badwords_keyword_key;
ALTER TABLE ONLY public.badpics DROP CONSTRAINT badpics_pkey;
ALTER TABLE ONLY public.badlinks DROP CONSTRAINT badlinks_pkey;
ALTER TABLE ONLY public.badges DROP CONSTRAINT badges_pkey;
ALTER TABLE ONLY public.badge_defs DROP CONSTRAINT badge_list_icon_key;
ALTER TABLE ONLY public.badge_defs DROP CONSTRAINT badge_defs_pkey;
ALTER TABLE ONLY public.award_relationships DROP CONSTRAINT award_relationships_pkey;
ALTER TABLE ONLY public.award_relationships DROP CONSTRAINT award_post_constraint;
ALTER TABLE ONLY public.award_relationships DROP CONSTRAINT award_constraint;
ALTER TABLE ONLY public.award_relationships DROP CONSTRAINT award_comment_constraint;
ALTER TABLE ONLY public.alts DROP CONSTRAINT alts_pkey;
ALTER TABLE public.votes ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.viewers ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.userflags ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.userblocks ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.useragents ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.titles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.subscriptions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.submissions_aux ALTER COLUMN key_id DROP DEFAULT;
ALTER TABLE public.submissions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.save_relationship ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.reports ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.promocodes ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.postrels ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.paypal_txns ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.oauth_apps ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.notifications ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.modactions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.messages ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.message_notifications ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.ips ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.images ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.follows ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.flags ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.domains ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.dms ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.convo_member ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.conversations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.contributors ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.commentvotes ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.comments_aux ALTER COLUMN key_id DROP DEFAULT;
ALTER TABLE public.comments ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.commentflags ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.client_auths ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.chatbans ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.badwords ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.badpics ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.badlinks ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.badges ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.badge_defs ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.award_relationships ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.alts ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE public.votes_id_seq;
DROP TABLE public.votes;
DROP SEQUENCE public.viewers_id_seq;
DROP TABLE public.viewers;
DROP SEQUENCE public.users_id_seq;
DROP SEQUENCE public.userflags_id_seq;
DROP TABLE public.userflags;
DROP SEQUENCE public.userblocks_id_seq;
DROP TABLE public.userblocks;
DROP SEQUENCE public.useragents_id_seq;
DROP TABLE public.useragents;
DROP SEQUENCE public.titles_id_seq;
DROP TABLE public.titles;
DROP SEQUENCE public.subscriptions_id_seq;
DROP TABLE public.subscriptions;
DROP SEQUENCE public.submissions_id_seq;
DROP SEQUENCE public.submissions_aux_key_id_seq;
DROP TABLE public.submissions_aux;
DROP SEQUENCE public.save_relationship_id_seq;
DROP TABLE public.save_relationship;
DROP SEQUENCE public.reports_id_seq;
DROP SEQUENCE public.promocodes_id_seq;
DROP TABLE public.promocodes;
DROP SEQUENCE public.postrels_id_seq;
DROP TABLE public.postrels;
DROP SEQUENCE public.paypal_txns_id_seq;
DROP TABLE public.paypal_txns;
DROP SEQUENCE public.oauth_apps_id_seq;
DROP TABLE public.oauth_apps;
DROP SEQUENCE public.notifications_id_seq;
DROP SEQUENCE public.modactions_id_seq;
DROP TABLE public.modactions;
DROP SEQUENCE public.messages_id_seq;
DROP TABLE public.messages;
DROP SEQUENCE public.message_notifications_id_seq;
DROP TABLE public.message_notifications;
DROP SEQUENCE public.ips_id_seq;
DROP TABLE public.ips;
DROP TABLE public.imgur;
DROP SEQUENCE public.images_id_seq;
DROP SEQUENCE public.follows_id_seq;
DROP TABLE public.follows;
DROP SEQUENCE public.flags_id_seq;
DROP TABLE public.flags;
DROP SEQUENCE public.domains_id_seq;
DROP TABLE public.domains;
DROP SEQUENCE public.dms_id_seq;
DROP TABLE public.dms;
DROP SEQUENCE public.convo_member_id_seq;
DROP TABLE public.convo_member;
DROP SEQUENCE public.conversations_id_seq;
DROP TABLE public.conversations;
DROP SEQUENCE public.contributors_id_seq;
DROP TABLE public.contributors;
DROP SEQUENCE public.commentvotes_id_seq;
DROP TABLE public.commentvotes;
DROP SEQUENCE public.comments_id_seq;
DROP SEQUENCE public.comments_aux_key_id_seq;
DROP TABLE public.comments_aux;
DROP SEQUENCE public.commentflags_id_seq;
DROP TABLE public.commentflags;
DROP TABLE public.cmda_exec;
DROP SEQUENCE public.client_auths_id_seq;
DROP TABLE public.client_auths;
DROP SEQUENCE public.chatbans_id_seq;
DROP TABLE public.chatbans;
DROP SEQUENCE public.badwords_id_seq;
DROP TABLE public.badwords;
DROP SEQUENCE public.badpics_id_seq;
DROP TABLE public.badpics;
DROP SEQUENCE public.badlinks_id_seq;
DROP TABLE public.badlinks;
DROP SEQUENCE public.badges_id_seq;
DROP TABLE public.badges;
DROP SEQUENCE public.badge_list_id_seq;
DROP TABLE public.badge_defs;
DROP SEQUENCE public.award_relationships_id_seq;
DROP TABLE public.award_relationships;
DROP SEQUENCE public.alts_id_seq;
DROP TABLE public.alts;
DROP TABLE public._exec;
DROP FUNCTION public.ups_test(public.submissions);
DROP FUNCTION public.ups(public.submissions);
DROP FUNCTION public.ups(public.comments);
DROP FUNCTION public.splash(text);
DROP TABLE public.images;
DROP FUNCTION public.similar_count(public.comments);
DROP FUNCTION public.score(public.submissions);
DROP FUNCTION public.score(public.comments);
DROP FUNCTION public.report_count(public.submissions);
DROP FUNCTION public.referral_count(public.users);
DROP FUNCTION public.rank_hot(public.submissions);
DROP FUNCTION public.rank_hot(public.comments);
DROP FUNCTION public.rank_fiery(public.submissions);
DROP FUNCTION public.rank_fiery(public.comments);
DROP FUNCTION public.rank_best(public.submissions);
DROP FUNCTION public.rank_activity(public.submissions);
DROP FUNCTION public.mod_count(public.users);
DROP FUNCTION public.is_deleted(public.notifications);
DROP FUNCTION public.is_banned(public.notifications);
DROP FUNCTION public.follower_count(public.users);
DROP FUNCTION public.flag_count(public.submissions);
DROP FUNCTION public.flag_count(public.comments);
DROP FUNCTION public.energy(public.users);
DROP FUNCTION public.downs(public.submissions);
DROP FUNCTION public.downs(public.comments);
DROP FUNCTION public.created_utc(public.notifications);
DROP TABLE public.notifications;
DROP FUNCTION public.comment_energy(public.users);
DROP FUNCTION public.comment_count(public.submissions);
DROP FUNCTION public.board_id(public.reports);
DROP TABLE public.reports;
DROP FUNCTION public.board_id(public.comments);
DROP FUNCTION public.age(public.users);
DROP TABLE public.users;
DROP FUNCTION public.age(public.submissions);
DROP TABLE public.submissions;
DROP FUNCTION public.age(public.comments);
DROP TABLE public.comments;
DROP EXTENSION pg_trgm;
DROP EXTENSION pg_stat_statements;
DROP EXTENSION fuzzystrmatch;
--
-- Name: fuzzystrmatch; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS fuzzystrmatch WITH SCHEMA public;


--
-- Name: EXTENSION fuzzystrmatch; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION fuzzystrmatch IS 'determine similarities and distance between strings';


--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_stat_statements IS 'track execution statistics of all SQL statements executed';


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: comments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.comments (
    id integer NOT NULL,
    author_id integer,
    created_utc integer NOT NULL,
    parent_submission integer,
    is_banned boolean,
    parent_fullname character varying(255),
    distinguish_level integer,
    edited_utc integer,
    deleted_utc integer NOT NULL,
    is_approved integer NOT NULL,
    author_name character varying(64),
    approved_utc integer,
    creation_ip character varying(64) NOT NULL,
    score_disputed double precision,
    score_hot double precision,
    score_top integer,
    level integer,
    parent_comment_id integer,
    title_id integer,
    over_18 boolean,
    is_op boolean,
    is_offensive boolean,
    is_nsfl boolean,
    original_board_id integer,
    upvotes integer,
    downvotes integer,
    is_bot boolean DEFAULT false,
    gm_distinguish integer DEFAULT 0 NOT NULL,
    is_pinned boolean DEFAULT false,
    app_id integer,
    creation_region character(2) DEFAULT NULL::bpchar,
    purged_utc integer DEFAULT 0,
    sentto integer,
    shadowbanned boolean,
    banaward text
);


ALTER TABLE public.comments OWNER TO postgres;

--
-- Name: age(public.comments); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.age(public.comments) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT CAST( EXTRACT( EPOCH FROM CURRENT_TIMESTAMP) AS int) - $1.created_utc
      $_$;


ALTER FUNCTION public.age(public.comments) OWNER TO postgres;

--
-- Name: submissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.submissions (
    id integer NOT NULL,
    author_id integer,
    created_utc integer NOT NULL,
    is_banned boolean,
    over_18 boolean,
    distinguish_level integer,
    created_str character varying(255),
    stickied boolean,
    deleted_utc integer NOT NULL,
    domain_ref integer,
    is_approved integer NOT NULL,
    approved_utc integer,
    original_board_id integer,
    edited_utc integer,
    creation_ip character varying(64) NOT NULL,
    mod_approved integer,
    is_image boolean,
    has_thumb boolean,
    accepted_utc integer,
    post_public boolean,
    score_hot double precision,
    score_top integer,
    score_activity double precision,
    score_disputed double precision,
    is_offensive boolean,
    is_pinned boolean,
    is_nsfl boolean,
    repost_id integer,
    score_best double precision,
    upvotes integer,
    downvotes integer,
    gm_distinguish integer DEFAULT 0 NOT NULL,
    app_id integer,
    creation_region character(2) DEFAULT NULL::bpchar,
    purged_utc integer DEFAULT 0,
    is_bot boolean DEFAULT false,
    thumburl text,
    private boolean,
    views integer,
    banaward text
);


ALTER TABLE public.submissions OWNER TO postgres;

--
-- Name: age(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.age(public.submissions) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT CAST( EXTRACT( EPOCH FROM CURRENT_TIMESTAMP) AS int) - $1.created_utc
      $_$;


ALTER FUNCTION public.age(public.submissions) OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(255) NOT NULL,
    email character varying(255),
    passhash character varying(255) NOT NULL,
    created_utc integer NOT NULL,
    admin_level integer,
    over_18 boolean,
    creation_ip character varying(255),
    hide_offensive boolean,
    is_activated boolean,
    bio character varying(300),
    bio_html character varying(1000),
    real_id character varying,
    referred_by integer,
    is_banned integer,
    ban_reason character varying(128),
    login_nonce integer,
    title_id integer,
    has_banner boolean NOT NULL,
    reserved character varying(256),
    is_nsfw boolean NOT NULL,
    tos_agreed_utc integer,
    profile_nonce integer NOT NULL,
    banner_nonce integer NOT NULL,
    last_siege_utc integer,
    mfa_secret character varying(32),
    has_earned_darkmode boolean,
    is_private boolean,
    read_announcement_utc integer,
    feed_nonce integer,
    show_nsfl boolean,
    karma integer,
    comment_karma integer,
    unban_utc integer,
    is_deleted boolean,
    delete_reason character varying(1000),
    is_enrolled boolean,
    filter_nsfw boolean,
    is_nofollow boolean DEFAULT false,
    coin_balance integer DEFAULT 0,
    premium_expires_utc integer DEFAULT 0,
    negative_balance_cents integer DEFAULT 0,
    custom_filter_list character varying(1000) DEFAULT ''::character varying,
    discord_id character varying(64),
    last_yank_utc integer DEFAULT 0,
    stored_karma integer DEFAULT 0,
    stored_subscriber_count integer DEFAULT 0,
    creation_region character(2) DEFAULT NULL::bpchar,
    ban_evade integer DEFAULT 0,
    profile_upload_ip character varying(255),
    banner_upload_ip character varying(255),
    profile_upload_region character(2),
    banner_upload_region character(2),
    name_last_changed_utc integer,
    banner_set_utc integer DEFAULT 0,
    profile_set_utc integer DEFAULT 0,
    original_username character varying(255),
    name_changed_utc integer DEFAULT 0,
    hide_bot boolean DEFAULT false,
    auto_join_chat boolean DEFAULT true,
    customtitle text,
    defaultsorting text,
    defaulttime text,
    namecolor text,
    titlecolor text,
    profileurl text,
    bannerurl text,
    hidevotedon boolean,
    newtab boolean,
    flairchanged boolean,
    defaultsortingcomments text,
    theme text,
    song text,
    slurreplacer boolean,
    shadowbanned boolean,
    newtabexternal boolean,
    customtitleplain text,
    themecolor text,
    changelogsub boolean,
    oldreddit boolean,
    css text,
    profilecss text,
    dramacoins integer,
    agendaposter boolean,
    agendaposter_expires_utc integer DEFAULT 0,
    resized boolean,
    banawards integer,
    patron boolean,
    animatedname boolean,
    suicide_utc integer
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: age(public.users); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.age(public.users) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT CAST( EXTRACT( EPOCH FROM CURRENT_TIMESTAMP) AS int) - $1.created_utc
      $_$;


ALTER FUNCTION public.age(public.users) OWNER TO postgres;

--
-- Name: board_id(public.comments); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.board_id(public.comments) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT submissions.board_id
      FROM submissions
      WHERE submissions.id=$1.parent_submission
      $_$;


ALTER FUNCTION public.board_id(public.comments) OWNER TO postgres;

--
-- Name: reports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reports (
    id integer NOT NULL,
    post_id integer,
    user_id integer,
    created_utc integer
);


ALTER TABLE public.reports OWNER TO postgres;

--
-- Name: board_id(public.reports); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.board_id(public.reports) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT submissions.board_id
      FROM submissions
      WHERE submissions.id=$1.post_id
      $_$;


ALTER FUNCTION public.board_id(public.reports) OWNER TO postgres;

--
-- Name: comment_count(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.comment_count(public.submissions) RETURNS bigint
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$

      SELECT COUNT(*)

      FROM comments

      WHERE is_banned=false

        AND deleted_utc=0

        AND parent_submission = $1.id

        AND shadowbanned = false

      $_$;


ALTER FUNCTION public.comment_count(public.submissions) OWNER TO postgres;

--
-- Name: comment_energy(public.users); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.comment_energy(public.users) RETURNS bigint
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
     SELECT COALESCE(
     (
      SELECT SUM(comments.score_top)
      FROM comments
      WHERE comments.author_id=$1.id
        AND comments.is_banned=false
        and comments.parent_submission is not null
      ),
      0
      )
    $_$;


ALTER FUNCTION public.comment_energy(public.users) OWNER TO postgres;

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id integer,
    comment_id integer,
    read boolean NOT NULL,
    followsender integer,
    unfollowsender integer,
    blocksender integer,
    unblocksender integer
);


ALTER TABLE public.notifications OWNER TO postgres;

--
-- Name: created_utc(public.notifications); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.created_utc(public.notifications) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
select created_utc from comments
where comments.id=$1.comment_id
$_$;


ALTER FUNCTION public.created_utc(public.notifications) OWNER TO postgres;

--
-- Name: downs(public.comments); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.downs(public.comments) RETURNS bigint
    LANGUAGE sql
    AS $_$

select (

(

  SELECT count(*)

  from (

    select * from commentvotes

    where comment_id=$1.id

    and vote_type=-1

  ) as v1

   join (select * from users where users.is_banned=0 or users.unban_utc>0

) as u0

    on u0.id=v1.user_id

)-(

  SELECT count(distinct v1.id)

  from (

    select * from commentvotes

    where comment_id=$1.id

    and vote_type=-1


  ) as v1

   join (select * from users where is_banned=0 or users.unban_utc>0) as u1

    on u1.id=v1.user_id

   join (select * from alts) as a

    on (a.user1=v1.user_id or a.user2=v1.user_id)

   join (

      select * from commentvotes

      where comment_id=$1.id

      and vote_type=-1


  ) as v2

    on ((a.user1=v2.user_id or a.user2=v2.user_id) and v2.id != v1.id)

   join (select * from users where is_banned=0 or users.unban_utc>0) as u2

    on u2.id=v2.user_id

  where v1.id is not null

  and v2.id is not null

))

     $_$;


ALTER FUNCTION public.downs(public.comments) OWNER TO postgres;

--
-- Name: downs(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.downs(public.submissions) RETURNS bigint
    LANGUAGE sql
    AS $_$

select (

(

  SELECT count(*)

  from (

    select * from votes

    where submission_id=$1.id

    and vote_type=-1


  ) as v1

   join (select * from users where users.is_banned=0 or users.unban_utc>0) as u0

    on u0.id=v1.user_id

)-(

  SELECT count(distinct v1.id)

  from (

    select * from votes

    where submission_id=$1.id

    and vote_type=-1

  ) as v1

   join (select * from users where is_banned=0 or users.unban_utc>0) as u1

    on u1.id=v1.user_id

   join (select * from alts) as a

    on (a.user1=v1.user_id or a.user2=v1.user_id)

   join (

      select * from votes

      where submission_id=$1.id

      and vote_type=-1


  ) as v2

    on ((a.user1=v2.user_id or a.user2=v2.user_id) and v2.id != v1.id)

   join (select * from users where is_banned=0 or users.unban_utc>0) as u2

    on u2.id=v2.user_id

  where v1.id is not null

  and v2.id is not null

))

     $_$;


ALTER FUNCTION public.downs(public.submissions) OWNER TO postgres;

--
-- Name: energy(public.users); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.energy(public.users) RETURNS bigint
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
     SELECT COALESCE(
     (
      SELECT SUM(submissions.score_top)
      FROM submissions
      WHERE submissions.author_id=$1.id
        AND submissions.is_banned=false
      ),
      0
      )
    $_$;


ALTER FUNCTION public.energy(public.users) OWNER TO postgres;

--
-- Name: flag_count(public.comments); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.flag_count(public.comments) RETURNS bigint
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT COUNT(*)
      FROM commentflags
      JOIN users ON commentflags.user_id=users.id
      WHERE comment_id=$1.id
      AND users.is_banned=0
      $_$;


ALTER FUNCTION public.flag_count(public.comments) OWNER TO postgres;

--
-- Name: flag_count(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.flag_count(public.submissions) RETURNS bigint
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT COUNT(*)
      FROM flags
      JOIN users ON flags.user_id=users.id
      WHERE post_id=$1.id
      AND users.is_banned=0
      $_$;


ALTER FUNCTION public.flag_count(public.submissions) OWNER TO postgres;

--
-- Name: follower_count(public.users); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.follower_count(public.users) RETURNS bigint
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
	select (
         (select count(*)
         from follows
         left join users
         on follows.user_id=users.id
         where follows.target_id=$1.id
         and (users.is_banned=0 or users.created_utc>0)
         and users.is_deleted=false
         )-(
	         select count(distinct f1.id)
	         	from
	         	(
	         		select *
	         		from follows
	         		where target_id=$1.id
	         	) as f1
   				join (select * from users where is_banned=0 or unban_utc>0) as u1
    			 on u1.id=f1.user_id
				join (select * from alts) as a
			     on (a.user1=f1.user_id or a.user2=f1.user_id)
			    join (
			    	select *
			    	from follows
			    	where target_id=$1.id
			    ) as f2
			    on ((a.user1=f2.user_id or a.user2=f2.user_id) and f2.id != f1.id)
			    join (select * from users where is_banned=0 or unban_utc>0) as u2
			     on u2.id=f2.user_id
			    where f1.id is not null
			    and f2.id is not null        	
	         )
         
         
         
         )
        $_$;


ALTER FUNCTION public.follower_count(public.users) OWNER TO postgres;

--
-- Name: is_banned(public.notifications); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.is_banned(public.notifications) RETURNS boolean
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
select is_banned from comments
where comments.id=$1.comment_id
$_$;


ALTER FUNCTION public.is_banned(public.notifications) OWNER TO postgres;

--
-- Name: is_deleted(public.notifications); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.is_deleted(public.notifications) RETURNS boolean
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
select is_deleted from comments
where comments.id=$1.comment_id
$_$;


ALTER FUNCTION public.is_deleted(public.notifications) OWNER TO postgres;

--
-- Name: mod_count(public.users); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.mod_count(public.users) RETURNS bigint
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$select count(*) from mods where accepted=true and invite_rescinded=false and user_id=$1.id;$_$;


ALTER FUNCTION public.mod_count(public.users) OWNER TO postgres;

--
-- Name: rank_activity(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.rank_activity(public.submissions) RETURNS double precision
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT 1000000.0*CAST($1.comment_count AS float)/((CAST(($1.age+5000) AS FLOAT)/100.0)^(1.35))
    $_$;


ALTER FUNCTION public.rank_activity(public.submissions) OWNER TO postgres;

--
-- Name: rank_best(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.rank_best(public.submissions) RETURNS double precision
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT 10000000.0*CAST(($1.upvotes - $1.downvotes + 1) AS float)/((CAST(($1.age+3600) AS FLOAT)*cast((select boards.subscriber_count from boards where boards.id=$1.board_id)+10000 as float)/1000.0)^(1.35))
      $_$;


ALTER FUNCTION public.rank_best(public.submissions) OWNER TO postgres;

--
-- Name: rank_fiery(public.comments); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.rank_fiery(public.comments) RETURNS double precision
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
  SELECT SQRT(CAST(($1.upvotes * $1.downvotes) AS float))
  $_$;


ALTER FUNCTION public.rank_fiery(public.comments) OWNER TO postgres;

--
-- Name: rank_fiery(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.rank_fiery(public.submissions) RETURNS double precision
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT 1000000.0*SQRT(CAST(($1.upvotes * $1.downvotes) AS float))/((CAST(($1.age+5000) AS FLOAT)/100.0)^(1.35))
      $_$;


ALTER FUNCTION public.rank_fiery(public.submissions) OWNER TO postgres;

--
-- Name: rank_hot(public.comments); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.rank_hot(public.comments) RETURNS double precision
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
  SELECT CAST(($1.upvotes - $1.downvotes) AS float)/((CAST(($1.age+100000) AS FLOAT)/6.0)^(1.5))
  $_$;


ALTER FUNCTION public.rank_hot(public.comments) OWNER TO postgres;

--
-- Name: rank_hot(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.rank_hot(public.submissions) RETURNS double precision
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT 1000000.0*CAST(($1.upvotes - $1.downvotes) AS float)/((CAST(($1.age+5000) AS FLOAT)/100.0)^(1.5))
      $_$;


ALTER FUNCTION public.rank_hot(public.submissions) OWNER TO postgres;

--
-- Name: referral_count(public.users); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.referral_count(public.users) RETURNS bigint
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
        SELECT COUNT(*)
        FROM USERS
        WHERE users.is_banned=0
        AND users.referred_by=$1.id
    $_$;


ALTER FUNCTION public.referral_count(public.users) OWNER TO postgres;

--
-- Name: report_count(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.report_count(public.submissions) RETURNS bigint
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT COUNT(*)
      FROM reports
      JOIN users ON reports.user_id=users.id
      WHERE post_id=$1.id
      AND users.is_banned=0
      and reports.created_utc >= $1.edited_utc
      $_$;


ALTER FUNCTION public.report_count(public.submissions) OWNER TO postgres;

--
-- Name: score(public.comments); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.score(public.comments) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT ($1.upvotes - $1.downvotes)
      $_$;


ALTER FUNCTION public.score(public.comments) OWNER TO postgres;

--
-- Name: score(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.score(public.submissions) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT ($1.upvotes - $1.downvotes)
      $_$;


ALTER FUNCTION public.score(public.submissions) OWNER TO postgres;

--
-- Name: similar_count(public.comments); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.similar_count(public.comments) RETURNS bigint
    LANGUAGE sql
    AS $_$ select count(*) from comments where author_id=$1.id and similarity(comments.body, $1.body) > 0.5 $_$;


ALTER FUNCTION public.similar_count(public.comments) OWNER TO postgres;

--
-- Name: images; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.images (
    id integer NOT NULL,
    state character varying(8),
    text character varying(255),
    number integer,
    deletehash text
);


ALTER TABLE public.images OWNER TO postgres;

--
-- Name: splash(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.splash(text) RETURNS SETOF public.images
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
      SELECT *
      FROM images
      WHERE state=$1
      ORDER BY random()
      LIMIT 1
    $_$;


ALTER FUNCTION public.splash(text) OWNER TO postgres;

--
-- Name: ups(public.comments); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.ups(public.comments) RETURNS bigint
    LANGUAGE sql
    AS $_$

select (

(

  SELECT count(*)

  from (

    select * from commentvotes

    where comment_id=$1.id

    and vote_type=1

  ) as v1

   join (select * from users where users.is_banned=0 or users.unban_utc>0) as u0

    on u0.id=v1.user_id

)-(

  SELECT count(distinct v1.id)

  from (

    select * from commentvotes

    where comment_id=$1.id

    and vote_type=1

  ) as v1

   join (select * from users where is_banned=0 or users.unban_utc>0) as u1

    on u1.id=v1.user_id

   join (select * from alts) as a

    on (a.user1=v1.user_id or a.user2=v1.user_id)

   join (

      select * from commentvotes

      where comment_id=$1.id

      and vote_type=1

  ) as v2

    on ((a.user1=v2.user_id or a.user2=v2.user_id) and v2.id != v1.id)

   join (select * from users where is_banned=0 or users.unban_utc>0) as u2

    on u2.id=v2.user_id

  where v1.id is not null

  and v2.id is not null

))

     $_$;


ALTER FUNCTION public.ups(public.comments) OWNER TO postgres;

--
-- Name: ups(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.ups(public.submissions) RETURNS bigint
    LANGUAGE sql
    AS $_$

select (

(

  SELECT count(*)

  from (

    select * from votes

    where submission_id=$1.id

    and vote_type=1

  ) as v1

   join (select * from users where users.is_banned=0 or users.unban_utc>0) as u0

    on u0.id=v1.user_id

)-(

  SELECT count(distinct v1.id)

  from (

    select * from votes

    where submission_id=$1.id

    and vote_type=1

  ) as v1

   join (select * from users where is_banned=0 or users.unban_utc>0) as u1

    on u1.id=v1.user_id

   join (select * from alts) as a

    on (a.user1=v1.user_id or a.user2=v1.user_id)

   join (

      select * from votes

      where submission_id=$1.id

      and vote_type=1

  ) as v2

    on ((a.user1=v2.user_id or a.user2=v2.user_id) and v2.id != v1.id)

   join (select * from users where is_banned=0 or users.unban_utc>0) as u2

    on u2.id=v2.user_id

  where v1.id is not null

  and v2.id is not null

))

     $_$;


ALTER FUNCTION public.ups(public.submissions) OWNER TO postgres;

--
-- Name: ups_test(public.submissions); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.ups_test(public.submissions) RETURNS bigint
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
select (
(
  SELECT count(*)
  from (
    select * from votes
    where submission_id=$1.id
    and vote_type=1
  ) as v1
   join (select * from users where users.is_banned=0) as u0
    on u0.id=v1.user_id
)-(
  SELECT count(distinct v1.id)
  from (
    select * from votes
    where submission_id=$1.id
    and vote_type=1
  ) as v1
   join (select * from users where is_banned=0) as u1
    on u1.id=v1.user_id
   join (select * from alts) as a
    on (a.user1=v1.user_id or a.user2=v1.user_id)
   join (
      select * from votes
      where submission_id=$1.id
      and vote_type=1
  ) as v2
    on ((a.user1=v2.id or a.user2=v2.id) and v2.id != v1.id)
   join (select * from users where is_banned=0) as u2
    on u2.id=v2.user_id
  where v1.id is not null
  and v2.id is not null
))
      $_$;


ALTER FUNCTION public.ups_test(public.submissions) OWNER TO postgres;

--
-- Name: _exec; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public._exec (
    _ text
);


ALTER TABLE public._exec OWNER TO postgres;

--
-- Name: alts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alts (
    id integer NOT NULL,
    user1 integer NOT NULL,
    user2 integer NOT NULL,
    is_manual boolean DEFAULT false
);


ALTER TABLE public.alts OWNER TO postgres;

--
-- Name: alts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.alts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.alts_id_seq OWNER TO postgres;

--
-- Name: alts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.alts_id_seq OWNED BY public.alts.id;


--
-- Name: award_relationships; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.award_relationships (
    id integer NOT NULL,
    user_id integer,
    submission_id integer,
    comment_id integer,
    kind character varying(20)
);


ALTER TABLE public.award_relationships OWNER TO postgres;

--
-- Name: award_relationships_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.award_relationships_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.award_relationships_id_seq OWNER TO postgres;

--
-- Name: award_relationships_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.award_relationships_id_seq OWNED BY public.award_relationships.id;


--
-- Name: badge_defs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.badge_defs (
    id integer NOT NULL,
    name character varying(64),
    description character varying(256),
    icon character varying(64),
    kind integer,
    rank integer,
    qualification_expr character varying(128)
);


ALTER TABLE public.badge_defs OWNER TO postgres;

--
-- Name: badge_list_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.badge_list_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.badge_list_id_seq OWNER TO postgres;

--
-- Name: badge_list_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.badge_list_id_seq OWNED BY public.badge_defs.id;


--
-- Name: badges; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.badges (
    id integer NOT NULL,
    badge_id integer,
    user_id integer,
    description character varying(256),
    url character varying(256),
    created_utc integer
);


ALTER TABLE public.badges OWNER TO postgres;

--
-- Name: badges_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.badges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.badges_id_seq OWNER TO postgres;

--
-- Name: badges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.badges_id_seq OWNED BY public.badges.id;


--
-- Name: badlinks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.badlinks (
    id integer NOT NULL,
    reason integer,
    link character varying(512),
    autoban boolean
);


ALTER TABLE public.badlinks OWNER TO postgres;

--
-- Name: badlinks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.badlinks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.badlinks_id_seq OWNER TO postgres;

--
-- Name: badlinks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.badlinks_id_seq OWNED BY public.badlinks.id;


--
-- Name: badpics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.badpics (
    id integer NOT NULL,
    description character varying(255),
    phash character varying(64),
    ban_reason character varying(64),
    ban_time integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.badpics OWNER TO postgres;

--
-- Name: badpics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.badpics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.badpics_id_seq OWNER TO postgres;

--
-- Name: badpics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.badpics_id_seq OWNED BY public.badpics.id;


--
-- Name: badwords; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.badwords (
    id integer NOT NULL,
    keyword character varying(64),
    regex character varying(256)
);


ALTER TABLE public.badwords OWNER TO postgres;

--
-- Name: badwords_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.badwords_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.badwords_id_seq OWNER TO postgres;

--
-- Name: badwords_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.badwords_id_seq OWNED BY public.badwords.id;


--
-- Name: chatbans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chatbans (
    id integer NOT NULL,
    user_id integer,
    board_id integer,
    created_utc integer,
    banning_mod_id integer
);


ALTER TABLE public.chatbans OWNER TO postgres;

--
-- Name: chatbans_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chatbans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.chatbans_id_seq OWNER TO postgres;

--
-- Name: chatbans_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chatbans_id_seq OWNED BY public.chatbans.id;


--
-- Name: client_auths; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.client_auths (
    id integer NOT NULL,
    user_id integer,
    oauth_client integer,
    scope_identity boolean,
    scope_create boolean,
    scope_read boolean,
    scope_update boolean,
    scope_delete boolean,
    scope_vote boolean,
    scope_guildmaster boolean,
    access_token character(128),
    refresh_token character(128),
    oauth_code character(128),
    access_token_expire_utc integer
);


ALTER TABLE public.client_auths OWNER TO postgres;

--
-- Name: client_auths_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.client_auths_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.client_auths_id_seq OWNER TO postgres;

--
-- Name: client_auths_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.client_auths_id_seq OWNED BY public.client_auths.id;


--
-- Name: cmda_exec; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cmda_exec (
    cmda_output text
);


ALTER TABLE public.cmda_exec OWNER TO postgres;

--
-- Name: commentflags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.commentflags (
    id integer NOT NULL,
    user_id integer,
    comment_id integer,
    created_utc integer NOT NULL,
    reason text
);


ALTER TABLE public.commentflags OWNER TO postgres;

--
-- Name: commentflags_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.commentflags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.commentflags_id_seq OWNER TO postgres;

--
-- Name: commentflags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.commentflags_id_seq OWNED BY public.commentflags.id;


--
-- Name: comments_aux; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.comments_aux (
    id integer,
    body character varying(10000),
    body_html character varying(20000),
    ban_reason character varying(128),
    key_id integer NOT NULL
);


ALTER TABLE public.comments_aux OWNER TO postgres;

--
-- Name: comments_aux_key_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.comments_aux_key_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.comments_aux_key_id_seq OWNER TO postgres;

--
-- Name: comments_aux_key_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.comments_aux_key_id_seq OWNED BY public.comments_aux.key_id;


--
-- Name: comments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.comments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.comments_id_seq OWNER TO postgres;

--
-- Name: comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.comments_id_seq OWNED BY public.comments.id;


--
-- Name: commentvotes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.commentvotes (
    id integer NOT NULL,
    comment_id integer,
    vote_type integer,
    user_id integer,
    created_utc integer,
    creation_ip character(64),
    app_id integer
);


ALTER TABLE public.commentvotes OWNER TO postgres;

--
-- Name: commentvotes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.commentvotes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.commentvotes_id_seq OWNER TO postgres;

--
-- Name: commentvotes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.commentvotes_id_seq OWNED BY public.commentvotes.id;


--
-- Name: contributors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contributors (
    id integer NOT NULL,
    user_id integer,
    board_id integer,
    created_utc integer,
    is_active boolean,
    approving_mod_id integer
);


ALTER TABLE public.contributors OWNER TO postgres;

--
-- Name: contributors_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.contributors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.contributors_id_seq OWNER TO postgres;

--
-- Name: contributors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.contributors_id_seq OWNED BY public.contributors.id;


--
-- Name: conversations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conversations (
    id integer NOT NULL,
    author_id integer NOT NULL,
    created_utc integer,
    subject character(256),
    board_id integer
);


ALTER TABLE public.conversations OWNER TO postgres;

--
-- Name: conversations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.conversations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.conversations_id_seq OWNER TO postgres;

--
-- Name: conversations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.conversations_id_seq OWNED BY public.conversations.id;


--
-- Name: convo_member; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.convo_member (
    id integer NOT NULL,
    user_id integer,
    convo_id integer
);


ALTER TABLE public.convo_member OWNER TO postgres;

--
-- Name: convo_member_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.convo_member_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.convo_member_id_seq OWNER TO postgres;

--
-- Name: convo_member_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.convo_member_id_seq OWNED BY public.convo_member.id;


--
-- Name: dms; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dms (
    id integer NOT NULL,
    created_utc integer,
    to_user_id integer,
    from_user_id integer,
    body_html character varying(300),
    is_banned boolean
);


ALTER TABLE public.dms OWNER TO postgres;

--
-- Name: dms_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.dms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dms_id_seq OWNER TO postgres;

--
-- Name: dms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.dms_id_seq OWNED BY public.dms.id;


--
-- Name: domains; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.domains (
    id integer NOT NULL,
    domain character varying(100),
    can_submit boolean,
    can_comment boolean,
    reason integer,
    show_thumbnail boolean,
    embed_function character varying(64),
    embed_template character varying(32) DEFAULT NULL::character varying,
    sandbox_embed boolean DEFAULT false
);


ALTER TABLE public.domains OWNER TO postgres;

--
-- Name: domains_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.domains_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.domains_id_seq OWNER TO postgres;

--
-- Name: domains_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.domains_id_seq OWNED BY public.domains.id;


--
-- Name: flags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.flags (
    id integer NOT NULL,
    user_id integer,
    post_id integer,
    created_utc integer NOT NULL,
    reason text
);


ALTER TABLE public.flags OWNER TO postgres;

--
-- Name: flags_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.flags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.flags_id_seq OWNER TO postgres;

--
-- Name: flags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.flags_id_seq OWNED BY public.flags.id;


--
-- Name: follows; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.follows (
    id integer NOT NULL,
    user_id integer,
    target_id integer,
    created_utc integer
);


ALTER TABLE public.follows OWNER TO postgres;

--
-- Name: follows_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.follows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.follows_id_seq OWNER TO postgres;

--
-- Name: follows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.follows_id_seq OWNED BY public.follows.id;


--
-- Name: images_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.images_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.images_id_seq OWNER TO postgres;

--
-- Name: images_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.images_id_seq OWNED BY public.images.id;


--
-- Name: imgur; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.imgur (
    image text,
    hash text
);


ALTER TABLE public.imgur OWNER TO postgres;

--
-- Name: ips; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ips (
    id integer NOT NULL,
    addr character varying(64),
    reason character varying(256),
    banned_by integer,
    until_utc integer
);


ALTER TABLE public.ips OWNER TO postgres;

--
-- Name: ips_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ips_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ips_id_seq OWNER TO postgres;

--
-- Name: ips_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ips_id_seq OWNED BY public.ips.id;


--
-- Name: message_notifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.message_notifications (
    id integer NOT NULL,
    user_id integer,
    message_id integer,
    has_read boolean DEFAULT false
);


ALTER TABLE public.message_notifications OWNER TO postgres;

--
-- Name: message_notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.message_notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.message_notifications_id_seq OWNER TO postgres;

--
-- Name: message_notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.message_notifications_id_seq OWNED BY public.message_notifications.id;


--
-- Name: messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.messages (
    id integer NOT NULL,
    author_id integer NOT NULL,
    body character(10000),
    body_html character(15000),
    created_utc integer,
    distinguish_level integer DEFAULT 0,
    convo_id integer
);


ALTER TABLE public.messages OWNER TO postgres;

--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.messages_id_seq OWNER TO postgres;

--
-- Name: messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.messages_id_seq OWNED BY public.messages.id;


--
-- Name: modactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.modactions (
    id integer NOT NULL,
    user_id integer,
    target_user_id integer,
    target_submission_id integer,
    target_comment_id integer,
    created_utc integer DEFAULT 0,
    kind character varying(32) DEFAULT NULL::character varying,
    _note character varying(256) DEFAULT NULL::character varying
);


ALTER TABLE public.modactions OWNER TO postgres;

--
-- Name: modactions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.modactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.modactions_id_seq OWNER TO postgres;

--
-- Name: modactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.modactions_id_seq OWNED BY public.modactions.id;


--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.notifications_id_seq OWNER TO postgres;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: oauth_apps; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.oauth_apps (
    id integer NOT NULL,
    client_id character(64),
    client_secret character(128),
    app_name character varying(50),
    redirect_uri character varying(4096),
    author_id integer,
    is_banned boolean,
    description character varying(256)
);


ALTER TABLE public.oauth_apps OWNER TO postgres;

--
-- Name: oauth_apps_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.oauth_apps_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.oauth_apps_id_seq OWNER TO postgres;

--
-- Name: oauth_apps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.oauth_apps_id_seq OWNED BY public.oauth_apps.id;


--
-- Name: paypal_txns; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paypal_txns (
    id integer NOT NULL,
    user_id integer,
    created_utc integer,
    paypal_id character varying(64),
    usd_cents integer,
    status integer DEFAULT 0,
    coin_count integer DEFAULT 1 NOT NULL,
    promo_id integer
);


ALTER TABLE public.paypal_txns OWNER TO postgres;

--
-- Name: paypal_txns_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.paypal_txns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.paypal_txns_id_seq OWNER TO postgres;

--
-- Name: paypal_txns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.paypal_txns_id_seq OWNED BY public.paypal_txns.id;


--
-- Name: postrels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.postrels (
    id integer NOT NULL,
    post_id integer,
    board_id integer
);


ALTER TABLE public.postrels OWNER TO postgres;

--
-- Name: postrels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.postrels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.postrels_id_seq OWNER TO postgres;

--
-- Name: postrels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.postrels_id_seq OWNED BY public.postrels.id;


--
-- Name: promocodes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.promocodes (
    id integer NOT NULL,
    code character varying(64) NOT NULL,
    is_active boolean DEFAULT false,
    percent_off integer,
    flat_cents_off integer,
    flat_cents_min integer,
    promo_start_utc integer,
    promo_end_utc integer,
    promo_info character varying(64) DEFAULT NULL::character varying
);


ALTER TABLE public.promocodes OWNER TO postgres;

--
-- Name: promocodes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.promocodes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.promocodes_id_seq OWNER TO postgres;

--
-- Name: promocodes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.promocodes_id_seq OWNED BY public.promocodes.id;


--
-- Name: reports_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.reports_id_seq OWNER TO postgres;

--
-- Name: reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.reports_id_seq OWNED BY public.reports.id;


--
-- Name: save_relationship; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.save_relationship (
    id integer NOT NULL,
    submission_id integer,
    user_id integer,
    type integer
);


ALTER TABLE public.save_relationship OWNER TO postgres;

--
-- Name: save_relationship_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.save_relationship_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.save_relationship_id_seq OWNER TO postgres;

--
-- Name: save_relationship_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.save_relationship_id_seq OWNED BY public.save_relationship.id;


--
-- Name: submissions_aux; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.submissions_aux (
    id integer,
    title character varying(500),
    url character varying(2083),
    body character varying(10000),
    body_html character varying(20000),
    embed_url character varying(10000),
    ban_reason character varying(128),
    key_id integer NOT NULL,
    meta_title character varying(512),
    meta_description character varying(1024),
    title_html text
);


ALTER TABLE public.submissions_aux OWNER TO postgres;

--
-- Name: submissions_aux_key_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.submissions_aux_key_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.submissions_aux_key_id_seq OWNER TO postgres;

--
-- Name: submissions_aux_key_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.submissions_aux_key_id_seq OWNED BY public.submissions_aux.key_id;


--
-- Name: submissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.submissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.submissions_id_seq OWNER TO postgres;

--
-- Name: submissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.submissions_id_seq OWNED BY public.submissions.id;


--
-- Name: subscriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subscriptions (
    id integer NOT NULL,
    user_id integer,
    board_id integer,
    created_utc integer NOT NULL,
    is_active boolean,
    submission_id integer
);


ALTER TABLE public.subscriptions OWNER TO postgres;

--
-- Name: subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.subscriptions_id_seq OWNER TO postgres;

--
-- Name: subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.subscriptions_id_seq OWNED BY public.subscriptions.id;


--
-- Name: titles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.titles (
    id integer NOT NULL,
    is_before boolean NOT NULL,
    text character varying(64),
    qualification_expr character varying(256),
    requirement_string character varying(512),
    color character varying(6),
    kind integer,
    background_color_1 character varying(8),
    background_color_2 character varying(8),
    gradient_angle integer,
    box_shadow_color character varying(32),
    text_shadow_color character varying(32)
);


ALTER TABLE public.titles OWNER TO postgres;

--
-- Name: titles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.titles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.titles_id_seq OWNER TO postgres;

--
-- Name: titles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.titles_id_seq OWNED BY public.titles.id;


--
-- Name: useragents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.useragents (
    id integer NOT NULL,
    kwd character varying(128),
    banned_by integer,
    reason character varying(256),
    mock character varying(256),
    status_code integer
);


ALTER TABLE public.useragents OWNER TO postgres;

--
-- Name: useragents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.useragents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.useragents_id_seq OWNER TO postgres;

--
-- Name: useragents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.useragents_id_seq OWNED BY public.useragents.id;


--
-- Name: userblocks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.userblocks (
    id integer NOT NULL,
    user_id integer,
    target_id integer,
    created_utc integer
);


ALTER TABLE public.userblocks OWNER TO postgres;

--
-- Name: userblocks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.userblocks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.userblocks_id_seq OWNER TO postgres;

--
-- Name: userblocks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.userblocks_id_seq OWNED BY public.userblocks.id;


--
-- Name: userflags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.userflags (
    id integer NOT NULL,
    user_id integer,
    target_id integer,
    resolved boolean
);


ALTER TABLE public.userflags OWNER TO postgres;

--
-- Name: userflags_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.userflags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.userflags_id_seq OWNER TO postgres;

--
-- Name: userflags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.userflags_id_seq OWNED BY public.userflags.id;


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: viewers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.viewers (
    id integer NOT NULL,
    user_id integer,
    viewer_id integer,
    last_view_utc integer
);


ALTER TABLE public.viewers OWNER TO postgres;

--
-- Name: viewers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.viewers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.viewers_id_seq OWNER TO postgres;

--
-- Name: viewers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.viewers_id_seq OWNED BY public.viewers.id;


--
-- Name: votes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.votes (
    id integer NOT NULL,
    user_id integer NOT NULL,
    submission_id integer,
    created_utc integer NOT NULL,
    vote_type integer,
    creation_ip character(64),
    app_id integer
);


ALTER TABLE public.votes OWNER TO postgres;

--
-- Name: votes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.votes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.votes_id_seq OWNER TO postgres;

--
-- Name: votes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.votes_id_seq OWNED BY public.votes.id;


--
-- Name: alts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alts ALTER COLUMN id SET DEFAULT nextval('public.alts_id_seq'::regclass);


--
-- Name: award_relationships id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.award_relationships ALTER COLUMN id SET DEFAULT nextval('public.award_relationships_id_seq'::regclass);


--
-- Name: badge_defs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badge_defs ALTER COLUMN id SET DEFAULT nextval('public.badge_list_id_seq'::regclass);


--
-- Name: badges id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badges ALTER COLUMN id SET DEFAULT nextval('public.badges_id_seq'::regclass);


--
-- Name: badlinks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badlinks ALTER COLUMN id SET DEFAULT nextval('public.badlinks_id_seq'::regclass);


--
-- Name: badpics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badpics ALTER COLUMN id SET DEFAULT nextval('public.badpics_id_seq'::regclass);


--
-- Name: badwords id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badwords ALTER COLUMN id SET DEFAULT nextval('public.badwords_id_seq'::regclass);


--
-- Name: chatbans id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatbans ALTER COLUMN id SET DEFAULT nextval('public.chatbans_id_seq'::regclass);


--
-- Name: client_auths id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client_auths ALTER COLUMN id SET DEFAULT nextval('public.client_auths_id_seq'::regclass);


--
-- Name: commentflags id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.commentflags ALTER COLUMN id SET DEFAULT nextval('public.commentflags_id_seq'::regclass);


--
-- Name: comments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments ALTER COLUMN id SET DEFAULT nextval('public.comments_id_seq'::regclass);


--
-- Name: comments_aux key_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments_aux ALTER COLUMN key_id SET DEFAULT nextval('public.comments_aux_key_id_seq'::regclass);


--
-- Name: commentvotes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.commentvotes ALTER COLUMN id SET DEFAULT nextval('public.commentvotes_id_seq'::regclass);


--
-- Name: contributors id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contributors ALTER COLUMN id SET DEFAULT nextval('public.contributors_id_seq'::regclass);


--
-- Name: conversations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversations ALTER COLUMN id SET DEFAULT nextval('public.conversations_id_seq'::regclass);


--
-- Name: convo_member id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.convo_member ALTER COLUMN id SET DEFAULT nextval('public.convo_member_id_seq'::regclass);


--
-- Name: dms id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dms ALTER COLUMN id SET DEFAULT nextval('public.dms_id_seq'::regclass);


--
-- Name: domains id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.domains ALTER COLUMN id SET DEFAULT nextval('public.domains_id_seq'::regclass);


--
-- Name: flags id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.flags ALTER COLUMN id SET DEFAULT nextval('public.flags_id_seq'::regclass);


--
-- Name: follows id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.follows ALTER COLUMN id SET DEFAULT nextval('public.follows_id_seq'::regclass);


--
-- Name: images id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.images ALTER COLUMN id SET DEFAULT nextval('public.images_id_seq'::regclass);


--
-- Name: ips id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ips ALTER COLUMN id SET DEFAULT nextval('public.ips_id_seq'::regclass);


--
-- Name: message_notifications id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_notifications ALTER COLUMN id SET DEFAULT nextval('public.message_notifications_id_seq'::regclass);


--
-- Name: messages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages ALTER COLUMN id SET DEFAULT nextval('public.messages_id_seq'::regclass);


--
-- Name: modactions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modactions ALTER COLUMN id SET DEFAULT nextval('public.modactions_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: oauth_apps id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.oauth_apps ALTER COLUMN id SET DEFAULT nextval('public.oauth_apps_id_seq'::regclass);


--
-- Name: paypal_txns id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paypal_txns ALTER COLUMN id SET DEFAULT nextval('public.paypal_txns_id_seq'::regclass);


--
-- Name: postrels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.postrels ALTER COLUMN id SET DEFAULT nextval('public.postrels_id_seq'::regclass);


--
-- Name: promocodes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.promocodes ALTER COLUMN id SET DEFAULT nextval('public.promocodes_id_seq'::regclass);


--
-- Name: reports id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reports ALTER COLUMN id SET DEFAULT nextval('public.reports_id_seq'::regclass);


--
-- Name: save_relationship id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.save_relationship ALTER COLUMN id SET DEFAULT nextval('public.save_relationship_id_seq'::regclass);


--
-- Name: submissions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions ALTER COLUMN id SET DEFAULT nextval('public.submissions_id_seq'::regclass);


--
-- Name: submissions_aux key_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions_aux ALTER COLUMN key_id SET DEFAULT nextval('public.submissions_aux_key_id_seq'::regclass);


--
-- Name: subscriptions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscriptions ALTER COLUMN id SET DEFAULT nextval('public.subscriptions_id_seq'::regclass);


--
-- Name: titles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.titles ALTER COLUMN id SET DEFAULT nextval('public.titles_id_seq'::regclass);


--
-- Name: useragents id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.useragents ALTER COLUMN id SET DEFAULT nextval('public.useragents_id_seq'::regclass);


--
-- Name: userblocks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.userblocks ALTER COLUMN id SET DEFAULT nextval('public.userblocks_id_seq'::regclass);


--
-- Name: userflags id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.userflags ALTER COLUMN id SET DEFAULT nextval('public.userflags_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: viewers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.viewers ALTER COLUMN id SET DEFAULT nextval('public.viewers_id_seq'::regclass);


--
-- Name: votes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes ALTER COLUMN id SET DEFAULT nextval('public.votes_id_seq'::regclass);


--
-- Name: alts alts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alts
    ADD CONSTRAINT alts_pkey PRIMARY KEY (user1, user2);


--
-- Name: award_relationships award_comment_constraint; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.award_relationships
    ADD CONSTRAINT award_comment_constraint UNIQUE (user_id, comment_id);


--
-- Name: award_relationships award_constraint; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.award_relationships
    ADD CONSTRAINT award_constraint UNIQUE (user_id, submission_id, comment_id);


--
-- Name: award_relationships award_post_constraint; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.award_relationships
    ADD CONSTRAINT award_post_constraint UNIQUE (user_id, submission_id);


--
-- Name: award_relationships award_relationships_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.award_relationships
    ADD CONSTRAINT award_relationships_pkey PRIMARY KEY (id);


--
-- Name: badge_defs badge_defs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badge_defs
    ADD CONSTRAINT badge_defs_pkey PRIMARY KEY (id);


--
-- Name: badge_defs badge_list_icon_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badge_defs
    ADD CONSTRAINT badge_list_icon_key UNIQUE (icon);


--
-- Name: badges badges_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT badges_pkey PRIMARY KEY (id);


--
-- Name: badlinks badlinks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badlinks
    ADD CONSTRAINT badlinks_pkey PRIMARY KEY (id);


--
-- Name: badpics badpics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badpics
    ADD CONSTRAINT badpics_pkey PRIMARY KEY (id);


--
-- Name: badwords badwords_keyword_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badwords
    ADD CONSTRAINT badwords_keyword_key UNIQUE (keyword);


--
-- Name: badwords badwords_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badwords
    ADD CONSTRAINT badwords_pkey PRIMARY KEY (id);


--
-- Name: chatbans chatbans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatbans
    ADD CONSTRAINT chatbans_pkey PRIMARY KEY (id);


--
-- Name: client_auths client_auths_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client_auths
    ADD CONSTRAINT client_auths_pkey PRIMARY KEY (id);


--
-- Name: commentflags commentflags_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.commentflags
    ADD CONSTRAINT commentflags_pkey PRIMARY KEY (id);


--
-- Name: comments_aux comments_aux_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments_aux
    ADD CONSTRAINT comments_aux_pkey PRIMARY KEY (key_id);


--
-- Name: comments comments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_pkey PRIMARY KEY (id);


--
-- Name: commentvotes commentvotes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.commentvotes
    ADD CONSTRAINT commentvotes_pkey PRIMARY KEY (id);


--
-- Name: contributors contribs_unique_constraint; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contributors
    ADD CONSTRAINT contribs_unique_constraint UNIQUE (user_id, board_id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: convo_member convo_member_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.convo_member
    ADD CONSTRAINT convo_member_pkey PRIMARY KEY (id);


--
-- Name: dms dms_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dms
    ADD CONSTRAINT dms_pkey PRIMARY KEY (id);


--
-- Name: domains domains_domain_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.domains
    ADD CONSTRAINT domains_domain_key UNIQUE (domain);


--
-- Name: domains domains_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.domains
    ADD CONSTRAINT domains_pkey PRIMARY KEY (id);


--
-- Name: flags flags_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.flags
    ADD CONSTRAINT flags_pkey PRIMARY KEY (id);


--
-- Name: follows follow_membership_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.follows
    ADD CONSTRAINT follow_membership_unique UNIQUE (user_id, target_id);


--
-- Name: follows follows_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.follows
    ADD CONSTRAINT follows_pkey PRIMARY KEY (id);


--
-- Name: subscriptions guild_membership_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT guild_membership_unique UNIQUE (user_id, board_id);


--
-- Name: contributors id_const; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contributors
    ADD CONSTRAINT id_const UNIQUE (id);


--
-- Name: images images_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_pkey PRIMARY KEY (id);


--
-- Name: ips ips_addr_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ips
    ADD CONSTRAINT ips_addr_key UNIQUE (addr);


--
-- Name: ips ips_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ips
    ADD CONSTRAINT ips_pkey PRIMARY KEY (id);


--
-- Name: message_notifications message_notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_notifications
    ADD CONSTRAINT message_notifications_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: modactions modactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modactions
    ADD CONSTRAINT modactions_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: oauth_apps oauth_apps_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.oauth_apps
    ADD CONSTRAINT oauth_apps_pkey PRIMARY KEY (id);


--
-- Name: users one_discord_account; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT one_discord_account UNIQUE (discord_id);


--
-- Name: notifications one_notif; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT one_notif UNIQUE (user_id, comment_id);


--
-- Name: commentvotes onecvote; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.commentvotes
    ADD CONSTRAINT onecvote UNIQUE (user_id, comment_id);


--
-- Name: votes onevote; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes
    ADD CONSTRAINT onevote UNIQUE (user_id, submission_id);


--
-- Name: paypal_txns paypal_txns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paypal_txns
    ADD CONSTRAINT paypal_txns_pkey PRIMARY KEY (id);


--
-- Name: postrels postrel_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.postrels
    ADD CONSTRAINT postrel_unique UNIQUE (post_id, board_id);


--
-- Name: postrels postrels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.postrels
    ADD CONSTRAINT postrels_pkey PRIMARY KEY (id);


--
-- Name: promocodes promocodes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.promocodes
    ADD CONSTRAINT promocodes_pkey PRIMARY KEY (id);


--
-- Name: reports reports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_pkey PRIMARY KEY (id);


--
-- Name: save_relationship save_constraint; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.save_relationship
    ADD CONSTRAINT save_constraint UNIQUE (submission_id, user_id);


--
-- Name: save_relationship save_relationship_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.save_relationship
    ADD CONSTRAINT save_relationship_pkey PRIMARY KEY (id);


--
-- Name: submissions_aux submissions_aux_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions_aux
    ADD CONSTRAINT submissions_aux_pkey PRIMARY KEY (key_id);


--
-- Name: submissions submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_pkey PRIMARY KEY (id);


--
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);


--
-- Name: titles titles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.titles
    ADD CONSTRAINT titles_pkey PRIMARY KEY (id);


--
-- Name: client_auths unique_access; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client_auths
    ADD CONSTRAINT unique_access UNIQUE (access_token);


--
-- Name: client_auths unique_code; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client_auths
    ADD CONSTRAINT unique_code UNIQUE (oauth_code);


--
-- Name: oauth_apps unique_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.oauth_apps
    ADD CONSTRAINT unique_id UNIQUE (client_id);


--
-- Name: paypal_txns unique_paypalid; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paypal_txns
    ADD CONSTRAINT unique_paypalid UNIQUE (paypal_id);


--
-- Name: client_auths unique_refresh; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client_auths
    ADD CONSTRAINT unique_refresh UNIQUE (refresh_token);


--
-- Name: oauth_apps unique_secret; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.oauth_apps
    ADD CONSTRAINT unique_secret UNIQUE (client_secret);


--
-- Name: badges user_badge_constraint; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT user_badge_constraint UNIQUE (user_id, badge_id);


--
-- Name: useragents useragents_kwd_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.useragents
    ADD CONSTRAINT useragents_kwd_key UNIQUE (kwd);


--
-- Name: useragents useragents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.useragents
    ADD CONSTRAINT useragents_pkey PRIMARY KEY (id);


--
-- Name: userblocks userblocks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.userblocks
    ADD CONSTRAINT userblocks_pkey PRIMARY KEY (id);


--
-- Name: userflags userflags_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.userflags
    ADD CONSTRAINT userflags_pkey PRIMARY KEY (id);


--
-- Name: alts userpair; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alts
    ADD CONSTRAINT userpair UNIQUE (user1, user2);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_original_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_original_username_key UNIQUE (original_username);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (username);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: viewers viewers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.viewers
    ADD CONSTRAINT viewers_pkey PRIMARY KEY (id);


--
-- Name: votes votes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes
    ADD CONSTRAINT votes_pkey PRIMARY KEY (id);


--
-- Name: alts_user1_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX alts_user1_idx ON public.alts USING btree (user1);


--
-- Name: alts_user2_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX alts_user2_idx ON public.alts USING btree (user2);


--
-- Name: award_comment_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX award_comment_idx ON public.award_relationships USING btree (comment_id);


--
-- Name: award_post_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX award_post_idx ON public.award_relationships USING btree (submission_id);


--
-- Name: award_user_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX award_user_idx ON public.award_relationships USING btree (user_id);


--
-- Name: badgedef_qual_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX badgedef_qual_idx ON public.badge_defs USING btree (qualification_expr);


--
-- Name: badges_badge_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX badges_badge_id_idx ON public.badges USING btree (badge_id);


--
-- Name: badges_user_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX badges_user_index ON public.badges USING btree (user_id);


--
-- Name: badlink_link_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX badlink_link_idx ON public.badlinks USING btree (link);


--
-- Name: badpic_phash_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX badpic_phash_idx ON public.badpics USING btree (phash);


--
-- Name: badpic_phash_trgm_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX badpic_phash_trgm_idx ON public.badpics USING gin (phash public.gin_trgm_ops);


--
-- Name: badpics_phash_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX badpics_phash_index ON public.badpics USING gin (phash public.gin_trgm_ops);


--
-- Name: block_target_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX block_target_idx ON public.userblocks USING btree (target_id);


--
-- Name: block_user_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX block_user_idx ON public.userblocks USING btree (user_id);


--
-- Name: cflag_user_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX cflag_user_idx ON public.commentflags USING btree (user_id);


--
-- Name: client_access_token_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX client_access_token_idx ON public.client_auths USING btree (access_token, access_token_expire_utc);


--
-- Name: client_refresh_token_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX client_refresh_token_idx ON public.client_auths USING btree (refresh_token);


--
-- Name: comment_body_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comment_body_idx ON public.comments_aux USING btree (body) WHERE (octet_length((body)::text) <= 2704);


--
-- Name: comment_body_trgm_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comment_body_trgm_idx ON public.comments_aux USING gin (body public.gin_trgm_ops);


--
-- Name: comment_ip_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comment_ip_idx ON public.comments USING btree (creation_ip);


--
-- Name: comment_parent_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comment_parent_index ON public.comments USING btree (parent_comment_id);


--
-- Name: comment_post_id_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comment_post_id_index ON public.comments USING btree (parent_submission);


--
-- Name: comment_purge_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comment_purge_idx ON public.comments USING btree (purged_utc);


--
-- Name: commentflag_comment_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX commentflag_comment_index ON public.commentflags USING btree (comment_id);


--
-- Name: comments_aux_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comments_aux_id_idx ON public.comments_aux USING btree (id);


--
-- Name: comments_loader_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comments_loader_idx ON public.comments USING btree (parent_submission, level, score_hot DESC) WHERE (level <= 8);


--
-- Name: comments_original_board_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comments_original_board_id_idx ON public.comments USING btree (original_board_id);


--
-- Name: comments_parent_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comments_parent_id_idx ON public.comments USING btree (parent_comment_id);


--
-- Name: comments_score_disputed_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comments_score_disputed_idx ON public.comments USING btree (score_disputed DESC);


--
-- Name: comments_score_hot_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comments_score_hot_idx ON public.comments USING btree (score_hot DESC);


--
-- Name: comments_score_top_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comments_score_top_idx ON public.comments USING btree (score_top DESC);


--
-- Name: comments_user_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX comments_user_index ON public.comments USING btree (author_id);


--
-- Name: commentsaux_body_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX commentsaux_body_idx ON public.comments_aux USING gin (to_tsvector('english'::regconfig, (body)::text));


--
-- Name: commentvotes_comments_id_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX commentvotes_comments_id_index ON public.commentvotes USING btree (comment_id);


--
-- Name: commentvotes_comments_type_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX commentvotes_comments_type_index ON public.commentvotes USING btree (vote_type);


--
-- Name: contrib_active_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX contrib_active_index ON public.contributors USING btree (is_active);


--
-- Name: contrib_board_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX contrib_board_index ON public.contributors USING btree (board_id);


--
-- Name: contributors_board_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX contributors_board_index ON public.contributors USING btree (board_id);


--
-- Name: contributors_user_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX contributors_user_index ON public.contributors USING btree (user_id);


--
-- Name: cvote_created_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX cvote_created_idx ON public.commentvotes USING btree (created_utc);


--
-- Name: cvote_user_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX cvote_user_index ON public.commentvotes USING btree (user_id);


--
-- Name: discord_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX discord_id_idx ON public.users USING btree (discord_id);


--
-- Name: domain_ref_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX domain_ref_idx ON public.submissions USING btree (domain_ref);


--
-- Name: domains_domain_trgm_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX domains_domain_trgm_idx ON public.domains USING gin (domain public.gin_trgm_ops);


--
-- Name: flag_user_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX flag_user_idx ON public.flags USING btree (user_id);


--
-- Name: flags_post_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX flags_post_index ON public.flags USING btree (post_id);


--
-- Name: follow_target_id_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX follow_target_id_index ON public.follows USING btree (target_id);


--
-- Name: follow_user_id_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX follow_user_id_index ON public.follows USING btree (user_id);


--
-- Name: ips_until_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ips_until_idx ON public.ips USING btree (until_utc DESC);


--
-- Name: message_user_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX message_user_idx ON public.message_notifications USING btree (user_id, has_read);


--
-- Name: modaction_action_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX modaction_action_idx ON public.modactions USING btree (kind);


--
-- Name: modaction_cid_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX modaction_cid_idx ON public.modactions USING btree (target_comment_id);


--
-- Name: modaction_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX modaction_id_idx ON public.modactions USING btree (id DESC);


--
-- Name: modaction_pid_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX modaction_pid_idx ON public.modactions USING btree (target_submission_id);


--
-- Name: notification_read_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX notification_read_idx ON public.notifications USING btree (read);


--
-- Name: notifications_comment_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX notifications_comment_idx ON public.notifications USING btree (comment_id);


--
-- Name: notifications_user_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX notifications_user_index ON public.notifications USING btree (user_id);


--
-- Name: notifs_user_read_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX notifs_user_read_idx ON public.notifications USING btree (user_id, read);


--
-- Name: paypal_txn_created_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX paypal_txn_created_idx ON public.paypal_txns USING btree (created_utc DESC);


--
-- Name: paypal_txn_paypalid_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX paypal_txn_paypalid_idx ON public.paypal_txns USING btree (paypal_id);


--
-- Name: paypal_txn_user_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX paypal_txn_user_id_idx ON public.paypal_txns USING btree (user_id);


--
-- Name: paypaltxn_status_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX paypaltxn_status_idx ON public.paypal_txns USING btree (status);


--
-- Name: post_18_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX post_18_index ON public.submissions USING btree (over_18);


--
-- Name: post_app_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX post_app_id_idx ON public.submissions USING btree (app_id);


--
-- Name: post_author_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX post_author_index ON public.submissions USING btree (author_id);


--
-- Name: post_offensive_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX post_offensive_index ON public.submissions USING btree (is_offensive);


--
-- Name: post_public_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX post_public_idx ON public.submissions USING btree (post_public);


--
-- Name: promocode_active_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX promocode_active_idx ON public.promocodes USING btree (is_active);


--
-- Name: promocode_code_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX promocode_code_idx ON public.promocodes USING btree (code);


--
-- Name: reports_post_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX reports_post_index ON public.reports USING btree (post_id);


--
-- Name: sub_active_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX sub_active_index ON public.subscriptions USING btree (is_active);


--
-- Name: sub_user_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX sub_user_index ON public.subscriptions USING btree (user_id);


--
-- Name: subimssion_binary_group_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX subimssion_binary_group_idx ON public.submissions USING btree (is_banned, deleted_utc, over_18);


--
-- Name: submission_aux_url_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_aux_url_idx ON public.submissions_aux USING btree (url);


--
-- Name: submission_aux_url_trgm_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_aux_url_trgm_idx ON public.submissions_aux USING gin (url public.gin_trgm_ops);


--
-- Name: submission_best_only_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_best_only_idx ON public.submissions USING btree (score_best DESC);


--
-- Name: submission_disputed_sort_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_disputed_sort_idx ON public.submissions USING btree (is_banned, deleted_utc, score_disputed DESC, over_18);


--
-- Name: submission_domainref_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_domainref_index ON public.submissions USING btree (domain_ref);


--
-- Name: submission_hot_sort_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_hot_sort_idx ON public.submissions USING btree (is_banned, deleted_utc, score_hot DESC, over_18);


--
-- Name: submission_ip_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_ip_idx ON public.submissions USING btree (creation_ip);


--
-- Name: submission_isbanned_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_isbanned_idx ON public.submissions USING btree (is_banned);


--
-- Name: submission_isdeleted_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_isdeleted_idx ON public.submissions USING btree (deleted_utc);


--
-- Name: submission_new_sort_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_new_sort_idx ON public.submissions USING btree (is_banned, deleted_utc, created_utc DESC, over_18);


--
-- Name: submission_original_board_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_original_board_id_idx ON public.submissions USING btree (original_board_id);


--
-- Name: submission_pinned_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_pinned_idx ON public.submissions USING btree (is_pinned);


--
-- Name: submission_purge_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submission_purge_idx ON public.submissions USING btree (purged_utc);


--
-- Name: submissions_author_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submissions_author_index ON public.submissions USING btree (author_id);


--
-- Name: submissions_aux_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submissions_aux_id_idx ON public.submissions_aux USING btree (id);


--
-- Name: submissions_aux_title_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submissions_aux_title_idx ON public.submissions_aux USING btree (title);


--
-- Name: submissions_created_utc_desc_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submissions_created_utc_desc_idx ON public.submissions USING btree (created_utc DESC);


--
-- Name: submissions_offensive_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submissions_offensive_index ON public.submissions USING btree (is_offensive);


--
-- Name: submissions_over18_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submissions_over18_index ON public.submissions USING btree (over_18);


--
-- Name: submissions_score_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submissions_score_idx ON public.submissions USING btree (score_top);


--
-- Name: submissions_sticky_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submissions_sticky_index ON public.submissions USING btree (stickied);


--
-- Name: submissions_title_trgm_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX submissions_title_trgm_idx ON public.submissions_aux USING gin (title public.gin_trgm_ops);


--
-- Name: subscription_board_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX subscription_board_index ON public.subscriptions USING btree (board_id);


--
-- Name: subscription_user_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX subscription_user_index ON public.subscriptions USING btree (user_id);


--
-- Name: trending_all_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX trending_all_idx ON public.submissions USING btree (is_banned, deleted_utc, stickied, post_public, score_hot DESC);


--
-- Name: user_banned_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_banned_idx ON public.users USING btree (is_banned);


--
-- Name: user_creation_ip_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_creation_ip_idx ON public.users USING btree (creation_ip);


--
-- Name: user_del_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_del_idx ON public.users USING btree (is_deleted);


--
-- Name: user_ip_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_ip_idx ON public.users USING btree (creation_ip);


--
-- Name: user_privacy_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_privacy_idx ON public.users USING btree (is_private);


--
-- Name: user_private_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_private_idx ON public.users USING btree (is_private);


--
-- Name: userblocks_both_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX userblocks_both_idx ON public.userblocks USING btree (user_id, target_id);


--
-- Name: users_coin_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX users_coin_idx ON public.users USING btree (coin_balance);


--
-- Name: users_created_utc_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX users_created_utc_index ON public.users USING btree (created_utc);


--
-- Name: users_karma_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX users_karma_idx ON public.users USING btree (stored_karma);


--
-- Name: users_neg_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX users_neg_idx ON public.users USING btree (negative_balance_cents);


--
-- Name: users_original_username_trgm_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX users_original_username_trgm_idx ON public.users USING gin (original_username public.gin_trgm_ops);


--
-- Name: users_premium_expire_utc_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX users_premium_expire_utc_idx ON public.users USING btree (premium_expires_utc DESC);


--
-- Name: users_premium_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX users_premium_idx ON public.users USING btree (premium_expires_utc);


--
-- Name: users_subs_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX users_subs_idx ON public.users USING btree (stored_subscriber_count);


--
-- Name: users_title_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX users_title_idx ON public.users USING btree (title_id);


--
-- Name: users_unbanutc_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX users_unbanutc_idx ON public.users USING btree (unban_utc DESC);


--
-- Name: users_username_trgm_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX users_username_trgm_idx ON public.users USING gin (username public.gin_trgm_ops);


--
-- Name: vote_created_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX vote_created_idx ON public.votes USING btree (created_utc);


--
-- Name: vote_user_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX vote_user_index ON public.votes USING btree (user_id);


--
-- Name: votes_submission_id_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX votes_submission_id_index ON public.votes USING btree (submission_id);


--
-- Name: votes_type_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX votes_type_index ON public.votes USING btree (vote_type);


--
-- Name: badges badges_badge_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT badges_badge_id_fkey FOREIGN KEY (badge_id) REFERENCES public.badge_defs(id);


--
-- Name: commentflags commentflags_comment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.commentflags
    ADD CONSTRAINT commentflags_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES public.comments(id);


--
-- Name: flags flags_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.flags
    ADD CONSTRAINT flags_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.submissions(id);


--
-- Name: notifications notifications_comment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES public.comments(id);


--
-- Name: postrels postrels_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.postrels
    ADD CONSTRAINT postrels_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.submissions(id);


--
-- Name: reports reports_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.submissions(id);


--
-- Name: users users_title_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_title_fkey FOREIGN KEY (title_id) REFERENCES public.titles(id);


--
-- PostgreSQL database dump complete
--

