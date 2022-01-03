function initializeBootstrap() {
    // tooltips
    let tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(element){
    	return new bootstrap.Tooltip(element);
    });
    // popovers
    let popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    let popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
    	let popoverId = popoverTriggerEl.getAttribute('data-content-id');
    	let contentEl = document.getElementById(popoverId);
    	if (contentEl) {
    		return new bootstrap.Popover(popoverTriggerEl, {
    			content: contentEl.innerHTML,
    			html: true,
    			sanitize: false
    		});
    	}
    })
}

document.addEventListener("DOMContentLoaded", function(){
	initializeBootstrap()
});

function post(url) {
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	var form = new FormData()
	form.append("formkey", formkey());
	xhr.withCredentials=true;
	xhr.send(form);
};

function formkey() {
	let formkey = document.getElementById("formkey")
	if (formkey) return formkey.innerHTML;
	else return null;
}

function makeBold(form) {
	var text = document.getElementById(form);
	var startIndex = text.selectionStart,
	endIndex = text.selectionEnd;
	var selectedText = text.value.substring(startIndex, endIndex);

	var format = '**'

	if (selectedText.includes('**')) {
		text.value = selectedText.replace(/\*/g, '');
	}
	else if (selectedText.length == 0) {
		text.value = text.value.substring(0, startIndex) + selectedText + text.value.substring(endIndex);
	}
	else {
		text.value = text.value.substring(0, startIndex) + format + selectedText + format + text.value.substring(endIndex);
	}
}

function makeItalics(form) {
	var text = document.getElementById(form);
	var startIndex = text.selectionStart,
	endIndex = text.selectionEnd;
	var selectedText = text.value.substring(startIndex, endIndex);

	var format = '*'

	if (selectedText.includes('*')) {
		text.value = selectedText.replace(/\*/g, '');
	}
	else if (selectedText.length == 0) {
		text.value = text.value.substring(0, startIndex) + selectedText + text.value.substring(endIndex);
	}
	else {
		text.value = text.value.substring(0, startIndex) + format + selectedText + format + text.value.substring(endIndex);
	}
}

makeQuote = function (form) {
	var text = document.getElementById(form);
	var startIndex = text.selectionStart,
	endIndex = text.selectionEnd;
	var selectedText = text.value.substring(startIndex, endIndex);

	var format = '>'

	if (selectedText.includes('>')) {
		text.value = text.value.substring(0, startIndex) + selectedText.replace(/\>/g, '') + text.value.substring(endIndex);
	}
	else if (selectedText.length == 0) {
		text.value = text.value.substring(0, startIndex) + selectedText + text.value.substring(endIndex);
	}
	else {
		text.value = text.value.substring(0, startIndex) + format + selectedText + text.value.substring(endIndex);
	}
}

function autoExpand (field) {

	xpos=window.scrollX;
	ypos=window.scrollY;

	field.style.height = 'inherit';

	var computed = window.getComputedStyle(field);

	var height = parseInt(computed.getPropertyValue('border-top-width'), 10)
	+ parseInt(computed.getPropertyValue('padding-top'), 10)
	+ field.scrollHeight
	+ parseInt(computed.getPropertyValue('padding-bottom'), 10)
	+ parseInt(computed.getPropertyValue('border-bottom-width'), 10)
	+ 32;

	field.style.height = height + 'px';

	window.scrollTo(xpos,ypos);

};


document.addEventListener('input', function (event) {
	if (event.target.tagName.toLowerCase() !== 'textarea') return;
	autoExpand(event.target);
}, false);

function post_toast2(url, button1, button2) {
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	var form = new FormData()
	form.append("formkey", formkey());

	if(typeof data === 'object' && data !== null) {
		for(let k of Object.keys(data)) {
			form.append(k, data[k]);
		}
	}


	form.append("formkey", formkey());
	xhr.withCredentials=true;

	xhr.onload = function() {
		data=JSON.parse(xhr.response);
		if (xhr.status >= 200 && xhr.status < 300 && !data["error"]) {
			try {
				document.getElementById('toast-post-success-text').innerText = data["message"];
			} catch(e) {
				document.getElementById('toast-post-success-text').innerText = "Action successful!";
			}
			var myToast = new bootstrap.Toast(document.getElementById('toast-post-success'));
			myToast.show();
			return true

		} else if (xhr.status >= 300 && xhr.status < 400) {
			window.location.href = JSON.parse(xhr.response)["redirect"]
		} else {
			try {
				data=JSON.parse(xhr.response);

				var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
				myToast.show();
				document.getElementById('toast-post-error-text').innerText = data["error"];
				return false
			} catch(e) {
				var myToast = new bootstrap.Toast(document.getElementById('toast-post-success'));
				myToast.hide();
				var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
				myToast.show();
				return false
			}
		}
	};

	xhr.send(form);

	document.getElementById(button1).classList.toggle("hidden");
	document.getElementById(button2).classList.toggle("hidden");
}

function postToast(url) {
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	var form = new FormData()
	form.append("formkey", formkey());

	if(typeof data === 'object' && data !== null) {
		for(let k of Object.keys(data)) {
			form.append(k, data[k]);
		}
	}
	form.append("formkey", formkey());
	xhr.withCredentials=true;

	xhr.onload = function() {
		data=JSON.parse(xhr.response);
		if (xhr.status >= 200 && xhr.status < 300 && !data["error"]) {
			try {
				document.getElementById('toast-post-success-text').innerText = data["message"];
			} catch(e) {
				document.getElementById('toast-post-success-text').innerText = "Action successful!";
			}
			var myToast = new bootstrap.Toast(document.getElementById('toast-post-success'));
			myToast.show();
			return true
		} else if (xhr.status >= 300 && xhr.status < 400) {
			window.location.href = JSON.parse(xhr.response)["redirect"]
		} else {
			try {
				data=JSON.parse(xhr.response);

				var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
				myToast.show();
				document.getElementById('toast-post-error-text').innerText = data["error"];
				return false
			} catch(e) {
				var myToast = new bootstrap.Toast(document.getElementById('toast-post-success'));
				myToast.hide();
				var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
				myToast.show();
				return false
			}
		}
	};
	xhr.send(form);
}

function submitFormAjax(e, success, error) {
	const form = e.target;
	const xhr = new XMLHttpRequest();

	e.preventDefault();

	formData = new FormData(form);

	formData.append("formkey", formkey());
	if(typeof data === 'object' && data !== null) {
		for(let k of Object.keys(data)) {
			form.append(k, data[k]);
		}
	}
	xhr.withCredentials = true;

	actionPath = form.getAttribute("action");

	xhr.open("POST", actionPath, true);

	xhr.onload = function() {
		if (xhr.status >= 200 && xhr.status < 300) {
			data = JSON.parse(xhr.response);
			try {
				document.getElementById('toast-post-success-text').innerText = data["message"];
			} catch(e) {
				document.getElementById('toast-post-success-text').innerText = "Action successful!";
			}
			var myToast = new bootstrap.Toast(document.getElementById('toast-post-success'));
			myToast.show();
			// Run success function
			if (success) success()
			return true
		} else if (xhr.status >= 300 && xhr.status < 400) {
			window.location.href = JSON.parse(xhr.response)["redirect"]
		} else {
			try {
				data=JSON.parse(xhr.response);
				var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
				myToast.show();
				document.getElementById('toast-post-error-text').innerText = data["error"];
			} catch(e) {
				var myToast = new bootstrap.Toast(document.getElementById('toast-post-success'));
				myToast.hide();
				var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
				myToast.show();
			}
			// Run error function
			if (error) error()
			return false;
		}
	};

	xhr.send(formData);

	return false
}

function expandDesktopImage(image) {
	document.getElementById("desktop-expanded-image").src = image.replace("200w_d.webp", "giphy.webp");
	document.getElementById("desktop-expanded-image-link").href = image;
	document.getElementById("desktop-expanded-image-wrap-link").href=image;
};

// Send Direct Message
const messageModal = document.getElementById('directMessageModal')

// When message modal opens
messageModal.addEventListener('show.bs.modal', function (event) {
	// Form that will send the message
	const form = messageModal.querySelector('form');
	// Button that submits the form
	const submit = messageModal.querySelector('[type=submit]');
	// Button that triggered the modal
	const button = event.relatedTarget;
	// Extract info from data-bs-* attributes
	const recipient = button.getAttribute('data-bs-recipient');
	// Update the modal's content.
	const modalTitle = messageModal.querySelector('.modal-title');
	// Set our form's action
	form.action = `/@${recipient}/message`
	// Set our modal header text
	modalTitle.textContent = 'New message to ' + recipient

	// Hide our modal if message is sent
	const success = () => {
		submit.textContent = 'Sent!';
		setTimeout(() => {
			const modal = bootstrap.Modal.getOrCreateInstance(messageModal) // Bootstrap modal instance
			modal.hide();
		}, 200);
	};
	// Enable button if message does not send
	const error = () => {
		submit.disabled = false;
		submit.textContent = 'Try again';
	};
	// Submit our form
	form.addEventListener("submit", function(event) {
		submit.disabled = true;
		submit.textContent = 'Sending';
		submitFormAjax(event, success, error);
	})
})

// When message modal closes
messageModal.addEventListener('hidden.bs.modal', function (event) {
	// Button that submits the form
	const submit = messageModal.querySelector('[type=submit]');
	// Message input box
	const modalBodyInput = messageModal.querySelector('.modal-body textarea')
	// Clear the message
	modalBodyInput.value = '';
	// Reset the submit button state and text
	submit.disabled = false;
	submit.textContent = 'Send';
})

// Send coins