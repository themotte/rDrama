function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function pinned_timestamp(id) {
    const el = document.getElementById(id)
    const time =  new Date(parseInt(el.dataset.timestamp)*1000)
    el.setAttribute("data-bs-original-title", `Pinned until ${time}`)
}

function togglePostEdit(id){
	body=document.getElementById("post-body");
	title=document.getElementById("post-title");
	form=document.getElementById("edit-post-body-"+id);
	box=document.getElementById("post-edit-box-"+id);

	body.classList.toggle("hidden");
	title.classList.toggle("hidden");
	form.classList.toggle("hidden");
	autoExpand(box);
};

function bet_vote(cid) {
    for(let el of document.getElementsByClassName('bet')) {
        el.disabled = true;
    }
    for(let el of document.getElementsByClassName('cost')) {
        el.classList.add('hidden')
    }
    var scoretext = document.getElementById('bet-' + cid);
    var score = Number(scoretext.textContent);
    scoretext.textContent = score + 1;
    post('/bet/' + cid);
    document.getElementById("user-coins-amount").innerText = parseInt(document.getElementById("user-coins-amount").innerText) - 200;
}

function checkboxSticky(el, id) {
  if (el.checked) {
    postToast(`/sticky/${id}`)
  } else {
    postToast(`/unsticky/${id}`)
  }
}

function checkboxClub(el, id) {
  if (el.checked) {
    postToast(`/toggle_club/${id}`)
  } else {
    postToast(`/toggle_club/${id}`)
  }
}

function checkboxNSFW(el, id) {
  if (el.checked) {
    postToast(`/toggle_post_nsfw/${id}`)
  } else {
    postToast(`/toggle_post_nsfw/${id}`)
  }
}