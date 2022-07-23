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

function fillnote(user,post,comment) {

	let dialog = document.getElementById("modal-1");
	let table  = "";

	for(let i = 0; i < user.notes.length; ++i){
		let note_id = "note_" + i;
		let note = user.notes[i];
		let date = new Date(parseInt(note.created) * 1000);
		let date_str = date.toLocaleDateString();
		let time_str = date.toLocaleTimeString();

		let tag = "None";
		switch(note.tag){
			case 0: tag = "Quality"; break;
			case 1: tag = "Good"   ; break;
			case 2: tag = "Comment"; break;
			case 3: tag = "Warning"; break;
			case 4: tag = "Tempban"; break;
			case 5: tag = "Permban"; break;
			case 6: tag = "Spam"   ; break;
			case 7: tag = "Bot"    ; break;
		}

		table += "" +
		"<div class=\"table_note\" id=\"" + note_id + "\" data-id=\"" + note.id + "\">" +
			"<div class=\"table_note_author\">" + 
				note.author_name + "<br/>" + 
				"<a class=\"table_note_date\" href=\"" + note.reference + "\">" + date_str + ", " + time_str + "</a>" +
			"</div>" +
			"<div class=\"table_note_message\">" + note.note + "</div>" +
			"<div class=\"table_note_tag\">" + tag + "</div>" +
			"<div class=\"table_note_delete\"><span onclick=\"delete_note('" + note_id + "','" + user.url + "')\">Delete</span></div>" +
		"</div>\n"
	}

	dialog.getElementsByClassName('notes_target')[0].innerText = user.username;
	dialog.getElementsByClassName('table_content')[0].innerHTML = table;

	dialog.dataset.context = JSON.stringify({
		'url':  user.url,
		'post': post,
		'comment': comment,
		'user': user.id,
	});
}

function delete_note(element,url) {
	let note = document.getElementById(element);
	let id   = note.dataset.id;

	const xhr = new XMLHttpRequest();
	xhr.open("POST", url + "/delete_note/" + id);
	xhr.setRequestHeader('xhr', 'xhr');
	xhr.responseType = 'json';
	
	xhr.onload = function() {
		if(xhr.status === 200) {
			console.log(xhr.response);
			location.reload();
		}
	}

	var form = new FormData()
	form.append("formkey", formkey());
	xhr.send(form);
}

function send_note() {
	let dialog = document.getElementById("modal-1");
	let context = JSON.parse(dialog.dataset.context);

	let note = document.querySelector("#modal-1 textarea").value;
	let tag = document.querySelector("#modal-1 #usernote_tag").value;

	const xhr = new XMLHttpRequest();
	xhr.open("POST", context.url + "/create_note");
	xhr.setRequestHeader('xhr', 'xhr');
	xhr.responseType = 'json';
	var form = new FormData()

	form.append("formkey", formkey());
	form.append("data", JSON.stringify({
		'note': note,
		'post': context.post,
		'comment': context.comment,
		'user': context.user,
		'tag':  tag
	}));
	
	xhr.onload = function() {
		if(xhr.status === 200) {
			console.log(xhr.response);
			location.reload();
		}
	}

	xhr.send(form);
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

function vote(type, id, dir, vid) {
	const upvotes = document.getElementsByClassName(type + '-' + id + '-up');
	const downvotes = document.getElementsByClassName(type + '-' + id + '-down');
	const scoretexts = document.getElementsByClassName(type + '-score-' + id);

	for (let i=0; i<upvotes.length; i++) {
		
		const upvote = upvotes[i]
		const downvote = downvotes[i]
		const scoretext = scoretexts[i]
		const score = Number(scoretext.textContent);

		if (dir == "1") {
			if (upvote.classList.contains('active')) {
				upvote.classList.remove('active')
				scoretext.textContent = score - 1
				votedirection = "0"
				if (vid && ['1','9'].includes(vid)) document.getElementById(id+'-title').classList.remove('visited')
			} else if (downvote.classList.contains('active')) {
				upvote.classList.add('active')
				downvote.classList.remove('active')
				scoretext.textContent = score + 2
				votedirection = "1"
			} else {
				upvote.classList.add('active')
				scoretext.textContent = score + 1
				votedirection = "1"
				if (vid && ['1','9'].includes(vid)) document.getElementById(id+'-title').classList.add('visited')
			}

			if (upvote.classList.contains('active')) {
				scoretext.classList.add('score-up')
				scoretext.classList.remove('score-down')
				scoretext.classList.remove('score')
			} else if (downvote.classList.contains('active')) {
				scoretext.classList.add('score-down')
				scoretext.classList.remove('score-up')
				scoretext.classList.remove('score')
			} else {
				scoretext.classList.add('score')
				scoretext.classList.remove('score-up')
				scoretext.classList.remove('score-down')
			}
		}
		else {
			if (downvote.classList.contains('active')) {
				downvote.classList.remove('active')
				scoretext.textContent = score + 1
				votedirection = "0"
				if (vid && ['1','9'].includes(vid)) document.getElementById(id+'-title').classList.remove('visited')
			} else if (upvote.classList.contains('active')) {
				downvote.classList.add('active')
				upvote.classList.remove('active')
				scoretext.textContent = score - 2
				votedirection = "-1"
			} else {
				downvote.classList.add('active')
				scoretext.textContent = score - 1
				votedirection = "-1"
				if (vid && ['1','9'].includes(vid)) document.getElementById(id+'-title').classList.add('visited')
			}

			if (upvote.classList.contains('active')) {
				scoretext.classList.add('score-up')
				scoretext.classList.remove('score-down')
				scoretext.classList.remove('score')
			} else if (downvote.classList.contains('active')) {
				scoretext.classList.add('score-down')
				scoretext.classList.remove('score-up')
				scoretext.classList.remove('score')
			} else {
				scoretext.classList.add('score')
				scoretext.classList.remove('score-up')
				scoretext.classList.remove('score-down')
			}
		}
	}
	
	const xhr = new XMLHttpRequest();
	xhr.open("POST", "/vote/" + type.replace('-mobile','') + "/" + id + "/" + votedirection);
	xhr.setRequestHeader('xhr', 'xhr');
	var form = new FormData()
	form.append("formkey", formkey());
	xhr.send(form);
}
