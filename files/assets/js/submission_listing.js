function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function expandText(id) {
	const el = document.getElementById('post-text-'+id);
    ['gradient-mask', 'max-h-32', 'overflow-hidden', 'pointer-events-none', 'text-gray-600'].map(v=> el.classList.toggle(v));
    ['text-black'].map(v=> el.classList.toggle(v));
    document.getElementsByClassName('text-expand-icon-'+id)[0].classList.toggle('fa-expand-alt');
    document.getElementsByClassName('text-expand-icon-'+id)[0].classList.toggle('fa-compress-alt');
};