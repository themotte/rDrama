function collapse_comment(comment_id) {
    const comment = "comment-" + comment_id
    const element = document.getElementById(comment)
    const closed = element.classList.toggle("collapsed")
    const top = element.getBoundingClientRect().y

    if (closed && top < 0) {
        element.scrollIntoView()
        window.scrollBy(0, - 100)
    }
};

function poll_vote_no_v() {
    var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
    myToast.show();
    document.getElementById('toast-post-error-text').innerText = "Only logged-in users can vote!";
}