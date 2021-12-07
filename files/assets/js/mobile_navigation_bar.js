let prevScrollpos = window.pageYOffset;

document.getElementsByTagName('body')[0].onscroll = () => {
	let currentScrollPos = window.pageYOffset;
	// var topBar = document.getElementById("fixed-bar-mobile");
	const bottomBar = document.getElementById("mobile-bottom-navigation-bar");
	// var dropdown = document.getElementById("mobileSortDropdown");
	// var navbar = document.getElementById("navbar");

	if (bottomBar != null) {
		if (currentScrollPos <= 60 || (window.innerHeight + currentScrollPos >= document.body.offsetHeight - 60)) {
			bottomBar.style.transform = "translateY(60px)";
		}
		else if (prevScrollpos > currentScrollPos && (window.innerHeight + currentScrollPos < document.body.offsetHeight - 60)) {
			bottomBar.style.transform = "translateY(0px)"
		}
		else {
			bottomBar.style.transform = "translateY(60px)";
		}
	}

	// if (topBar != null && dropdown != null) {
	// 	if (prevScrollpos > currentScrollPos) {
	// 		topBar.style.top = "48px";
	// 		navbar.classList.remove("shadow");
	// 	} 
	// 	else if (currentScrollPos <= 125) {
	// 		topBar.style.top = "48px";
	// 		navbar.classList.remove("shadow");
	// 	}
	// 	else {
	// 		topBar.style.top = "-48px";
	// 		dropdown.classList.remove('show');
	// 		navbar.classList.add("shadow");
	// 	}
	// }
	prevScrollpos = currentScrollPos;
}