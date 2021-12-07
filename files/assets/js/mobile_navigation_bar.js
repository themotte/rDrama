let prevScrollpos = window.pageYOffset;

document.getElementsByTagName('body')[0].onscroll = () => {

	console.log('this works')

	let currentScrollPos = window.pageYOffset;
	// var topBar = document.getElementById("fixed-bar-mobile");
	const bottomBar = document.getElementById("mobile-bottom-navigation-bar");
	// var dropdown = document.getElementById("mobileSortDropdown");
	// var navbar = document.getElementById("navbar");

	if (bottomBar != null) {
		if (prevScrollpos > currentScrollPos && (window.innerHeight + currentScrollPos) < (document.body.offsetHeight - 65)) {
			console.log('this translate y 0 works')
			bottomBar.style.transform = "translateY(0px)"
		} 
		else if (currentScrollPos <= 125 && (window.innerHeight + currentScrollPos) < (document.body.offsetHeight - 65)) {
			bottomBar.style.transform = "translateY(0px)";
		}
		else if (prevScrollpos > currentScrollPos && (window.innerHeight + currentScrollPos) >= (document.body.offsetHeight - 65)) {
			console.log('this translate y works')
			bottomBar.style.transform = "translateY(60px)"
		}
		else {
			bottomBar.style.transform = "translateY(60px)"
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