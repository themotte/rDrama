from files.__main__ import cache
import files.helpers.listing as listing

# i hate this.
#
# we should probably come up with a better way for this in the future. 
# flask_caching is kinda weird in that it requires you to use a function 
# reference to deleted a memoized function, which basically means fitting your
# code to flask_caching's worldview. it's very much not ideal and ideally would
# be less coupled in the future.
# 
# the question is whether it's worth it.

def invalidate_cache(*, frontlist=False, userpagelisting=False, changeloglist=False):
	'''
	Invalidates the caches for the front page listing, user page listings,
	and optionally, the changelog listing.
	
	:param frontlist: Whether to invalidate the `frontlist` cache.
	:param userpagelisting: Whether to invalidate the `userpagelisting` cache.
	:param changeloglist: Whether to invalidate the `changeloglist` cache.
	'''
	if frontlist: cache.delete_memoized(listing.frontlist)
	if userpagelisting: cache.delete_memoized(listing.userpagelisting)
	if changeloglist: cache.delete_memoized(listing.changeloglist)
