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
    let badges = ''
    for (const x of author["badges"]) {
        badges += `<img class="flex-shrink-0 w-8 h-8 object-contain transform transition-100 hover:scale-[1.15]" loading="lazy" src="${x}"/>`
    }
    for (let i = 0; i < document.getElementsByClassName('pop-banner').length; i++) {
        document.getElementsByClassName('pop-banner')[i].src = author["bannerurl"]
        document.getElementsByClassName('pop-picture')[i].src = author["profile_url"]
        document.getElementsByClassName('pop-username')[i].innerHTML = author["username"]
        document.getElementsByClassName('pop-bio')[i].innerHTML = author["bio_html"]
        document.getElementsByClassName('pop-postcount')[i].innerHTML = author["post_count"]
        document.getElementsByClassName('pop-commentcount')[i].innerHTML = author["comment_count"]
        document.getElementsByClassName('pop-coins')[i].innerHTML = author["coins"]
        document.getElementsByClassName('pop-viewmore')[i].href = author["url"]
        document.getElementsByClassName('pop-badges')[i].innerHTML = badges
    }
}