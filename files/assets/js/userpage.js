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