function timestamp(id, ti) {
    date = new Date(ti*1000);
    document.getElementById('timestamp-'+id).title = date.toString();
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

var clipboard = new ClipboardJS('.copy-link');
clipboard.on('success', function(e) {
    var myToast = new bootstrap.Toast(document.getElementById('toast-success'));
    myToast.show();
});