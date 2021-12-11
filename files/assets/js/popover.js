function eventasdf(value){
    var content_id = value.getAttributeNode("data-content-id").value;
    value.addEventListener("click", function(){jhkj(content_id)});
}

function checkIfBussy(){
    if (document.getElementById("bussy") != null){
        document.body.removeChild(document.getElementById("bussy"));
    }
}

function dfgh(e){
    active = document.activeElement;
    if (active.getAttributeNode("class") == null || active.getAttributeNode("class").nodeValue != "user-name"){
        checkIfBussy();
    }
}

function jhkj(value){
    checkIfBussy();
    var popover_shit = document.getElementsByClassName("popover")[0];
    var uiop = document.createElement("DIV");

    uiop.innerHTML = popover_shit.outerHTML;
    uiop.id = "bussy";

    document.body.appendChild(uiop);
    document.body.removeChild(popover_shit);
}

var usernames = document.querySelectorAll("a.user-name");
usernames.forEach(eventasdf);

document.addEventListener("click", function(e){dfgh(e)});

function userPopover(author) {
    for (const x of document.getElementsByClassName('pop-banner')) {x.src = author["bannerurl"]}
    for (const x of document.getElementsByClassName('pop-picture')) {x.src = author["profile_url"]}

    for (const x of document.getElementsByClassName('pop-username')) {x.innerHTML = author["username"]}
    for (const x of document.getElementsByClassName('pop-bio')) {x.innerHTML = author["bio_html"]}
    for (const x of document.getElementsByClassName('pop-postcount')) {x.innerHTML = author["post_count"]}
    for (const x of document.getElementsByClassName('pop-commentcount')) {x.innerHTML = author["comment_count"]}
    for (const x of document.getElementsByClassName('pop-coins')) {x.innerHTML = author["coins"]}

    for (const x of document.getElementsByClassName('pop-viewmore')) {x.href = author["url"]}
}