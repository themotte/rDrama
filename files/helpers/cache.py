from flask import request

def make_cache_key(*args, **kwargs): 
	return request.base_url
