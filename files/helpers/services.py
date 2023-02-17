import sys

import gevent
from pusher_push_notifications import PushNotifications
from sqlalchemy.orm import scoped_session

from files.classes.leaderboard import (Leaderboard, LeaderboardMeta, 
                                       ReceivedDownvotesLeaderboard, GivenUpvotesLeaderboard)
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

_lb_received_downvotes_meta = LeaderboardMeta("Downvotes", "received downvotes", "received-downvotes", "downvotes", "downvoted")
_lb_given_upvotes_meta = LeaderboardMeta("Upvotes", "given upvotes", "given-upvotes", "upvotes", "upvoting")

def leaderboard_thread():
	global lb_downvotes_received, lb_upvotes_given

	db:scoped_session = db_session() # type: ignore

	lb_downvotes_received = ReceivedDownvotesLeaderboard(_lb_received_downvotes_meta, db)
	lb_upvotes_given = GivenUpvotesLeaderboard(_lb_given_upvotes_meta, db)

	db.close()
	sys.stdout.flush()

if app.config["ENABLE_SERVICES"]:
	gevent.spawn(leaderboard_thread())
