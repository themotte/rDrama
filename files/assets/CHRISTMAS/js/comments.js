function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function collapse_comment(comment_id) {
    const comment = document.getElementById(`comment-${comment_id}`)
    const top = comment.getBoundingClientRect().y;

    const toggler = document.getElementById(`comment-collapse-${comment_id}`);

    ['hidden', 'pointer-events-none'].map(x=> toggler.classList.toggle(x));

    ['items-center', 'opacity-50', 'md:hover:opacity-100', 'collapsed'].map(y=> comment.classList.toggle(y)); // apply flex alignment and opacity to comment parent wrapping div

    const isClosed = comment.classList.contains("collapsed");

    const icon = document.getElementsByClassName(`comment-toggle-icon-${comment_id}`);
    for (let i = 0; i < icon.length; i++) {
        //icon[i].innerText = isClosed ? '[+]' : '[-]'; // text fallback if we don't want to use icons
        icon[i].classList.toggle('fa-minus-circle');
        icon[i].classList.toggle('fa-plus-circle');
    }

    if (isClosed && top < 0) {
        comment.scrollIntoView()
        window.scrollBy(0, - 100)
    }
};

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
            btn.style.display = "none"; // hide button
            el.innerHTML += xhr.response.replace(/data-src/g, 'src').replace(/data-cfsrc/g, 'src').replace(/style="display:none;visibility:hidden;"/g, ''); // replace desired element with response html
            initializeBootstrap()
        } else {
            btn.disabled = false; // enable our button if GET fails
        }
    }
    xhr.send(form)
}

function poll_vote_no_v() {
    var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
    myToast.show();
    document.getElementById('toast-post-error-text').innerText = "Only logged-in users can vote!";
}