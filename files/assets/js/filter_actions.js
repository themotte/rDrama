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
			if(document.location.pathname === '/admin/filtered_submissions' || document.location.pathname === '/admin/reported/posts' ) {
				postRow.parentElement.removeChild(postRow);
			}

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

			document.getElementById('toast-post-success-text').innerText = json.result;
			bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-success')).show();
		  } else {
			document.getElementById('toast-post-error-text').innerText = "Error, please try again later."
			bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error')).show();
		  }
		});
}
