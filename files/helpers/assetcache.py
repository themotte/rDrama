import os
import zlib
from collections import defaultdict

ASSET_DIR = 'files/assets'
ASSET_CACHE = defaultdict(lambda: None)

def assetcache_build(asset_dir):
	for root, dirs, files in os.walk(asset_dir):
		for fname in files:
			fpath = root + '/' + fname
			relpath = fpath[len(asset_dir) + 1:].replace('\\', '/')
			with open(fpath, 'rb') as f:
				fhash = zlib.crc32(f.read())
				ASSET_CACHE[relpath] = '%x' % fhash

def assetcache_get(path):
	return ASSET_CACHE[path]

assetcache_build(ASSET_DIR)
