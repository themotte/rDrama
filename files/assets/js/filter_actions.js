function filter_new_status(id, new_status) {
	fetch('/admin/update_filter_status', {
	  method: 'POST',
	  body: JSON.stringify({ post_id: id, new_status: new_status, formkey: formkey() }),
	  headers: { 'content-type': 'application/json' }
	})
		.then(response => response.json())
		.then(json => {
		  if(json.result === 'Update successful') {
				const postRow = document.getElementById(`post-${id}`);
				if(document.location.pathname === '/admin/filtered/posts' || document.location.pathname === '/admin/reported/posts' ) {
					postRow.parentElement.removeChild(postRow);
				} else if(document.location.pathname.startsWith('/post/')) {
					const flaggerBox = document.getElementById('flaggers');
					if(flaggerBox) {
						flaggerBox.parentElement.removeChild(flaggerBox);
					}
					const flaggerButton = document.getElementById('submission-report-button');
					if(flaggerButton) {
						flaggerButton.parentElement.removeChild(flaggerButton);
					}
				} else {
					const approveLink = postRow.querySelector('a#filter-approve')
					const removeLink = postRow.querySelector('a#filter-remove')
					if(approveLink && removeLink) {
						approveLink.parentElement.removeChild(approveLink);
						removeLink.parentElement.removeChild(removeLink);
					}

					const reportButtonCell = document.getElementById(`flaggers-${id}`);
					if(reportButtonCell) {
						reportButtonCell.classList.add('d-none')
					}

					const reportButton = document.getElementById(`report-btn-${id}`);
					if(reportButton) {
						reportButton.parentElement.removeChild(reportButton);
					}
				}

				document.getElementById('toast-post-success-text').innerText = json.result;
				bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-success')).show();
		  } else {
				document.getElementById('toast-post-error-text').innerText = "Error, please try again later."
				bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error')).show();
		  }
		});
}

function filter_new_comment_status(id, new_status) {
	fetch('/admin/update_filter_status', {
	  method: 'POST',
	  body: JSON.stringify({ comment_id: id, new_status: new_status, formkey: formkey() }),
	  headers: { 'content-type': 'application/json' }
	})
		.then(response => response.json())
		.then(json => {
		  if(json.result === 'Update successful') {
				const commentRow = document.getElementById(`comment-${id}`);
				if(document.location.pathname === '/admin/filtered/comments' || document.location.pathname === '/admin/reported/comments' ) {
					commentRow.parentElement.removeChild(commentRow);
					const postRow = document.querySelector(`div.post-row-cid-${id}`);
					if (postRow) {
						postRow.parentElement.removeChild(postRow);
					}
				} else {
					const approveLink = commentRow.querySelector('button#filter-approve')
					const removeLink = commentRow.querySelector('button#filter-remove')
					if(approveLink && removeLink) {
						approveLink.parentElement.removeChild(approveLink);
						removeLink.parentElement.removeChild(removeLink);
					}

					const reportButtonCell = document.getElementById(`flaggers-${id}`);
					if(reportButtonCell) {
						reportButtonCell.classList.add('d-none')
					}

					const reportButton = document.getElementById(`report-btn-${id}`);
					if(reportButton) {
						reportButton.parentElement.removeChild(reportButton);
					}
				}

				document.getElementById('toast-post-success-text').innerText = json.result;
				bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-success')).show();
			} else {
				document.getElementById('toast-post-error-text').innerText = "Error, please try again later."
				bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error')).show();
			}
		});
}
