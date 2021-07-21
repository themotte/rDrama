import flask_caching
from flask_caching import backends
import hashlib


class CustomCache(backends.rediscache.RedisCache):

	def __init__(self, app, config, *args):

		self.caches = [
			flask_caching.Cache(
				app,
				config={"CACHE_TYPE": 'redis',
						"CACHE_REDIS_URL": url}
			) for url in app.config['redis_urls']
		]

	def key_to_cache(self, key):

		return self.caches[self.key_to_cache_number(key)]

	def key_to_cache_number(self, key):

		return int(hashlib.md5(bytes(key, 'utf-8')).hexdigest()
				   [-5:], 16) % len(self.caches)

	def sharded_keys(self, keys, return_index=False):

		sharded_keys = {i: [] for i in range(len(self.caches))}
		idx = {}
		for key in keys:
			cache = self.key_to_cache_number(key)
			sharded_keys[cache].append(key)
			idx[key] = [cache, len(sharded_keys[cache]) - 1]

		if not return_index:
			return sharded_keys
		else:
			return sharded_keys, idx

	def get(self, key):

		cache = self.key_to_cache(key)

		return cache.get(key)

	def get_many(self, *keys):

		sharded_keys, idx = self.sharded_keys(keys, return_index=True)

		objects = {i: self.caches[i].get_many(
			*sharded_keys[i]) for i in range(len(self.caches))}

		output = [objects[idx[key][0]][idx[key][1]] for key in keys]

		return output

	def set(self, key, value, timeout=None):
		cache = self.key_to_cache(key)
		return cache.set(key, value, timeout=timeout)

	def add(self, key, value, timeout=None):
		cache = self.key_to_cache(key)
		return cache.add(key, value, timeout=timeout)

	def set_many(self, mapping, timeout=None):

		caches = {i: {} for i in range(len(self.caches))}
		for key in mapping:
			caches[self.key_to_cache_number(key)][key] = mapping[key]

		for i in caches:
			self.caches[i].set_many(caches[i], timeout=timeout)

	def delete(self, key):

		cache = self.key_to_cache(key)
		return cache.delete(key)

	def delete_many(self, *keys):

		if not keys:
			return

		sharded_keys = self.sharded_keys(keys)

		for i in sharded_keys:
			self.caches[i].delete_many(*sharded_keys[i])

		return True

	def has(self, key):
		cache = self.key_to_cache(key)
		return cache.has(key)

	def clear(self):

		return any([i.clear() for i in self.caches])

	def inc(self, key, delta=1):
		cache = self.key_to_cache(key)
		cache.inc(key, delta=delta)

	def dec(self, key, delta=1):
		cache = self.key_to_cache(key)
		cache.dec(key, delta=delta)

	def unlink(self, *keys):

		if not keys:
			return

		sharded_keys = self.sharded_keys(keys)

		for i in sharded_keys:
			self.caches[i].unlink(*sharded_keys[i])

		return True
