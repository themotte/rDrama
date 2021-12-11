function bet_vote(cid) {
    for(let el of document.getElementsByClassName('bet')) {
        el.disabled = true;
    }
    var scoretext = document.getElementById('bet-' + cid);
    var score = Number(scoretext.textContent);
    scoretext.textContent = score + 1;
    post('/bet/' + cid);
    document.getElementById("user-coins-amount").innerText = parseInt(document.getElementById("user-coins-amount").innerText) - 200;
    document.getElementById(`span-${cid}`).classList.add('bet_voted')
}