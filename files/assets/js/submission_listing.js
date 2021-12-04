function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).title = date.toString();
};

function expandText(id) {
    document.getElementById('post-text-'+id).classList.toggle('d-none');
    document.getElementsByClassName('text-expand-icon-'+id)[0].classList.toggle('fa-expand-alt');
    document.getElementsByClassName('text-expand-icon-'+id)[0].classList.toggle('fa-compress-alt');
};