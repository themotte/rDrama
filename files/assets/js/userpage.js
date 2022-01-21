let uid = document.getElementById('uid')

if (uid)
{
	uid = uid.innerHTML

	let audio = new Audio(`/songs/${uid}`);
	audio.loop=true;

	function toggle() {
		if (audio.paused) audio.play()
		else audio.pause()
	}

	audio.play();
	document.getElementById('userpage').addEventListener('click', () => {
		if (audio.paused) audio.play(); 
	}, {once : true});
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
			}
			else
			{
				audio.pause()
				localStorage.setItem("paused", "1")
			}
		}
	
		if (!paused)
		{
			audio.play();
			document.getElementById('userpage').addEventListener('click', () => {
				if (audio.paused) audio.play(); 
			}, {once : true});
		}
	}
}