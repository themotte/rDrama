// only allows the script to execute once
if (typeof showNewCommentCounts === 'undefined') {

	// localstorage comment counts format: {"<postId>": {c: <totalComments>, t: <timestampUpdated>}}
	/**
		* Display the number of new comments present since the last time the post was opened
		*/
	function showNewCommentCounts(postId, newTotal) {
		const comments = JSON.parse(localStorage.getItem("comment-counts")) || {}

		const lastCount = comments[postId]
		if (lastCount) {
			const newComments = newTotal - lastCount.c
			if (newComments > 0) {
				document.querySelectorAll(`#post-${postId} .new-comments`).forEach(elem => {
					elem.textContent = ` (+${newComments})`
					elem.classList.remove("d-none")
				})
			}
		}
	}

	/**
		* Saves the comment count to the localStorage
		*
		* @param postId The id of the post associated with the comments
		* @param lastTotalComs The new amount, If null it will just increment the previous amount
		*/
	function saveCommentsCount(postId, lastTotalComs = null) {
		const comments = JSON.parse(localStorage.getItem("comment-counts")) || {}

		const newTotal = lastTotalComs || ((comments[postId] || { c: 0 }).c + 1)

		var t = Date.now()
		t = (t-(t%1000))/1000
		console.log(t)
		comments[postId] = { c: newTotal, t: t }

		window.localStorage.setItem("comment-counts", JSON.stringify(comments))
	}


	/**
		* Cleans the expired entries (5 days). It runs every hour.
		*/
	function cleanCommentsCache() {
		const LAST_CACHE_CLEAN_ID = "last-cache-clean"
		const EXPIRE_INTERVAL_MILLIS = 5 * 24 * 60 * 60 * 1000
		const CACHE_CLEAN_INTERVAL = 60 * 60 * 1000 // 1 hour

		function cleanCache() {
			const lastCacheClean = JSON.parse(localStorage.getItem(LAST_CACHE_CLEAN_ID)) || Date.now()
			const now = Date.now()

			if (now - lastCacheClean > CACHE_CLEAN_INTERVAL) {
				const comments = JSON.parse(localStorage.getItem("comment-counts")) || {}

				for (let [key, value] of Object.entries(comments)) {
					if (now - value.t > EXPIRE_INTERVAL_MILLIS) {
						delete comments[key]
					}
				}
				window.localStorage.setItem("comment-counts", JSON.stringify(comments))
			}
			window.localStorage.setItem(LAST_CACHE_CLEAN_ID, JSON.stringify(now))
		}

		// So it does not slow the load of the main page with the clean up
		setTimeout(cleanCache, 500)
	}

	cleanCommentsCache()

}