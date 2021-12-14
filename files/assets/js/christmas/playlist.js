const trackList = [
'low',
'arianalastxmas',
'avriloholy',
'bandaidxmas',
'bingcrosbells',
'bongshit',
'bubleholly',
'charliebrownxmas',
'crosbydrummer',
'crosbyrudolf',
'deckthehalls',
'deckthetrap',
'dinahsilent',
'earthasantabb',
'elsababy',
'elvisbethlehem',
'elviswhite',
'firstnoelrem',
'hark',
'hark2',
'hark3',
'herecumssanta',
'herecumstrap',
'lindplum',
'lowxmas',
'marysboykid',
'nkcchestnuts',
'perryholy',
'rockintrap',
'rudolphtrap',
'santacumtownn',
'sinatramerry',
'sugarplum',
'sugartrap',
'taytayxmas',
'waitresseswrapping',
'womblexmas',
'bells',
'bows',
'buble',
'carol',
'cold',
'deck',
'elton',
'frosty',
'grinch',
'hark',
'holiday',
'kissing',
'mariah',
'navidad',
'nightcore',
'nightcore2',
'nightcore3',
'nightmare',
'pentatonix',
'rockin',
'rudolph',
'santa',
'santababy',
'simply',
'simplyhaving',
'sinatra',
'sinatra2',
'steve',
'trans',
'waitresses',
'wham',
'wonderland'
];
const selected = trackList[Math.floor(Math.random() * trackList.length)];

const audio = new Audio(`/assets/christmas/songs/${selected}.mp3`);
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
