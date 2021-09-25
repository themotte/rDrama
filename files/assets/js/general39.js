//POST

function post(url, callback, errortext) {
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	var form = new FormData()
	form.append("formkey", formkey());
	xhr.withCredentials=true;
	xhr.onerror=function() { alert(errortext); };
	xhr.onload = function() {
		if (xhr.status >= 200 && xhr.status < 300) {
			callback();
		} else {
			xhr.onerror();
		}
	};
	xhr.send(form);
};

function post_toast(url, reload, data) {
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
		if (xhr.status >= 200 && xhr.status < 300) {
			$('#toast-post-success').toast('dispose');
			$('#toast-post-success').toast('show');
			try {
				document.getElementById('toast-post-success-text').innerText = JSON.parse(xhr.response)["message"];
			} catch(e) {
				document.getElementById('toast-post-success-text').innerText = "Action successful!";
			}

			if (reload == 1) {window.location.reload(true)}
			return true

		} else if (xhr.status >= 300 && xhr.status < 400) {
			window.location.href = JSON.parse(xhr.response)["redirect"]
		} else {
			try {
				data=JSON.parse(xhr.response);

				$('#toast-post-error').toast('dispose');
				$('#toast-post-error').toast('show');
				document.getElementById('toast-post-error-text').innerText = data["error"];
				return false
			} catch(e) {
				$('#toast-post-success').toast('dispose');
				$('#toast-post-error').toast('dispose');
				$('#toast-post-error').toast('show');
				document.getElementById('toast-post-error-text').innerText = "Error. Try again later.";
				return false
			}
		}
	};

	xhr.send(form);

}


function post_toast2(url, button1, button2) {
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
		if (xhr.status >= 200 && xhr.status < 300) {
			$('#toast-post-success').toast('dispose');
			$('#toast-post-success').toast('show');
			try {
				document.getElementById('toast-post-success-text').innerText = JSON.parse(xhr.response)["message"];
			} catch(e) {
				document.getElementById('toast-post-success-text').innerText = "Action successful!";
			}
			return true

		} else if (xhr.status >= 300 && xhr.status < 400) {
			window.location.href = JSON.parse(xhr.response)["redirect"]
		} else {
			try {
				data=JSON.parse(xhr.response);

				$('#toast-post-error').toast('dispose');
				$('#toast-post-error').toast('show');
				document.getElementById('toast-post-error-text').innerText = data["error"];
				return false
			} catch(e) {
				$('#toast-post-success').toast('dispose');
				$('#toast-post-error').toast('dispose');
				$('#toast-post-error').toast('show');
				document.getElementById('toast-post-error-text').innerText = "Error. Try again later.";
				return false
			}
		}
	};

	xhr.send(form);

	document.getElementById(button1).classList.toggle("d-none");
	document.getElementById(button2).classList.toggle("d-none");
}

// Tooltips

$(document).ready(function(){
	$('[data-toggle="tooltip"]').tooltip(); 
});