function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).title = date.toString();
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

window.addEventListener("load",function(event) {
    var clipboard = new ClipboardJS('.copy-link');
    clipboard.on('success', function(e) {
        var myToast = new bootstrap.Toast(document.getElementById('toast-success'));
        myToast.show();
    });

    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));

    const popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        const popoverId = popoverTriggerEl.getAttribute('data-content-id');
        const contentEl = document.getElementById(popoverId).innerHTML;
        return new bootstrap.Popover(popoverTriggerEl, {
            content: contentEl,
            html: true,
        });
    })
});