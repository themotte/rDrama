'''
Rate limiting: which client a request counts against.
'''
from flask import request


def client_address() -> str:
	'''The client a request comes from: the address in its X-Real-IP header, set by the proxy in front of the site, or, without one, the connection's peer.'''
	real_ip = (request.headers.get('X-Real-IP') or '').strip()
	return real_ip or request.remote_addr
