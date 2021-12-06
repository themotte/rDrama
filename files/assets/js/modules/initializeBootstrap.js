export function initializeBootstrap() {
    // tooltips
    let tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(element){
        return new bootstrap.Tooltip(element);
    });
    // popovers
    let popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    let popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        let popoverId = popoverTriggerEl.getAttribute('data-content-id');
        let contentEl = document.getElementById(popoverId).innerHTML;
        return new bootstrap.Popover(popoverTriggerEl, {
            content: contentEl,
            html: true,
        });
    })
}