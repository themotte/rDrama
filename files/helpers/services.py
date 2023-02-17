from collections import Counter
import sys

import gevent
from pusher_push_notifications import PushNotifications
from sqlalchemy.sql import func
from sqlalchemy.orm import scoped_session

from files.classes import Comment, CommentVote, Submission, User, Vote
from files.helpers.assetcache import assetcache_path
from files.helpers.const import PUSHER_ID, PUSHER_KEY, SITE_FULL, SITE_ID
from files.__main__ import app, db_session

if PUSHER_ID != 'blahblahblah':
	beams_client = PushNotifications(instance_id=PUSHER_ID, secret_key=PUSHER_KEY)
else:
	beams_client = None

def pusher_thread2(interests, notifbody, username):
	if not beams_client: return
	beams_client.publish_to_interests(
		interests=[interests],
		publish_body={
			'web': {
				'notification': {
					'title': f'New message from @{username}',
					'body': notifbody,
					'deep_link': f'{SITE_FULL}/notifications?messages=true',
					'icon': SITE_FULL + assetcache_path(f'images/{SITE_ID}/icon.webp'),
				}
			},
			'fcm': {
				'notification': {
					'title': f'New message from @{username}',
					'body': notifbody,
				},
				'data': {
					'url': '/notifications?messages=true',
				}
			}
		},
	)
	sys.stdout.flush()

def leaderboard_thread():
	global lb_received_downvotes, lb_received_downvotes_first_25, lb_given_upvotes, lb_given_upvotes_first_25

	db: scoped_session = db_session() # type: ignore

	votes1 = db.query(Submission.author_id, func.count(Submission.author_id)).join(Vote, Vote.submission_id==Submission.id).filter(Vote.vote_type==-1).group_by(Submission.author_id).order_by(func.count(Submission.author_id).desc()).all()
	votes2 = db.query(Comment.author_id, func.count(Comment.author_id)).join(CommentVote, CommentVote.comment_id==Comment.id).filter(CommentVote.vote_type==-1).group_by(Comment.author_id).order_by(func.count(Comment.author_id).desc()).all()
	
	votes3 = Counter(dict(votes1)) + Counter(dict(votes2))
	users8 = db.query(User).filter(User.id.in_(votes3.keys())).all()
	
	lb_received_downvotes = []
	
	for user in users8: lb_received_downvotes.append((user, votes3[user.id]))
	
	lb_received_downvotes = sorted(lb_received_downvotes, key=lambda x: x[1], reverse=True)
	lb_received_downvotes_first_25 = lb_received_downvotes[:25]

	votes1 = db.query(Vote.user_id, func.count(Vote.user_id)).filter(Vote.vote_type==1).group_by(Vote.user_id).order_by(func.count(Vote.user_id).desc()).all()
	votes2 = db.query(CommentVote.user_id, func.count(CommentVote.user_id)).filter(CommentVote.vote_type==1).group_by(CommentVote.user_id).order_by(func.count(CommentVote.user_id).desc()).all()
	votes3 = Counter(dict(votes1)) + Counter(dict(votes2))
	
	users14 = db.query(User).filter(User.id.in_(votes3.keys())).all()
	
	lb_given_upvotes = []
	
	for user in users14:
		lb_given_upvotes.append((user, votes3[user.id]-user.post_count-user.comment_count))
	lb_given_upvotes = sorted(lb_given_upvotes, key=lambda x: x[1], reverse=True)
	lb_given_upvotes_first_25 = lb_given_upvotes[:25]

	db.close()
	sys.stdout.flush()

if app.config["ENABLE_SERVICES"]:
	gevent.spawn(leaderboard_thread())
