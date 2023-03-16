from files.__main__ import cache
import files.helpers.listing as listing

# i hate this.
#
# we should probably come up with a better way for this in the future. 
# flask_caching is kinda weird in that it requires you to use a function 
# reference to deleted a memoized function, which basically means fitting your
# code to flask_caching's worldview. it's not very 
# the question is whether it's worth it.

def invalidate_cache(*, frontlist=True, userpagelisting=False, changeloglist=False):
	'''
	Invalidates the caches for the front page listing, user page listings,
	and optionally, the changelog listing.
	'''
	if frontlist: cache.delete_memoized(listing.frontlist)
	if userpagelisting: cache.delete_memoized(listing.userpagelisting)
	if changeloglist: cache.delete_memoized(listing.changeloglist)