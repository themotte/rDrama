import os
import posixpath
import re
import zlib
from collections import defaultdict

ASSET_DIR = 'files/assets'
ASSET_URL = '/assets/'
ASSET_CACHE = defaultdict(lambda: None)
ASSET_CSS: dict[str, bytes] = {}
'''Stylesheets as served: their references to other site files carry those files' versions.'''

# A stylesheet's references: url(...) and @import "..."; the reference itself, then any version it already carries
_CSS_REFERENCE = re.compile(r"""(url\(\s*['"]?|@import\s+['"])([^'")?\s]+)(\?v=[^'")\s]*)?""")


def _version_stylesheet(asset_dir, relpath):
	if relpath in ASSET_CSS: return

	def versioned(match):
		prefix, ref, _ = match.groups()
		if ref.startswith(("data:", "http:", "https:", "//")): return match[0]
		target = ref[len(ASSET_URL):] if ref.startswith(ASSET_URL) else posixpath.normpath(posixpath.join(posixpath.dirname(relpath), ref))
		if target.endswith(".css"): _version_stylesheet(asset_dir, target)
		version = ASSET_CACHE.get(target)
		return f"{prefix}{ref}?v={version}" if version else match[0]

	with open(f"{asset_dir}/{relpath}", encoding="utf-8") as f:
		served = _CSS_REFERENCE.sub(versioned, f.read()).encode("utf-8")
	ASSET_CSS[relpath] = served
	# Covers the versions it carries, so a changed font gives its stylesheets new addresses too
	ASSET_CACHE[relpath] = '%x' % zlib.crc32(served)


def assetcache_build(asset_dir):
	stylesheets = []
	for root, dirs, files in os.walk(asset_dir):
		for fname in files:
			fpath = root + '/' + fname
			relpath = fpath[len(asset_dir) + 1:].replace('\\', '/')
			if relpath.endswith(".css"):
				stylesheets.append(relpath)
				continue
			with open(fpath, 'rb') as f:
				fhash = zlib.crc32(f.read())
				ASSET_CACHE[relpath] = '%x' % fhash
	for relpath in stylesheets:
		_version_stylesheet(asset_dir, relpath)

def assetcache_hash(asset_path):
	return ASSET_CACHE.get(asset_path)

def assetcache_path(asset_path):
	cachehash = assetcache_hash(asset_path)

	url = ASSET_URL + asset_path
	if cachehash:
		url += '?v=' + cachehash

	return url

assetcache_build(ASSET_DIR)
