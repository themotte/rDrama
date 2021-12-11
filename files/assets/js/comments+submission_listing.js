function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function pinned_timestamp(id) {
    const el = document.getElementById(id)
    const time =  new Date(parseInt(el.dataset.timestamp)*1000)
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

function popclick(author) {
    let badges = ''
    for (const x of author["badges"]) {
        badges += `<img width="32" loading="lazy" src="${x}">`
    }
    i = document.getElementsByClassName('pop-banner').length - 1
    document.getElementsByClassName('pop-banner')[i].src = author["bannerurl"]
    document.getElementsByClassName('pop-picture')[i].src = author["profile_url"]
    document.getElementsByClassName('pop-username')[i].innerHTML = author["username"]
    document.getElementsByClassName('pop-bio')[i].innerHTML = author["bio_html"]
    document.getElementsByClassName('pop-postcount')[i].innerHTML = author["post_count"]
    document.getElementsByClassName('pop-commentcount')[i].innerHTML = author["comment_count"]
    document.getElementsByClassName('pop-coins')[i].innerHTML = author["coins"]
    document.getElementsByClassName('pop-viewmore')[i].href = author["url"]
    document.getElementsByClassName('pop-badges')[i].innerHTML = badges

    let popfix = document.getElementById("popover-fix")
    if (popfix) document.body.removeChild(popfix);

    var popover_old = document.getElementsByClassName("popover")[0];
    var popover_new = document.createElement("DIV");
  
    popover_new.innerHTML = popover_old.outerHTML;
    popover_new.id = "popover-fix";
  
    document.body.appendChild(popover_new);
    document.body.removeChild(popover_old);
}

document.addEventListener("click", function(){
    active = document.activeElement.getAttributeNode("class");
    if (!(active && active.nodeValue == "user-name text-decoration-none")){
        let popfix = document.getElementById("popover-fix")
        if (popfix) document.body.removeChild(popfix);
    }
});