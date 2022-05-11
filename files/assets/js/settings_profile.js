function post(url) {
	const xhr = new XMLHttpRequest();
	xhr.open("POST", url);
	xhr.setRequestHeader('xhr', 'xhr');
	var form = new FormData()
	form.append("formkey", formkey());
	xhr.onload = function() {location.reload();};
	xhr.send(form);
};

function updatebgselection(){
	var bgselector = document.getElementById("backgroundSelector");
	const backgrounds = [
		{
			folder: "space",
			backgrounds:
			[
				"1.webp",
			]
		},
	]
		let bgContainer = document.getElementById(`bgcontainer`);
		bgContainer.innerHTML = '';

		let bgsToDisplay = backgrounds[bgselector.selectedIndex].backgrounds;
		let bgsDir = backgrounds[bgselector.selectedIndex].folder;
		for (i=0; i < bgsToDisplay.length; i++) {
			let onclickPost = bgsDir + "/" + bgsToDisplay[i];

			let img = document.createElement('IMG');
			img.className = 'bg-image';
			img.src = `/assets/images/backgrounds/${bgsDir}/${bgsToDisplay[i]}?v=3`;
			img.alt = `${bgsToDisplay[i]}-background`;
			img.addEventListener('click', () => {
				post(`/settings/profile?background=${onclickPost}`);
			});

			let button = document.createElement('BUTTON');
			button.className = "btn btn-secondary bg-button";
			button.appendChild(img);

			bgContainer.appendChild(button);
		}
	}
	updatebgselection();

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
