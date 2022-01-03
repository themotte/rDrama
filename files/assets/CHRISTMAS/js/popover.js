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

function userPopover(author) {
    let popfix = document.getElementById("popover-fix")
    if (popfix) document.body.removeChild(popfix);

    try {
        var popover_old = document.getElementsByClassName("popover")[0];
        var popover_new = document.createElement("DIV");
        popover_new.innerHTML = popover_old.outerHTML;
        popover_new.id = "popover-fix";
    } catch (error) {
        console.error(error);
    }
  
    let badges = ''
    for (const x of author["badges"]) {
        badges += `<img alt="badge" width="32" loading="lazy" src="${x}">`
    }

    if (popover_old !== 'undefined') {
        popover_new.getElementsByClassName('pop-banner')[0].src = author["bannerurl"]
        popover_new.getElementsByClassName('pop-picture')[0].src = author["profile_url"]
        popover_new.getElementsByClassName('pop-username')[0].innerHTML = author["username"]
        popover_new.getElementsByClassName('pop-bio')[0].innerHTML = author["bio_html"]
        popover_new.getElementsByClassName('pop-postcount')[0].innerHTML = author["post_count"]
        popover_new.getElementsByClassName('pop-commentcount')[0].innerHTML = author["comment_count"]
        popover_new.getElementsByClassName('pop-coins')[0].innerHTML = author["coins"]
        popover_new.getElementsByClassName('pop-viewmore')[0].href = author["url"]
        popover_new.getElementsByClassName('pop-badges')[0].innerHTML = badges
      
        document.body.appendChild(popover_new);
        document.body.removeChild(popover_old);
    }
}

document.addEventListener("click", function(){
    active = document.activeElement.getAttributeNode("class");
    if (!(active && active.nodeValue == "user-name")){
        let popfix = document.getElementById("popover-fix")
        if (popfix) document.body.removeChild(popfix);
    }
});