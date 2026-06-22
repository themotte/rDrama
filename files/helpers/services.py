import sys

from pusher_push_notifications import PushNotifications

from files.__main__ import service
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
					'deep_link': f'{SITE_FULL}/notifications/messages',
					'icon': SITE_FULL + assetcache_path(f'images/{SITE_ID}/icon.webp'),
				}
			},
			'fcm': {
				'notification': {
					'title': f'New message from @{username}',
					'body': notifbody,
				},
				'data': {
					'url': '/notifications/messages',
				}
			}
		},
	)
	sys.stdout.flush()
