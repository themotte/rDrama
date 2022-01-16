function report_postModal(id) {

	submitbutton=document.getElementById("reportPostButton");

	submitbutton.onclick = function() {

		this.innerHTML='Reporting post';
		this.disabled = true;

		const xhr = new XMLHttpRequest();
		xhr.setRequestHeader('Authorization', 'xhr');
		xhr.open("POST", '/report/post/'+id, true);
		var form = new FormData()
		form.append("formkey", formkey());
		form.append("reason", document.getElementById("reason").value);

		xhr.withCredentials=true;

		xhr.onload=function() {
			document.getElementById("reportPostFormBefore").classList.add('d-none');
			document.getElementById("reportPostFormAfter").classList.remove('d-none');
		};

		xhr.onerror=function(){alert(errortext)};
		xhr.send(form);

	}
};