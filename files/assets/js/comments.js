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

function morecomments(cid) {
    btn = document.getElementById(`btn-${cid}`);
    btn.disabled = true;
    btn.innerHTML = "Requesting...";
    var form = new FormData();
    form.append("formkey", formkey());
    var xhr = new XMLHttpRequest();
    xhr.open("post", `/morecomments/${cid}`);
    xhr.withCredentials=true;
    xhr.onload=function(){
        if (xhr.status==200) {
            document.getElementById(`morecomments-${cid}`).innerHTML = xhr.response.replace(/data-src/g, 'src').replace(/data-cfsrc/g, 'src').replace(/style="display:none;visibility:hidden;"/g, '');
            var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function(element){
                return new bootstrap.Tooltip(element);
            });
            popovertrigger()
        }
    }
    xhr.send(form)
}