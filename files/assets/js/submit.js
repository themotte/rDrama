function hide_image() {
	x=document.getElementById('image-upload-block');
	url=document.getElementById('post-URL').value;
	if (url.length>=1){
		x.classList.add('d-none');
	}
	else {
		x.classList.remove('d-none');
	}
}

function checkForRequired() {

	var title = document.getElementById("post-title");

	var url = document.getElementById("post-URL");

	var text = document.getElementById("post-text");

	var button = document.getElementById("create_button");

	var image = document.getElementById("file-upload");

	if (url.value.length > 0 || image.value.length > 0) {
		text.required = false;
		url.required=false;
	} else if (text.value.length > 0 || image.value.length > 0) {
		url.required = false;
	} else {
		text.required = true;
		url.required = true;
	}

	var isValidTitle = title.checkValidity();

	var isValidURL = url.checkValidity();

	var isValidText = text.checkValidity();

	if (isValidTitle && (isValidURL || image.value.length>0)) {
		button.disabled = false;
	} else if (isValidTitle && isValidText) {
		button.disabled = false;
	} else {
		button.disabled = true;
	}
}

document.onpaste = function(event) {
	f=document.getElementById('file-upload');
	files = event.clipboardData.files
	filename = files[0].name.toLowerCase()
	if (filename.endsWith(".jpg") || filename.endsWith(".jpeg") || filename.endsWith(".png") || filename.endsWith(".webp") || filename.endsWith(".gif"))
	{
		f.files = files;
		document.getElementById('filename-show').textContent = filename;
		document.getElementById('urlblock').classList.add('d-none');
		var fileReader = new FileReader();
		fileReader.readAsDataURL(f.files[0]);
		fileReader.addEventListener("load", function () {document.getElementById('image-preview').setAttribute('src', this.result);});  
		document.getElementById('file-upload').setAttribute('required', 'false');
		checkForRequired();
	}
}

document.getElementById('file-upload').addEventListener('change', function(){
	f=document.getElementById('file-upload');
	document.getElementById('urlblock').classList.add('d-none');
	document.getElementById('filename-show').textContent = document.getElementById('file-upload').files[0].name;
	filename = f.files[0].name.toLowerCase()
	if (filename.endsWith(".jpg") || filename.endsWith(".jpeg") || filename.endsWith(".png") || filename.endsWith(".webp") || filename.endsWith(".webp"))
	{
		var fileReader = new FileReader();
		fileReader.readAsDataURL(f.files[0]);
		fileReader.addEventListener("load", function () {document.getElementById('image-preview').setAttribute('src', this.result);});  
		checkForRequired();
	}
})

function savetext() {
	let post_title = document.getElementById('post-title').value
	let post_text = document.getElementById('post-text').value
	window.localStorage.setItem("post_title", post_title)
	window.localStorage.setItem("post_text", post_text)
}