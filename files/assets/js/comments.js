function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function collapse_comment(comment_id) {
    const comment = "comment-" + comment_id
    const element = document.getElementById(comment)
    const closed = element.classList.toggle("collapsed")
    const top = element.getBoundingClientRect().y

    const text = document.getElementById('comment-text-'+comment_id)
    const actions = document.getElementById('comment-actions-'+comment_id)
    const repliesOf = document.getElementById('replies-of-'+comment_id)

    const arr = [text, actions, repliesOf];

    arr.map(x => x.classList.toggle('hidden'));

    if (closed && top < 0) {
        element.scrollIntoView()
        window.scrollBy(0, - 100)
    }
};