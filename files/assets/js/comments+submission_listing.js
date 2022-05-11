function timestamp(str, ti) {
	date = new Date(ti*1000);
	document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function pinned_timestamp(id) {
	const el = document.getElementById(id)
	const time =  new Date(parseInt(el.dataset.timestamp)*1000)
	const pintooltip =  el.getAttribute("data-bs-original-title")
	if (!pintooltip.includes('until')) el.setAttribute("data-bs-original-title", `${pintooltip} until ${time}`)
}

function popclick(author) {
	setTimeout(() => {
		let popover = document.getElementsByClassName("popover")
		popover = popover[popover.length-1]

		let badges = ''
		for (const x of author["badges"]) {
			badges += `<img alt="badge" width="32" loading="lazy" src="${x}?v=1016">`
		}
		popover.getElementsByClassName('pop-banner')[0].src = author["bannerurl"]
		popover.getElementsByClassName('pop-picture')[0].src = author["profile_url"]
		popover.getElementsByClassName('pop-username')[0].innerHTML = author["username"]
		popover.getElementsByClassName('pop-bio')[0].innerHTML = author["bio_html"]
		popover.getElementsByClassName('pop-postcount')[0].innerHTML = author["post_count"]
		popover.getElementsByClassName('pop-commentcount')[0].innerHTML = author["comment_count"]
		popover.getElementsByClassName('pop-coins')[0].innerHTML = author["coins"]
		popover.getElementsByClassName('pop-viewmore')[0].href = author["url"]
		popover.getElementsByClassName('pop-badges')[0].innerHTML = badges
	; }, 1);
}

function shownotes(author) {
	let popover = document.getElementById("popover-usernotes")

	console.log(popover);

	return false;
}

document.addEventListener("click", function(){
	active = document.activeElement.getAttributeNode("class");
	if (active && active.nodeValue == "user-name text-decoration-none"){
		pops = document.getElementsByClassName('popover')
		if (pops.length > 1) pops[0].remove()
	}
	else document.querySelectorAll('.popover').forEach(e => e.remove());
});

function post(url) {
	const xhr = new XMLHttpRequest();
	xhr.open("POST", url);
	xhr.setRequestHeader('xhr', 'xhr');
	var form = new FormData()
	form.append("formkey", formkey());
	xhr.send(form);
};

function poll_vote(cid, parentid) {
	for(let el of document.getElementsByClassName('presult-'+parentid)) {
		el.classList.remove('d-none');
	}
	var type = document.getElementById(cid).checked;
	var scoretext = document.getElementById('poll-' + cid);
	var score = Number(scoretext.textContent);
	if (type == true) scoretext.textContent = score + 1;
	else scoretext.textContent = score - 1;
	post('/vote/poll/' + cid + '?vote=' + type);
}

function choice_vote(cid, parentid) {
	for(let el of document.getElementsByClassName('presult-'+parentid)) {
		el.classList.remove('d-none');
	}
	
	let curr = document.getElementById(`current-${parentid}`)
	if (curr && curr.value)
	{
		var scoretext = document.getElementById('choice-' + curr.value);
		var score = Number(scoretext.textContent);
		scoretext.textContent = score - 1;
	}

	var scoretext = document.getElementById('choice-' + cid);
	var score = Number(scoretext.textContent);
	scoretext.textContent = score + 1;
	post('/vote/choice/' + cid);
	curr.value = cid
}

function bet_vote(cid) {
	for(let el of document.getElementsByClassName('bet')) {
		el.disabled = true;
	}
	for(let el of document.getElementsByClassName('cost')) {
		el.classList.add('d-none')
	}
	var scoretext = document.getElementById('bet-' + cid);
	var score = Number(scoretext.textContent);
	scoretext.textContent = score + 1;
	post('/bet/' + cid);
	document.getElementById("user-coins-amount").innerText = parseInt(document.getElementById("user-coins-amount").innerText) - 200;
}
