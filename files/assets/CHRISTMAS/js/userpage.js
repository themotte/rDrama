function post_toast_callback(url, data, callback) {
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	var form = new FormData()

	if(typeof data === 'object' && data !== null) {
		for(let k of Object.keys(data)) {
			form.append(k, data[k]);
		}
	}

	form.append("formkey", formkey());
	xhr.withCredentials=true;

	xhr.onload = function() {
		let result = callback(xhr);
		if (xhr.status >= 200 && xhr.status < 300) {
			var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
			myToast.hide();

			var myToast = new bootstrap.Toast(document.getElementById('toast-post-success'));
			myToast.show();

			try {
				if(typeof result == "string") {
					document.getElementById('toast-post-success-text').innerText = result;
				} else {
					document.getElementById('toast-post-success-text').innerText = JSON.parse(xhr.response)["message"];
				}
			} catch(e) {
				document.getElementById('toast-post-success-text').innerText = "Action successful!";
			}

			return true;
		} else {
			var myToast = new bootstrap.Toast(document.getElementById('toast-post-success'));
			myToast.hide();

			var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
			myToast.show();

			try {
				if(typeof result == "string") {
					document.getElementById('toast-post-error-text').innerText = result;
				} else {
					document.getElementById('toast-post-error-text').innerText = JSON.parse(xhr.response)["error"];
				}
				return false
			} catch(e) {}

			return false;
		}
	};

	xhr.send(form);

}

function submitFormAjax(e) {
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
			let data = JSON.parse(xhr.response);
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
				let data=JSON.parse(xhr.response);
				var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
				myToast.show();
				document.getElementById('toast-post-error-text').innerText = data["error"];
			} catch(e) {
				var myToast = new bootstrap.Toast(document.getElementById('toast-post-success'));
				myToast.hide();
				var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
				myToast.show();
			}
		}
	};

	xhr.send(formData);

	return false
}

function toggleElement(group, id) {
	for(let el of document.getElementsByClassName(group)) {
		if(el.id != id) {
			el.classList.add('hidden');
		}
	}

	document.getElementById(id).classList.toggle('hidden');
}

// Admin Actions

function clubAccess(el, username) {
  if (el.checked) {
    postToast(`@${username}/club_allow`)
  } else {
    postToast(`@${username}/club_ban`)
  }
}

function verifyBadge(el, id) {
  if (el.checked) {
    postToast(`admin/verify/${id}`)
  } else {
    postToast(`admin/unverify/${id}`)
  }
}

