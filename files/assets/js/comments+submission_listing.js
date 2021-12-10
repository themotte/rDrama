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

function popoverEventListener(value){
    //get the id of the popover that will be created for this user
    var content_id = value.getAttributeNode("data-content-id").value;
    //add an event listener that will trigger the creation of a replacement popover when the username is clicked
    value.addEventListener("click", function(){createNewPopover(content_id)});
  }
  
  function checkIfPopover(){
    //check if a replacement popover already exists and remove it if so
    if (document.getElementById("popover-fix") != null){
      document.body.removeChild(document.getElementById("popover-fix"));
    }
  }
  
  function closePopover(e){
    //get the element that was clicked on
    active = document.activeElement;
    //if the element is not a username then check if a popover replacement already exists
    if (active.attributes.getNamedItem("data-bs-toggle").nodeValue != "popover"){
      checkIfPopover();
    }
  }
  
  function createNewPopover(value){
    //check for an existing replacement popover and then copy the original popover node
    checkIfPopover();
    var popover_old = document.getElementsByClassName("popover")[0];
    var popover_new = document.createElement("DIV");
  
    //copy the contents of the original popover
    popover_new.innerHTML = popover_old.outerHTML;
    popover_new.id = "popover-fix";
  
    //append the replacement popover to the document and remove the original one
    document.body.appendChild(popover_new);
    document.body.removeChild(popover_old);
  }
  
  window.addEventListener('load', (e) => {
    //grab all of the usernames on the page and create event listeners for them 
    var usernames = document.querySelectorAll("a[data-bs-toggle=popover]");
    usernames.forEach(popoverEventListener);
  
    //create an event listener to check if a clicked element is a username
    document.addEventListener("click", function(e){closePopover(e)});
  });
  

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