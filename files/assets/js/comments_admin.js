function removeCommentBackend(post_id) {
	url="/remove_comment/"+post_id

	post(url)
}

function approveCommentBackend(post_id) {
	url="/unremove_comment/"+post_id

	post(url)
}

function removeCommentDesktop(post_id,button1,button2) {
	removeCommentBackend(post_id)

	try {
		document.getElementById("comment-"+post_id+"-only").classList.add("banned");
	} catch(e) {
		document.getElementById("context").classList.add("banned");
	}

	var button=document.getElementById("remove-"+post_id);
	button.onclick=function(){approveCommentDesktop(post_id)};
	button.innerHTML='<i class="fas fa-clipboard-check"></i>Approve'

	if (typeof button1 !== 'undefined') {
		document.getElementById(button1).classList.toggle("d-md-inline-block");
		document.getElementById(button2).classList.toggle("d-md-inline-block");
	}
};

function approveCommentDesktop(post_id,button1,button2) {
	approveCommentBackend(post_id)

	try {
		document.getElementById("comment-"+post_id+"-only").classList.remove("banned");
	} catch(e) {
		document.getElementById("context").classList.remove("banned");
	}
	
	var button=document.getElementById("remove-"+post_id);
	button.onclick=function(){removeCommentDesktop(post_id)};
	button.innerHTML='<i class="fas fa-trash-alt"></i>Remove'

	if (typeof button1 !== 'undefined') {
		document.getElementById(button1).classList.toggle("d-md-inline-block");
		document.getElementById(button2).classList.toggle("d-md-inline-block");
	}
}


function removeCommentMobile(post_id,button1,button2) {
	removeCommentBackend(post_id)

	document.getElementById("comment-"+post_id+"-only").classList.add("banned");
	var button=document.getElementById("remove-"+post_id);
	button.onclick=function(){approveCommentMobile(post_id)};
	button.innerHTML='<i class="fas fa-clipboard-check"></i>Approve'

	if (typeof button1 !== 'undefined') {
		document.getElementById(button1).classList.toggle("d-none");
		document.getElementById(button2).classList.toggle("d-none");
	}
};

function approveCommentMobile(post_id,button1,button2) {
	approveCommentBackend(post_id)

	document.getElementById("comment-"+post_id+"-only").classList.remove("banned");
	var button=document.getElementById("remove-"+post_id);
	button.onclick=function(){removeCommentMobile(post_id)};
	button.innerHTML='<i class="fas fa-trash-alt"></i>Remove'

	if (typeof button1 !== 'undefined') {
		document.getElementById(button1).classList.toggle("d-none");
		document.getElementById(button2).classList.toggle("d-none");
	}
}
