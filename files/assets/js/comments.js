var closedCommentsKey = null;
var closedComments = [];

function collapsedCommentStorageInit(pageKey) {
	closedCommentsKey = `closedcomments_${pageKey}`;
}

function collapsedCommentStorageApply() {
	if (!closedCommentsKey) {
		return;
	}

	var closedCommentsValue = localStorage.getItem(closedCommentsKey);
	if (closedCommentsValue === null) {
		closedComments = [];
	} else {
		closedComments = JSON.parse(closedCommentsValue);
	}

	closedComments.forEach((commentId) => {
		try {
			document.getElementById(`comment-${commentId}`).classList.add("collapsed");
		} catch (e) {}
	})
}

function collapse_comment(id, element) {
	const closed = element.classList.toggle("collapsed")
	const top = element.getBoundingClientRect().y

	if (closed && top < 0) {
		element.scrollIntoView()
		window.scrollBy(0, - 100)
	}

	const flags = document.getElementById(`flaggers-${id}`)
	if (flags) flags.classList.add('d-none')

	if (closed && !closedComments.includes(id)) {
		closedComments.push(id);
	} else if (!closed && closedComments.includes(id)) {
		closedComments.splice(closedComments.indexOf(id), 1);
	}
	if (closedCommentsKey) {
		localStorage.setItem(closedCommentsKey, JSON.stringify(closedComments));
	}
};

function expandMarkdown(t,id) {
	let ta = document.getElementById('markdown-'+id);
	ta.classList.toggle('d-none');
	autoExpand(ta);
	document.getElementsByClassName('text-expand-icon-'+id)[0].classList.toggle('fa-expand-alt');
	document.getElementsByClassName('text-expand-icon-'+id)[0].classList.toggle('fa-compress-alt');

	let val = t.getElementsByTagName('span')[0]
	if (val.innerHTML == 'View source') val.innerHTML = 'Hide source'
	else val.innerHTML = 'View source'
};
