
(function(){
	let modal = document.getElementById('awardModal');
	if (modal) {
		modal.addEventListener('show.bs.modal', function (event) {
			let target = document.getElementById("awardTarget");
			target.action = event.relatedTarget.dataset.url;
		});
	}
})();

function pick(kind, canbuy1, canbuy2) {
	let buy1 = document.getElementById('buy1')
	if (canbuy1 && kind != "grass") buy1.disabled=false;
	else buy1.disabled=true;
	let buy2 = document.getElementById('buy2')
	if (canbuy2 && kind != "benefactor") buy2.disabled=false;
	else buy2.disabled=true;
	let ownednum = Number(document.getElementById(`${kind}-owned`).textContent);
	document.getElementById('giveaward').disabled = (ownednum == 0);
	document.getElementById('kind').value=kind;
	try {document.getElementsByClassName('picked')[0].classList.toggle('picked');} catch(e) {console.log(e)}
	document.getElementById(kind).classList.toggle('picked')

	document.getElementById('notelabel').innerHTML = "Note (optional):";
	document.getElementById('note').placeholder = "Note to include in award notification";
}

function buy(mb) {
	postToast(null, `/buy/${kind}${mb ? '?mb=true' : ''}`, 'POST', null, (xhr) => {
		document.getElementById('giveaward').disabled = false;
		let owned = document.getElementById(`${kind}-owned`);
		const ownednum = Number(owned.textContent);
		owned.textContent = ownednum + 1;
	});
}
