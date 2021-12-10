function timestamp(str, ti) {
    date = new Date(ti*1000);
    document.getElementById(str).setAttribute("data-bs-original-title", date.toString());
};

function pinned_timestamp(id) {
    const el = document.getElementById(id)
    const time =  new Date(el.dataset.timestamp).toString()
    el.setAttribute("data-bs-original-title", `Pinned until ${time}`)
}