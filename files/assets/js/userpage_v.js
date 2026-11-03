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
	for (elementId in ['message', 'message-mobile', 'message-preview', 'message-preview-mobile']) {
		const element = document.getElementById(elementId);
		if (element !== null) {
			element.classList.add("d-none");
		}
	}
	
	const form = e.target;
	postToast(null, form.getAttribute("action"), "POST", form, null);
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
