function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function pinned_timestamp(id) {
    const el = document.getElementById(id)
    const time =  new Date(el.dataset.timestamp)
    el.setAttribute("data-bs-original-title", `Pinned until ${time}`)
}

function expandDesktopImage(image) {
	document.getElementById("desktop-expanded-image").src = image.replace("200w_d.webp", "giphy.webp");
	document.getElementById("desktop-expanded-image-link").href = image;
	document.getElementById("desktop-expanded-image-wrap-link").href=image;
};


function popovertrigger() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        const popoverId = popoverTriggerEl.getAttribute('data-content-id');
        const contentEl = document.getElementById(popoverId);
        if (contentEl) {
            return new bootstrap.Popover(popoverTriggerEl, {
                content: contentEl.innerHTML,
                html: true,
            });
        }
    })
}

popovertrigger()

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
	if (active.getAttributeNode("class") == null || active.getAttributeNode("class").nodeValue != "user-name text-decoration-none"){
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

function popclick(author) {
    for (const x of document.getElementsByClassName('pop-banner')) {x.src = author["bannerurl"]}
    for (const x of document.getElementsByClassName('pop-picture')) {x.src = author["profile_url"]}
    for (const x of document.getElementsByClassName('pop-username')) {x.innerHTML = author["username"]}
    for (const x of document.getElementsByClassName('pop-bio')) {x.innerHTML = author["bio_html"]}
    for (const x of document.getElementsByClassName('pop-postcount')) {x.innerHTML = author["post_count"]}
    for (const x of document.getElementsByClassName('pop-commentcount')) {x.innerHTML = author["comment_count"]}
    for (const x of document.getElementsByClassName('pop-coins')) {x.innerHTML = author["coins"]}
    for (const x of document.getElementsByClassName('pop-viewmore')) {x.href = author["url"]}
}