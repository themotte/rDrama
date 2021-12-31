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
		try {
			let data = JSON.parse(xhr.response)
			if (xhr.status >= 200 && xhr.status < 300 && !data['error']) {
				document.getElementById('toast-post-success-text').innerText = data["message"];
				new bootstrap.Toast(document.getElementById('toast-post-success')).show();

				document.getElementById(button1).classList.toggle("d-none");
				document.getElementById(button2).classList.toggle("d-none");
			
			} else {
				if (data["error"]) document.getElementById('toast-post-error-text').innerText = data["error"];
				new bootstrap.Toast(document.getElementById('toast-post-error')).show();
			}
		}
		catch(e) {new bootstrap.Toast(document.getElementById('toast-post-error')).show();}
	};

	xhr.send(form);

}