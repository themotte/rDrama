function toggleElement(id, id2) {
	for(let el of document.getElementsByClassName('toggleable')) {
		if(el.id != id) {
			el.classList.add('d-none');
		}
	}

	document.getElementById(id).classList.toggle('d-none');
	document.getElementById(id2).focus()
}

function submitFormAjax(e) {
	const form = e.target;
	postToast(null, form.getAttribute("action"), "POST", form, null);

	// The message has been read from the form: put the message box away, and empty its preview so it starts afresh when opened again
	for (const formId of ['message', 'message-mobile']) {
		document.getElementById(formId)?.classList.add("d-none");
	}
	for (const previewId of ['message-preview', 'message-preview-mobile']) {
		const preview = document.getElementById(previewId);
		if (preview !== null) {
			preview.innerHTML = "";
		}
	}
	return false;
}

function showShadowbanModal(username, userId, shadowbanId, unshadowbanId) {
	document.getElementById('shadowbanUsername').textContent = username;
	
	const confirmButton = document.getElementById('confirmShadowban');
	confirmButton.onclick = function() {
		const shadowbanButton = document.getElementById(shadowbanId);
		postToastSwitch(shadowbanButton, `/shadowban/${userId}`, 'POST', shadowbanId, unshadowbanId);
		
		const modal = bootstrap.Modal.getInstance(document.getElementById('shadowbanModal'));
		if (modal) {
			modal.hide();
		}
	};
	
	const modal = new bootstrap.Modal(document.getElementById('shadowbanModal'));
	modal.show();
}
