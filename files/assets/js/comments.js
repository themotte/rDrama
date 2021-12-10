function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

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

function poll_vote_no_v() {
    var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
    myToast.show();
    document.getElementById('toast-post-error-text').innerText = "Only logged-in users can vote!";
}

function pinned_timestamp(id) {
    const el = document.getElementById(id)
    const time =  new Date(eldataset.timestamp).toString()
    el.setAttribute("data-bs-original-title", `Pinned until ${time}`)
}