function autoExpand(field) {
	xpos = window.scrollX;
	ypos = window.scrollY;

	field.style.height = 'inherit';

	var computed = window.getComputedStyle(field);

	var height = parseInt(computed.getPropertyValue('border-top-width'), 10)
	+ parseInt(computed.getPropertyValue('padding-top'), 10)
	+ field.scrollHeight
	+ parseInt(computed.getPropertyValue('padding-bottom'), 10)
	+ parseInt(computed.getPropertyValue('border-bottom-width'), 10);

	field.style.height = height + 'px';
	if (Math.abs(window.scrollX - xpos) < 1 && Math.abs(window.scrollY - ypos) < 1) return;

	window.scrollTo(xpos,ypos);
};

document.addEventListener('input', function (event) {
	if (event.target.tagName.toLowerCase() !== 'textarea') return;
	autoExpand(event.target);
}, false);

function formkey() {
	let formkey = document.getElementById("formkey")
	if (formkey) return formkey.innerHTML;
	else return null;
}


function bs_trigger(e) {
	const images = e.querySelectorAll('img[alt^="![]("]');

	for (const e of images) {
		e.setAttribute("data-bs-toggle", "modal")
		e.setAttribute("data-bs-target", "#expandImageModal")
		e.onclick = function(e) {
			const image = e.target.src
			document.getElementById("desktop-expanded-image").src = image.replace("200w_d.webp", "giphy.webp");
			document.getElementById("desktop-expanded-image-link").href = image;
			document.getElementById("desktop-expanded-image-wrap-link").href = image;	
		}
	}

	let tooltipTriggerList = [].slice.call(e.querySelectorAll('[data-bs-toggle="tooltip"]'));
	tooltipTriggerList.map(function(element){
		return bootstrap.Tooltip.getOrCreateInstance(element);
	});

	const popoverTriggerList = [].slice.call(e.querySelectorAll('[data-bs-toggle="popover"]'));
	popoverTriggerList.map(function(popoverTriggerEl) {
		const popoverId = popoverTriggerEl.getAttribute('data-content-id');
		let contentEl;
		try {contentEl = e.getElementById(popoverId);}
		catch(t) {contentEl = document.getElementById(popoverId);}
		if (contentEl) {
			return bootstrap.Popover.getOrCreateInstance(popoverTriggerEl, {
				content: contentEl.innerHTML,
				html: true,
			});
		}
	})
}

var bsTriggerOnReady = function() {
	bs_trigger(document);
}

if (document.readyState === "complete" || 
		(document.readyState !== "loading" && !document.documentElement.doScroll)) {
	bsTriggerOnReady();
} else {
	document.addEventListener("DOMContentLoaded", bsTriggerOnReady);
}

function expandDesktopImage(image) {
	document.getElementById("desktop-expanded-image").src = image.replace("200w_d.webp", "giphy.webp");
	document.getElementById("desktop-expanded-image-link").href = image;
	document.getElementById("desktop-expanded-image-wrap-link").href = image;
};

function postToast(targetElement, url, method, data, callbackFn) {
	if (targetElement) { // disable element to avoid repeated requests
		targetElement.disabled = true;
		targetElement.classList.add("disabled");
	}
	const xhr = new XMLHttpRequest(); // set up the request now
	xhr.open(method, url);
	xhr.setRequestHeader("xhr", "xhr");

	var formData = null;
	if (data instanceof HTMLFormElement) {
		formData = data;
	}
	var form = new FormData(formData ?? undefined);
	form.append("formkey", formkey());

	if (typeof data === 'object' && data !== null) {
		for (let k of Object.keys(data)) {
			form.append(k, data[k]);
		}
	}

	xhr.onload = function() {
		let data;
		try {
			data = JSON.parse(xhr.response);
		} catch (e) {
			console.error("Failed to parse response as JSON", e);
		}

		var message = null;

		if (callbackFn !== null) {
			try {
				const result = callbackFn(xhr);
				if (typeof result === 'string' && result !== null) {
					message = result;
				}
			} catch (e) {
				console.error("Failed to run callback function for postToast", e, xhr);
			}
		}

		if (xhr.status >= 200 && xhr.status < 300 && data && data['message']) {
			const toastPostSuccessTextElement = document.getElementById("toast-post-success-text");
			if (message === null) {
				message = data["message"];
			}
			if (message === null) {
				message = "Success!";
			}
			toastPostSuccessTextElement.innerText = message;
			bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-success')).show();
		} else {
			const toastPostErrorTextElement = document.getElementById('toast-post-error-text');
			if (message != null && data) {
				if (data["details"]) {
					message = data["details"];
				} else if (data["error"]) {
					message = data["error"];
				} else {
					message = "Error, please try again later.";
				}
			}
			if (messageOverride) toastPostErrorTextElement.innerText = message;
			bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error')).show();
		}
	}

	setTimeout(() => {
		targetElement.disabled = false;
		targetElement.classList.remove("disabled");
	}, 1500);

	xhr.send(form);
}

function postToastSimple(t, url, method="POST", data=null) {
	postToast(t, url, method, data, null);
}

function postToastReload(t, url, method, data) {
	postToast(t, url, method, data, (xhr) => location.reload());
}

function postToastSwitch(t, url, method, button1, button2, cssClass="d-none") {
	postToast(t, url, method, null, (xhr) => {
		document.getElementById(button1).classList.toggle(cssClass);
		document.getElementById(button2).classList.toggle(cssClass);
	})
}

function escapeHTML(unsafe) {
	return unsafe.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function changename(s1,s2) {
	let files = document.getElementById(s2).files;
	let filename = '';
	for (const e of files) {
		filename += e.name.substr(0, 20) + ', ';
	}
	document.getElementById(s1).innerHTML = escapeHTML(filename.slice(0, -2));
}
