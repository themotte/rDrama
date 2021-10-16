function post(url) {
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	var form = new FormData()
	form.append("formkey", formkey());
	xhr.withCredentials=true;
	xhr.onload = function() {location.reload(true);};
	xhr.send(form);
};

function updatebgselection(){
	var bgselector = document.getElementById("backgroundSelector");
	const backgrounds = [
		{
			folder: "fantasy",
			backgrounds: 
			[
				"1.gif",
				"2.gif",
				"3.gif",
				"4.gif",
				"5.gif",
				"6.gif",
			]
		},
		{
			folder: "solarpunk",
			backgrounds: 
			[
				"1.gif",
				"2.gif",
				"3.gif",
				"4.gif",
				"5.gif",
				"6.gif",
				"7.gif",
				"8.gif",
				"9.gif",
				"10.gif",
				"11.gif",
				"12.gif",
				"13.gif",
				"14.gif",
				"15.gif",
				"16.gif",
				"17.gif",
				"18.gif",
				"19.gif",
			]
		},
		{
		folder: "pixelart",
		backgrounds:
		[
			"1.gif",
			"2.gif",
			"3.gif",
			"4.gif",
			"5.gif",
		]
		}
	]
		let bgContainer = document.getElementById(`bgcontainer`);
		let str = '';
		let bgsToDisplay = backgrounds[bgselector.selectedIndex].backgrounds;
		let bgsDir = backgrounds[bgselector.selectedIndex].folder;
		for (i=0; i < bgsToDisplay.length; i++) {
			let onclickPost = bgsDir + "/" + bgsToDisplay[i];
			str += `<button class="btn btn-secondary m-1 p-0" style="width:15rem; overflow: hidden;"><img loading="lazy" style="padding:0.25rem; width: 15rem" src="/assets/images/backgrounds/${bgsDir}/${bgsToDisplay[i]}" alt="${bgsToDisplay[i]}-background" onclick="post('/settings/profile?background=${onclickPost}')"/></button>`;
		}
		bgContainer.innerHTML = str;
	}
	updatebgselection();