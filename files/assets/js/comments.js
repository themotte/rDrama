function collapse_comment(comment_id) {
	const c = "#comment-" + comment_id
	document.querySelectorAll(c).forEach(n => n.classList.toggle('collapsed'))
	const flags = document.getElementById(`flaggers-${comment_id}`)
	if (flags) flags.classList.add('d-none')
};

function poll_vote_no_v() {
	document.getElementById('toast-post-error-text').innerText = "Only logged-in users can vote!";
	bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error')).show();
}

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