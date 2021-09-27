function post_vote(url, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", url, true);
    var form = new FormData()
    form.append("formkey", formkey());
    xhr.withCredentials=true;
    xhr.send(form);
}

var upvote = function(event) {

    var type = event.target.dataset.bsContentType;
    var id = event.target.dataset.bsIdUp;

    var downvoteButton = document.getElementsByClassName(type + '-' + id + '-down');
    var upvoteButton = document.getElementsByClassName(type + '-' + id + '-up');
    var scoreText = document.getElementsByClassName(type + '-score-' + id);

    for (var j = 0; j < upvoteButton.length && j < downvoteButton.length && j < scoreText.length; j++) {

        var thisUpvoteButton = upvoteButton[j];
        var thisDownvoteButton = downvoteButton[j];
        var thisScoreText = scoreText[j];
        var thisScore = Number(thisScoreText.textContent);

        if (thisUpvoteButton.classList.contains('active')) {
            thisUpvoteButton.classList.remove('active')
            thisScoreText.textContent = thisScore - 1
            voteDirection = "0"
        } else if (thisDownvoteButton.classList.contains('active')) {
            thisUpvoteButton.classList.add('active')
            thisDownvoteButton.classList.remove('active')
            thisScoreText.textContent = thisScore + 2
            voteDirection = "1"
        } else {
            thisUpvoteButton.classList.add('active')
            thisScoreText.textContent = thisScore + 1
            voteDirection = "1"
        }

        if (thisUpvoteButton.classList.contains('active')) {
            thisScoreText.classList.add('score-up')
            thisScoreText.classList.remove('score-down')
            thisScoreText.classList.remove('score')
        } else if (thisDownvoteButton.classList.contains('active')) {
            thisScoreText.classList.add('score-down')
            thisScoreText.classList.remove('score-up')
            thisScoreText.classList.remove('score')
        } else {
            thisScoreText.classList.add('score')
            thisScoreText.classList.remove('score-up')
            thisScoreText.classList.remove('score-down')
        }
    }

    post_vote("/vote/" + type + "/" + id + "/" + voteDirection);
}

var downvote = function(event) {

    var type = event.target.dataset.bsContentType;
    var id = event.target.dataset.bsIdDown;

    var downvoteButton = document.getElementsByClassName(type + '-' + id + '-down');
    var upvoteButton = document.getElementsByClassName(type + '-' + id + '-up');
    var scoreText = document.getElementsByClassName(type + '-score-' + id);

    for (var j = 0; j < upvoteButton.length && j < downvoteButton.length && j < scoreText.length; j++) {

        var thisUpvoteButton = upvoteButton[j];
        var thisDownvoteButton = downvoteButton[j];
        var thisScoreText = scoreText[j];
        var thisScore = Number(thisScoreText.textContent);

        if (thisDownvoteButton.classList.contains('active')) {
            thisDownvoteButton.classList.remove('active')
            thisScoreText.textContent = thisScore + 1
            voteDirection = "0"
        } else if (thisUpvoteButton.classList.contains('active')) {
            thisDownvoteButton.classList.add('active')
            thisUpvoteButton.classList.remove('active')
            thisScoreText.textContent = thisScore - 2
            voteDirection = "-1"
        } else {
            thisDownvoteButton.classList.add('active')
            thisScoreText.textContent = thisScore - 1
            voteDirection = "-1"
        }

        if (thisUpvoteButton.classList.contains('active')) {
            thisScoreText.classList.add('score-up')
            thisScoreText.classList.remove('score-down')
            thisScoreText.classList.remove('score')
        } else if (thisDownvoteButton.classList.contains('active')) {
            thisScoreText.classList.add('score-down')
            thisScoreText.classList.remove('score-up')
            thisScoreText.classList.remove('score')
        } else {
            thisScoreText.classList.add('score')
            thisScoreText.classList.remove('score-up')
            thisScoreText.classList.remove('score-down')
        }
    }

    post_vote("/vote/" + type + "/" + id + "/" + voteDirection);
}


var upvoteButtons = document.getElementsByClassName('upvote-button')

var downvoteButtons = document.getElementsByClassName('downvote-button')

var voteDirection = 0

for (var i = 0; i < upvoteButtons.length; i++) {
    upvoteButtons[i].addEventListener('click', upvote, false);
    upvoteButtons[i].addEventListener('keydown', function(event) {
        if (event.keyCode === 13) {
            upvote(event)
        }
    }, false)
};

for (var i = 0; i < downvoteButtons.length; i++) {
    downvoteButtons[i].addEventListener('click', downvote, false);
    downvoteButtons[i].addEventListener('keydown', function(event) {
        if (event.keyCode === 13) {
            downvote(event)
        }
    }, false)
};

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