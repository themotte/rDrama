function post(url) {
	const xhr = new XMLHttpRequest();
	xhr.open("POST", url);
	xhr.setRequestHeader('xhr', 'xhr');
	var form = new FormData()
	form.append("formkey", formkey());
	xhr.onload = function() {location.reload();};
	xhr.send(form);
};

document.onpaste = function(event) {
	var focused = document.activeElement;
	if (focused.id == 'bio-text') {
		f=document.getElementById('file-upload');
		files = event.clipboardData.files
		filename = files[0].name.toLowerCase()
		if (filename.endsWith(".jpg") || filename.endsWith(".jpeg") || filename.endsWith(".png") || filename.endsWith(".webp") || filename.endsWith(".gif"))
		{
			f.files = files;
			document.getElementById('filename-show').textContent = filename;
		}
	}
}