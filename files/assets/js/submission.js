function togglePostEdit(id){
	body=document.getElementById("post-body");
	title=document.getElementById("post-title");
	form=document.getElementById("edit-post-body-"+id);
	box=document.getElementById("post-edit-box-"+id);

	body.classList.toggle("hidden");
	title.classList.toggle("hidden");
	form.classList.toggle("hidden");
	autoExpand(box);
};
