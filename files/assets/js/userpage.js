const playing = localStorage.getItem("playing")

let uid = document.getElementById('uid')

if (uid)
{
	uid = uid.innerHTML

	let audio = new Audio(`/songs/${uid}`);
	audio.loop=true;

	function toggle() {
		if (audio.paused)
		{
			audio.play()
			localStorage.setItem("playing", "1")
		}
		else
		{
			audio.pause()
			localStorage.setItem("playing", "")
		}
	}

	if (!playing)
	{
		audio.play();
		document.getElementById('userpage').addEventListener('click', () => {
			if (audio.paused) audio.play(); 
		}, {once : true});

		localStorage.setItem("playing", "1")
		window.addEventListener("unload", function(e) {
			localStorage.setItem("playing", "")
		});
	}
}
else
{
	let uid = document.getElementById('vid')
	if (uid)
	{
		uid = uid.innerHTML

		const paused = localStorage.getItem("paused")

		let audio = new Audio(`/songs/${uid}`);
		audio.loop=true;
	
		function toggle() {
			if (audio.paused)
			{
				audio.play()
				localStorage.setItem("paused", "")
				localStorage.setItem("playing", "1")
			}
			else
			{
				audio.pause()
				localStorage.setItem("paused", "1")
				localStorage.setItem("playing", "")
			}
		}
	
		if (!paused && !playing)
		{
			audio.play();
			document.getElementById('userpage').addEventListener('click', () => {
				if (audio.paused) audio.play(); 
			}, {once : true});

			localStorage.setItem("playing", "1")
			window.addEventListener("unload", function(e) {
				localStorage.setItem("playing", "")
			});
		}
	}
}