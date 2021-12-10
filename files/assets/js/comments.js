function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function collapse_comment(comment_id) {
    const comment = document.getElementById(`comment-${comment_id}`)
    const isClosed = comment.classList.contains("collapsed");
    const top = comment.getBoundingClientRect().y;

    const toggler = document.getElementById(`comment-collapse-${comment_id}`);

    ['hidden', 'pointer-events-none'].map(x=> toggler.classList.toggle(x));

    ['items-center', 'opacity-50', 'hover:opacity-100', 'collapsed'].map(y=> comment.classList.toggle(y)); // apply flex alignment and opacity to comment parent wrapping div

    toggler.innerText = isClosed ? '[+]' : '[-]';

    if (isClosed && top < 0) {
        comment.scrollIntoView()
        window.scrollBy(0, - 100)
    }
};