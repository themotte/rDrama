function viewmore(pid,sort,offset) {
    btn = document.getElementById("viewbtn");
    btn.disabled = true;
    btn.innerHTML = "Requesting...";
    var form = new FormData();
	form.append("formkey", formkey());
    var xhr = new XMLHttpRequest();
    xhr.open("post", `/viewmore/${pid}/${sort}/${offset}`);
    xhr.withCredentials=true;
    xhr.onload=function(){
        if (xhr.status==200) {
            document.getElementById(`viewmore-${offset}`).innerHTML = xhr.response.replace(/data-src/g, 'src').replace(/data-cfsrc/g, 'src').replace(/style="display:none;visibility:hidden;"/g, '');
            var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function(element){
                return new bootstrap.Tooltip(element);
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
        }
    }
    xhr.send(form)
}