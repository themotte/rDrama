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