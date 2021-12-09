function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function collapse_comment(comment_id) {
    const comment = document.getElementById(`comment-${comment_id}`)
    const text = document.getElementById(`comment-text-${comment_id}`)
    const actions = document.getElementById(`comment-${comment_id}-actions`)
    const repliesOf = document.getElementById(`replies-of-${comment_id}`)


    const isClosed = comment.classList.contains("collapsed");

    const top = comment.getBoundingClientRect().y;

    const arr = [text, actions, repliesOf];

    arr.map(x => x.classList.toggle('hidden')); // hide comment elements
    ['items-center', 'opacity-50'].map(y=> comment.classList.toggle(y)); // apply flex alignment and opacity to comment parent wrapping div

    if (isClosed && top < 0) {
        comment.scrollIntoView()
        window.scrollBy(0, - 100)
    }
};