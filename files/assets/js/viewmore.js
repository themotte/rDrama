function loadMore(pid,sort,offset,id,trigger) {
    const btn = document.getElementById(trigger) // trigger button
    const el = document.getElementById(id) // target element to populate
    const form = new FormData();
    const xhr = new XMLHttpRequest();

    btn.classList.toggle('animate-pulse');

    xhr.open("post", `/viewmore/${pid}/${sort}/${offset}`);
    xhr.withCredentials=true;
    xhr.onload=function(){
        if (xhr.status==200) {
            el.innerHTML += xhr.response.replace(/data-src/g, 'src').replace(/data-cfsrc/g, 'src').replace(/style="display:none;visibility:hidden;"/g, ''); // replace desired element with response html
            btn.style.display = "none"; // hide button
            initializeBootstrap()
        } else {
            btn.disabled = false; // enable our button if GET fails
        }
    }
    xhr.send(form)
}

function loadMoreReplies(cid,id,trigger) {
    const btn = document.getElementById(trigger) // trigger button
    const el = document.getElementById(id) // target element to populate
    const form = new FormData();
    const xhr = new XMLHttpRequest();

    btn.classList.toggle('animate-pulse');

    xhr.open("post", `/morecomments/${cid}`);
    xhr.withCredentials=true;
    xhr.onload=function(){
        if (xhr.status==200) {
            el.innerHTML += xhr.response.replace(/data-src/g, 'src').replace(/data-cfsrc/g, 'src').replace(/style="display:none;visibility:hidden;"/g, ''); // replace desired element with response html
            btn.style.display = "none"; // hide button
            initializeBootstrap()
        } else {
            btn.disabled = false; // enable our button if GET fails
        }
    }
    xhr.send(form)
}