function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).title = date.toString();
};

function expandText(id) {
    document.getElementById('post-text-'+id).classList.toggle('d-none');
    document.getElementsByClassName('text-expand-icon-'+id)[0].classList.toggle('fa-expand-alt');
    document.getElementsByClassName('text-expand-icon-'+id)[0].classList.toggle('fa-compress-alt');
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