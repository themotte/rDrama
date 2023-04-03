document.getElementById('post-title').value = localStorage.getItem("post_title")
document.getElementById('post-text').value = localStorage.getItem("post_text")
document.getElementById('post-url').value = localStorage.getItem("post_url")

function checkForRequired() {
	const title = document.getElementById("post-title");
	const url = document.getElementById("post-url");
	const text = document.getElementById("post-text");
	const button = document.getElementById("create_button");
	const image = document.getElementById("file-upload");
	const image2 = document.getElementById("file-upload-submit");

	if (url.value.length > 0 || image.files.length > 0 || image2.files.length > 0) {
		text.required = false;
		url.required=false;
	} else if (text.value.length > 0 || image.files.length > 0 || image2.files.length > 0) {
		url.required = false;
	} else {
		text.required = true;
		url.required = true;
	}

	const isValidTitle = title.checkValidity();
	const isValidURL = url.checkValidity();
	const isValidText = text.checkValidity();

	if (isValidTitle && (isValidURL || image.files.length > 0 || image2.files.length > 0)) {
		button.disabled = false;
	} else if (isValidTitle && isValidText) {
		button.disabled = false;
	} else {
		button.disabled = true;
	}
}
checkForRequired();

function hide_image() {
	x=document.getElementById('image-upload-block');
	url=document.getElementById('post-url').value;
	if (url.length>=1){
		x.classList.add('d-none');
	}
	else {
		x.classList.remove('d-none');
	}
}

document.onpaste = function(event) {
	files = event.clipboardData.files

	filename = files[0]

	if (filename)
	{
		filename = filename.name.toLowerCase()
		if (filename.endsWith(".jpg") || filename.endsWith(".jpeg") || filename.endsWith(".png") || filename.endsWith(".webp") || filename.endsWith(".gif"))
		{
			if (document.activeElement.id == 'post-text') {
				document.getElementById('file-upload-submit').files = files;
				document.getElementById('filename-show-submit').textContent = filename;
			}
			else {
				f=document.getElementById('file-upload');
				f.files = files;
				document.getElementById('filename-show').textContent = filename;
				document.getElementById('urlblock').classList.add('d-none');
				var fileReader = new FileReader();
				fileReader.readAsDataURL(f.files[0]);
				fileReader.addEventListener("load", function () {document.getElementById('image-preview').setAttribute('src', this.result);});  
				document.getElementById('file-upload').setAttribute('required', 'false');	
			}
			document.getElementById('post-url').value = null;
			localStorage.setItem("post_url", "")
		}
		checkForRequired();
	}
}

document.getElementById('file-upload').addEventListener('change', function(){
	f=document.getElementById('file-upload');
	document.getElementById('urlblock').classList.add('d-none');
	document.getElementById('filename-show').textContent = document.getElementById('file-upload').files[0].name.substr(0, 20);
	filename = f.files[0].name.toLowerCase()
	if (filename.endsWith(".jpg") || filename.endsWith(".jpeg") || filename.endsWith(".png") || filename.endsWith(".webp") || filename.endsWith(".webp"))
	{
		var fileReader = new FileReader();
		fileReader.readAsDataURL(f.files[0]);
		fileReader.addEventListener("load", function () {document.getElementById('image-preview').setAttribute('src', this.result);});  
	}
	checkForRequired();
})

function savetext() {
	localStorage.setItem("post_title", document.getElementById('post-title').value)
	localStorage.setItem("post_text", document.getElementById('post-text').value)
	localStorage.setItem("post_url", document.getElementById('post-url').value)
}


function autoSuggestTitle()	{

	var urlField = document.getElementById("post-url");

	var titleField = document.getElementById("post-title");

	var isValidURL = urlField.checkValidity();

	if (isValidURL && urlField.value.length > 0 && titleField.value === "") {

		var x = new XMLHttpRequest();
		x.withCredentials=true;
		x.onreadystatechange = function() {
			if (x.readyState == 4 && x.status == 200 && !titleField.value) {

				title=JSON.parse(x.responseText)["title"];
				titleField.value=title;
				checkForRequired()
			}
		}
		x.open('get','/submit/title?url=' + urlField.value);
		x.send(null);

	};

};

function draft(t) {
	const followers = document.getElementById("followers")
	if (t.checked == true) {
		followers.checked = false;
		followers.disabled = true;
	} else {
		followers.disabled = false;
   }
}

function checkRepost(t) {
	const system = document.getElementById('system')
	system.innerHTML = `To post an image, use a direct image link such as i.imgur.com`;
	const url = t.value

	if (url) {
		const xhr = new XMLHttpRequest();
		xhr.open("post", "/is_repost");
		xhr.setRequestHeader('xhr', 'xhr');
		var form = new FormData()
		form.append("url", url);

		xhr.onload=function(){
			try {data = JSON.parse(xhr.response)}
			catch(e) {console.log(e)}
			
			if (data && data["permalink"]) {
				const permalink = data["permalink"]
				if (permalink) {
					system.innerHTML = `<span class='text-danger'>This is a repost of <a href=${permalink}>${permalink}</a></span>`;
				}
			}
		}
		xhr.send(form)
	}
}
