let uid = document.getElementById('uid')

if (uid)
{
	uid = uid.innerHTML

	let audio = new Audio(`/songs/${uid}`);
	audio.loop=true;

	function pause() {
		audio.pause();
		document.getElementById("pause1").classList.toggle("d-none");
		document.getElementById("play1").classList.toggle("d-none");
		document.getElementById("pause2").classList.toggle("d-none");
		document.getElementById("play2").classList.toggle("d-none");
	}

	function play() {
		audio.play();
		document.getElementById("pause1").classList.toggle("d-none");
		document.getElementById("play1").classList.toggle("d-none");
		document.getElementById("pause2").classList.toggle("d-none");
		document.getElementById("play2").classList.toggle("d-none");
	}
}