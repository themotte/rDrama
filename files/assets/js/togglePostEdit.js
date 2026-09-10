const togglePostEdit = (id) =>	{
	const body = document.getElementById("post-body");
	const title = document.getElementById("post-title");
	const form = document.getElementById(`edit-post-body-${id}`);
	const box = document.getElementById(`post-edit-box-${id}`);

	// Init preview and char count
	box.oninput();

	body.classList.toggle("d-none");
	title.classList.toggle("d-none");
	form.classList.toggle("d-none");
	autoExpand(box);
};
