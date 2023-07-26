function moderate(isPost, id, removing, removeButtonDesktopId, removeButtonMobileId, approveButtonDesktopId, approveButtonMobileId) {
	const filterState = removing ? "removed" : "normal";
	if (isPost) {
		filter_new_status(id, filterState);
	} else {
		filter_new_comment_status(id, filterState);
	}
	const removeButtonDesktop = document.getElementById(removeButtonDesktopId);
	const removeButtonMobile = document.getElementById(removeButtonMobileId);
	const approveButtonDesktop = document.getElementById(approveButtonDesktopId);
	const approveButtonMobile = document.getElementById(approveButtonMobileId);
	if (removing) {
		removeButtonDesktop.classList.add("d-none");
		removeButtonMobile.classList.add("d-none");
		approveButtonDesktop.classList.remove("d-none");
		approveButtonMobile.classList.remove("d-none");
	} else {
		removeButtonDesktop.classList.remove("d-none");
		removeButtonMobile.classList.remove("d-none");
		approveButtonDesktop.classList.add("d-none");
		approveButtonMobile.classList.add("d-none");
	}
}
