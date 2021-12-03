function awardModal(link) {
	var target = document.getElementById("awardTarget");
	target.action = link;
}

function bruh(kind) {
	document.getElementById('giveaward').disabled=false;
	document.getElementById('kind').value=kind;
	try {document.getElementsByClassName('picked')[0].classList.toggle('picked');} catch(e) {}
	document.getElementById(kind).classList.toggle('picked')
	if (kind == "flairlock") {
		document.getElementById('notelabel').innerHTML = "New flair:";
		document.getElementById('note').placeholder = "Insert new flair here...";
	}
	else {
		document.getElementById('notelabel').innerHTML = "Note (optional):";
		document.getElementById('note').placeholder = "Note to include in award notification";
	}
}