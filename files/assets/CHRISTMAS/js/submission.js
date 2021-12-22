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