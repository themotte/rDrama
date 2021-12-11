const audio = new Audio('/assets/christmas/songs/cold.mp3');
audio.loop=true;

function play() {
		audio.play();
}

console.log(audio)

audio.loop=true;

window.addEventListener('load', function() {
	audio.play();
	document.getElementById('thread').addEventListener('click', () => {
		if (audio.paused) audio.play(); 
	}, {once : true});

});