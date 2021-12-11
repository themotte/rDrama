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
    let badges = ''
    for (const x of author["badges"]) {
        badges += `<img width="32" loading="lazy" src="${x}">`
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