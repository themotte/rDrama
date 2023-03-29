import sys

import gevent
from pusher_push_notifications import PushNotifications
from sqlalchemy.orm import Session

from files.__main__ import db_session, service
from files.classes.leaderboard import (GivenUpvotesLeaderboard,
                                       LeaderboardMeta,
                                       ReceivedDownvotesLeaderboard)
from files.helpers.assetcache import assetcache_path
from files.helpers.config.environment import (ENABLE_SERVICES, PUSHER_ID,
                                              PUSHER_KEY, SITE_FULL, SITE_ID)

if service.enable_services and ENABLE_SERVICES and PUSHER_ID != 'blahblahblah':
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

lb_downvotes_received: ReceivedDownvotesLeaderboard | None = None
lb_upvotes_given: GivenUpvotesLeaderboard | None = None

def leaderboard_thread():
	global lb_downvotes_received, lb_upvotes_given

	db: Session = db_session()

	lb_downvotes_received = ReceivedDownvotesLeaderboard(_lb_received_downvotes_meta, db)
	lb_upvotes_given = GivenUpvotesLeaderboard(_lb_given_upvotes_meta, db)

	db.close()
	sys.stdout.flush()

if service.enable_services and ENABLE_SERVICES:
	gevent.spawn(leaderboard_thread())
