function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function collapse_comment(comment_id) {
    const comment = document.getElementById(`comment-${comment_id}`)
    const isClosed = comment.classList.contains("collapsed");
    const top = comment.getBoundingClientRect().y;

    ['items-center', 'opacity-50', 'hover:opacity-100', 'collapsed'].map(y=> comment.classList.toggle(y)); // apply flex alignment and opacity to comment parent wrapping div

    if (isClosed && top < 0) {
        comment.scrollIntoView()
        window.scrollBy(0, - 100)
    }
};