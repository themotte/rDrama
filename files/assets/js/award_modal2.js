function vote(type, upvote, downvote, scoretext) {

    upvote = document.getElementsById(upvote);
    downvote = document.getElementsById(downvote);
    scoretext = document.getElementsById(scoretext);
    var score = Number(scoretext.textContent);

    if (type == "1") {
        if (upvote.classList.contains('active')) {
            upvote.classList.remove('active')
            scoretext.textContent = score - 1
            votedirection = "0"
        } else if (downvote.classList.contains('active')) {
            upvote.classList.add('active')
            downvote.classList.remove('active')
            scoretext.textContent = score + 2
            votedirection = "1"
        } else {
            upvote.classList.add('active')
            scoretext.textContent = score + 1
            votedirection = "1"
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
        } else if (upvote.classList.contains('active')) {
            downvote.classList.add('active')
            upvote.classList.remove('active')
            scoretext.textContent = score - 2
            votedirection = "-1"
        } else {
            downvote.classList.add('active')
            scoretext.textContent = score - 1
            votedirection = "-1"
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

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/vote/" + type + "/" + id + "/" + votedirection, true);
    var form = new FormData()
    form.append("formkey", formkey());
    xhr.withCredentials=true;
    xhr.send(form);
}


function awardModal(link) {
    var target = document.getElementById("awardTarget");
    target.action = link;
}

function bruh(kind) {
    document.getElementById('giveaward').disabled=false;
    document.getElementById('kind').value=kind;
    try {document.getElementsByClassName('picked')[0].classList.toggle('picked');} catch(e) {}
    document.getElementById(kind).classList.toggle('picked')
}