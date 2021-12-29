function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function pinned_timestamp(id) {
    const el = document.getElementById(id)
    const time =  new Date(parseInt(el.dataset.timestamp)*1000)
    el.setAttribute("data-bs-original-title", `Pinned until ${time}`)
}

function expandText(id) {
	const el = document.getElementById('post-text-'+id);
    ['gradient-mask', 'max-h-10', 'overflow-hidden', 'pointer-events-none', 'text-gray-500', 'dark:text-gray-400'].map(v=> el.classList.toggle(v));
    ['text-black', 'dark:text-gray-100'].map(v=> el.classList.toggle(v));

    const trigger = document.getElementsByClassName('text-expand-icon-'+id);
    for (let i = 0; i < trigger.length; i++) {
    	trigger[i].classList.toggle('fa-expand-alt');
    	trigger[i].classList.toggle('fa-compress-alt');
    }
};

function togglevideo(pid) {
    // Video elements
    const vid = document.getElementById(`video-${pid}`)
    const vid2 = document.getElementById(`video2-${pid}`)
    // Toggle hidden class
    vid.classList.toggle('hidden')
    // Controls
    if (vid.classList.contains('hidden')) {
        vid2.pause()
    } else {
        vid2.play()
    }
}