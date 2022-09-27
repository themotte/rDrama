function post_toast3(t, url, button1, button2) {
	t.disabled=true;
	t.classList.add("disabled");
	const xhr = new XMLHttpRequest();
	xhr.open("POST", url);
	xhr.setRequestHeader('xhr', 'xhr');
	var form = new FormData()
	form.append("formkey", formkey());

	if(typeof data === 'object' && data !== null) {
		for(let k of Object.keys(data)) {
				form.append(k, data[k]);
		}
	}

	xhr.onload = function() {
		let data
		try {data = JSON.parse(xhr.response)}
		catch(e) {console.log(e)}
		if (xhr.status >= 200 && xhr.status < 300 && data && data["message"]) {
			document.getElementById('toast-post-success-text').innerText = data["message"];
			bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-success')).show();

			document.getElementById(button1).classList.toggle("d-md-inline-block");
			document.getElementById(button2).classList.toggle("d-md-inline-block");
		
		} else {
			document.getElementById('toast-post-error-text').innerText = "Error, please try again later."
			if (data && data["error"]) document.getElementById('toast-post-error-text').innerText = data["error"];
			bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error')).show();
		}
		setTimeout(() => {
			t.disabled = false;
			t.classList.remove("disabled");
		}, 2000);
	};

	xhr.send(form);
}

function report_commentModal(id, author) {
	document.getElementById("comment-author").textContent = author;

	const wholeFormBefore = document.getElementById('reportCommentFormBefore');
	const wholeFormAfter = document.getElementById('reportCommentFormAfter');
	const submitButton = document.getElementById("reportCommentButton")
	const reasonField = document.getElementById("reason-field")

	//The HTML is reused if the user makes multiple reports without a reload, so clean up
	//from any previous openings
	wholeFormBefore.classList.remove('d-none');
	wholeFormAfter.classList.add('d-none');
	submitButton.disabled = true;
	submitButton.classList.add('disabled');
	submitButton.innerHTML = 'Report comment';
	reasonField.value = ""
	reasonField.disabled = true;
	for (const radioButton of document.querySelectorAll('input[name="report-reason"]')) {
		radioButton.checked = false;
	}

	const otherButton = document.querySelector('input#other');
	function handleRadioButtonChange() {
		submitButton.disabled = false;
		submitButton.classList.remove('disabled');
		reasonField.disabled = !otherButton.checked;
		if (!otherButton.checked) {
			reasonField.value = "";
		}
	};
	wholeFormBefore.addEventListener('change', handleRadioButtonChange);

	submitButton.onclick = function() {
		this.innerHTML = 'Reporting comment';
		this.disabled = true;
		this.classList.add('disabled');

		const xhr = new XMLHttpRequest();
		xhr.open("POST", '/report/comment/'+id);
		xhr.setRequestHeader('xhr', 'xhr');
		var form = new FormData()
		form.append("formkey", formkey());
		let reasonValue;
		if (otherButton.checked) {
			reasonValue = reasonField.value;
		} else {
			reasonValue = document.querySelector('input[name="report-reason"]:checked').value;
		}
		form.append("reason", reasonValue);

		xhr.onload=function() {
			wholeFormBefore.classList.add('d-none');
			wholeFormAfter.classList.remove('d-none');
			wholeFormBefore.removeEventListener('change', handleRadioButtonChange);
		};

		xhr.onerror=function(){alert(errortext)};
		xhr.send(form);
	}
};

function openReplyBox(id) {
	const element = document.getElementById(id);
	const textarea = element.getElementsByTagName('textarea')[0]
	let text = getSelection().toString()
	if (text)
	{
		textarea.value = '>' + text
		textarea.value = textarea.value.replace(/\n\n([^$])/g,"\n\n>$1")
		if (!textarea.value.endsWith('\n\n')) textarea.value += '\n\n'
	}
	element.classList.remove('d-none')
	textarea.focus()
}

function toggleEdit(id){
	comment=document.getElementById("comment-text-"+id);
	form=document.getElementById("comment-edit-"+id);
	box=document.getElementById('comment-edit-body-'+id);
	actions = document.getElementById('comment-' + id +'-actions');

	comment.classList.toggle("d-none");
	form.classList.toggle("d-none");
	actions.classList.toggle("d-none");
	autoExpand(box);
};


function delete_commentModal(id) {
	document.getElementById("deleteCommentButton").onclick =  function() {
		const xhr = new XMLHttpRequest();
		xhr.open("POST", `/delete/comment/${id}`);
		xhr.setRequestHeader('xhr', 'xhr');
		var form = new FormData()
		form.append("formkey", formkey());
		xhr.onload = function() {
			let data
			try {data = JSON.parse(xhr.response)}
			catch(e) {console.log(e)}
			if (xhr.status >= 200 && xhr.status < 300 && data && data['message']) {
				document.getElementsByClassName(`comment-${id}-only`)[0].classList.add('deleted');
				document.getElementById(`delete-${id}`).classList.add('d-none');
				document.getElementById(`undelete-${id}`).classList.remove('d-none');
				document.getElementById(`delete2-${id}`).classList.add('d-none');
				document.getElementById(`undelete2-${id}`).classList.remove('d-none');
				document.getElementById('toast-post-success-text').innerText = data["message"];
				bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-success')).show();
			} else {
				document.getElementById('toast-post-error-text').innerText = "Error, please try again later."
				if (data && data["error"]) document.getElementById('toast-post-error-text').innerText = data["error"];
				bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error')).show();
			}
		};
		xhr.send(form);
	};
}

function post_reply(id){
	const btn = document.getElementById(`save-reply-to-${id}`)
	btn.disabled = true;
	btn.classList.add('disabled');

	var form = new FormData();
	form.append('formkey', formkey());
	form.append('parent_id', id);
	form.append('body', document.getElementById('reply-form-body-'+id).value);

	try {
		for (const e of document.getElementById('file-upload').files)
			form.append('file', e);
	}
	catch(e) {}

	const xhr = new XMLHttpRequest();
	xhr.open("post", "/reply");
	xhr.setRequestHeader('xhr', 'xhr');
	xhr.onload=function(){
		let data
		try {data = JSON.parse(xhr.response)}
		catch(e) {console.log(e)}
		if (data && data["comment"]) {
			commentForm=document.getElementById('comment-form-space-'+id);
			commentForm.innerHTML = data["comment"].replace(/data-src/g, 'src').replace(/data-cfsrc/g, 'src').replace(/style="display:none;visibility:hidden;"/g, '').replace('comment-collapse-desktop d-none d-md-block','d-none').replace('border-left: 2px solid','padding-left:0;border-left: 0px solid');
			bs_trigger(commentForm);
		}
		else {
			if (data && data["error"]) document.getElementById('toast-post-error-text').innerText = data["error"];
			else document.getElementById('toast-post-error-text').innerText = "Error, please try again later."
			bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error')).show();
		}
		setTimeout(() => {
			btn.disabled = false;
			btn.classList.remove('disabled');
		}, 2000);
	}
	xhr.send(form)
}

function comment_edit(id){
	const btn = document.getElementById(`edit-btn-${id}`)
	btn.disabled = true
	btn.classList.add('disabled');

	var form = new FormData();

	form.append('formkey', formkey());
	form.append('body', document.getElementById('comment-edit-body-'+id).value);

	try {
		for (const e of document.getElementById('file-edit-reply-'+id).files)
			form.append('file', e);
	}
	catch(e) {}

	const xhr = new XMLHttpRequest();
	xhr.open("post", "/edit_comment/"+id);
	xhr.setRequestHeader('xhr', 'xhr');
	xhr.onload=function(){
		let data
		try {data = JSON.parse(xhr.response)}
		catch(e) {console.log(e)}
		if (data && data["comment"]) {
			commentForm=document.getElementById('comment-text-'+id);
			commentForm.innerHTML = data["comment"].replace(/data-src/g, 'src').replace(/data-cfsrc/g, 'src').replace(/style="display:none;visibility:hidden;"/g, '')
			document.getElementById('cancel-edit-'+id).click()
			bs_trigger(commentForm);
		}
		else {
			if (data && data["error"]) document.getElementById('toast-post-error-text').innerText = data["error"];
			else document.getElementById('toast-post-error-text').innerText = "Error, please try again later."
			bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error')).show();
		}
		setTimeout(() => {
			btn.disabled = false;
			btn.classList.remove('disabled');
		}, 2000);
	}
	xhr.send(form)
}


function post_comment(fullname,id,level = 1){
	const previewPlaceholderHTML= '<p class="preview-msg">Comment preview</p>';
	function reset_preview(element_id) {
		const element = document.getElementById(element_id);
		if (element) {
			element.innerHTML = previewPlaceholderHTML;
			return true;
		}
		return false;
	}

	const btn = document.getElementById('save-reply-to-'+fullname)
	btn.disabled = true
	btn.classList.add('disabled');

	var form = new FormData();
	let submissionEl = document.getElementById('reply-form-submission-'+fullname);
	let bodyEl = document.getElementById('reply-form-body-'+fullname);

	form.append('formkey', formkey());
	form.append('parent_fullname', fullname);
	form.append('parent_level', level);
	form.append('submission', submissionEl.value);
	form.append('body', bodyEl.value);

	try {
		for (const e of document.getElementById('file-upload-reply-'+fullname).files)
			form.append('file', e);
	}
	catch(e) {}

	const xhr = new XMLHttpRequest();
	xhr.open("post", "/comment");
	xhr.setRequestHeader('xhr', 'xhr');
	xhr.onload=function(){
		let data
		try {data = JSON.parse(xhr.response)}
		catch(e) {console.log(e)}
		if (data && data["comment"]) {
			let id = fullname.split('_')[1];
			let name = 'comment-form-space-' + fullname;
			commentForm = document.getElementById(name);

			// dynamically insert comment into the comments section of the current comment/post
			let comments = document.getElementById('replies-of-' + id);
			let comment = data["comment"].replace(/data-src/g, 'src').replace(/data-cfsrc/g, 'src').replace(/style="display:none;visibility:hidden;"/g, '');

			comments.innerHTML = comment + comments.innerHTML;

			bs_trigger(commentForm);

			// remove the placeholder if it exists
			let placeholder = document.getElementById("placeholder-comment");
			if(placeholder){
				// clear out the text-center classes etc.
				comments.classList.remove('text-center');
				comments.classList.remove('py-7');
				placeholder.parentNode.removeChild(placeholder);
			}

			// clear comment textarea, and preview.
			bodyEl.value = '';
			// when called from top-level comment, clear top-level preview
			reset_preview('form-preview-'+id);
			// when called from comment reply, clear comment reply preview
			if(reset_preview('reply-edit-'+id)) {
				// We are in a comment reply, need to find and hide the comment section
				const replyArea = document.getElementById(`reply-to-${id}`);
				if (replyArea) {
					replyArea.classList.add('d-none');
				}
			}
		}
		else {
			if (data && data["error"]) document.getElementById('toast-post-error-text').innerText = data["error"];
			else document.getElementById('toast-post-error-text').innerText = "Error, please try again later."
			bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error')).show();
		}
		setTimeout(() => {
			btn.disabled = false;
			btn.classList.remove('disabled');
		}, 2000);
	}
	xhr.send(form)
}

document.onpaste = function(event) {
	var focused = document.activeElement;
	if (focused.id.includes('reply-form-body-')) {
		var fullname = focused.dataset.fullname;
		f=document.getElementById('file-upload-reply-' + fullname);
		files = event.clipboardData.files
		try {
			filename = files[0].name.toLowerCase()
			if (filename.endsWith(".jpg") || filename.endsWith(".jpeg") || filename.endsWith(".png") || filename.endsWith(".webp") || filename.endsWith(".gif"))
			{
				f.files = files;
				document.getElementById('filename-show-reply-' + fullname).textContent = filename;
			}
		}
		catch(e) {console.log(e)}
	}
	else if (focused.id.includes('comment-edit-body-')) {
		var id = focused.dataset.id;
		f=document.getElementById('file-edit-reply-' + id);
		files = event.clipboardData.files
		filename = files[0].name.toLowerCase()
		if (filename.endsWith(".jpg") || filename.endsWith(".jpeg") || filename.endsWith(".png") || filename.endsWith(".webp") || filename.endsWith(".gif"))
		{
			f.files = files;
			document.getElementById('filename-edit-reply-' + id).textContent = filename;
		}
	}
	else if (focused.id.includes('post-edit-box-')) {
		var id = focused.dataset.id;
		f=document.getElementById('file-upload-edit-' + id);
		files = event.clipboardData.files
		filename = files[0].name.toLowerCase()
		if (filename.endsWith(".jpg") || filename.endsWith(".jpeg") || filename.endsWith(".png") || filename.endsWith(".webp") || filename.endsWith(".gif"))
		{
			f.files = files;
			document.getElementById('filename-show-edit-' + id).textContent = filename;
		}
	}
}

function handle_action(type, cid, thing) {


	const btns = document.getElementsByClassName(`action-${cid}`)
	for (const btn of btns)
	{
		btn.disabled = true;
		btn.classList.add('disabled');
	}

	const form = new FormData();
	form.append('formkey', formkey());
	form.append('comment_id', cid);
	form.append('thing', thing);
	
	const xhr = new XMLHttpRequest();
	xhr.open("post", `/${type}/${cid}`);
	xhr.setRequestHeader('xhr', 'xhr');



	xhr.onload=function(){
		let data
		try {data = JSON.parse(xhr.response)}
		catch(e) {console.log(e)}
		if (data && data["response"]) {
			const element = document.getElementById(`${type}-${cid}`);
			element.innerHTML = data["response"]
		}
		else {
			if (data && data["error"]) document.getElementById('toast-post-error-text').innerText = data["error"];
			else document.getElementById('toast-post-error-text').innerText = "Error, please try again later."
			bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error')).show();
		}
		setTimeout(() => {
			for (const btn of btns)
			{		
				btn.disabled = false;
				btn.classList.remove('disabled');
			}
		}, 2000);
	}
	xhr.send(form)
}
