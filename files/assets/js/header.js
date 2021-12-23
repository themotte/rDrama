function formkey() {
	let formkey = document.getElementById("formkey")
	if (formkey) return formkey.innerHTML;
	else return null;
}
	
document.addEventListener("DOMContentLoaded", function(){
	var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
	tooltipTriggerList.map(function(element){
		return new bootstrap.Tooltip(element);
	});
});

function post_toast(url, reload, data) {
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	var form = new FormData()
	form.append("formkey", formkey());

	if(typeof data === 'object' && data !== null) {
		for(let k of Object.keys(data)) {
			form.append(k, data[k]);
		}
	}

	xhr.withCredentials=true;

	xhr.onload = function() {
		data=JSON.parse(xhr.response);
		if (xhr.status >= 200 && xhr.status < 300 && !data["error"]) {
			var myToast = new bootstrap.Toast(document.getElementById('toast-post-success'));
			myToast.show();
			try {
				document.getElementById('toast-post-success-text').innerText = data["message"];
			} catch(e) {
			}

			if (reload == 1) {location.reload(true)}
			return true

		} else if (xhr.status >= 300 && xhr.status < 400) {
			window.location.href = data["redirect"]
		} else {
			try {
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