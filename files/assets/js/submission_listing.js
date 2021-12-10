function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function expandText(id) {
    document.getElementById('post-text-'+id).classList.toggle('d-none');
    document.getElementsByClassName('text-expand-icon-'+id)[0].classList.toggle('fa-expand-alt');
    document.getElementsByClassName('text-expand-icon-'+id)[0].classList.toggle('fa-compress-alt');
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

function pinned_timestamp(id) {
    const time =  new Date(dataset.timestamp).toString()
    document.getElementById(id).setAttribute("data-bs-original-title", `Pinned until ${time}`)
}