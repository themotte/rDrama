import os
import zlib
from collections import defaultdict

ASSET_DIR = 'files/assets'
ASSET_URL = '/assets/'
ASSET_CACHE = defaultdict(lambda: None)

def assetcache_build(asset_dir):
	for root, dirs, files in os.walk(asset_dir):
		for fname in files:
			fpath = root + '/' + fname
			relpath = fpath[len(asset_dir) + 1:].replace('\\', '/')
			with open(fpath, 'rb') as f:
				fhash = zlib.crc32(f.read())
				ASSET_CACHE[relpath] = '%x' % fhash

def assetcache_hash(asset_path):
	return ASSET_CACHE[asset_path]

def assetcache_path(asset_path):
	cachehash = assetcache_hash(asset_path)

	url = ASSET_URL + asset_path
	if cachehash:
		url += '?v=' + cachehash

	return url

assetcache_build(ASSET_DIR)
