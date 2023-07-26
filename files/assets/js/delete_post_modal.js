function delete_postModal(id) {
	document.getElementById("deletePostButton").onclick = () => postToast(null, `/delete_post/${id}`, 'POST', null, (xhr) => {
		if (xhr.status >= 200 && xhr.status < 300) {
			document.getElementById(`post-${id}`).classList.add('deleted');
			document.getElementById(`delete-${id}`).classList.add('d-none');
			document.getElementById(`undelete-${id}`).classList.remove('d-none');
			document.getElementById(`delete2-${id}`).classList.add('d-none');
			document.getElementById(`undelete2-${id}`).classList.remove('d-none');
		}
	})};
}
