document.getElementById('password-register').addEventListener('input', function () {

	var charCount = document.getElementById("password-register").value;
	var id = document.getElementById("passwordHelpRegister");
	var successID = document.getElementById("passwordHelpSuccess");

	if (charCount.length >= 8) {
		id.classList.add("d-none");
		successID.classList.remove("d-none");
	} else {
		id.classList.remove("d-none");
		successID.classList.add("d-none");
	}
});

// Asks whether a name is taken only once typing pauses, so typing doesn't send a request per keystroke; at this delay a typist can't send more than two a second, under the route's limit
const USERNAME_CHECK_DELAY_MS = 500;
let usernameCheckTimer;

document.getElementById('username-register').addEventListener('input', function () {

	const field = document.getElementById("username-register");
	const userName = field.value;
	const id = document.getElementById("usernameHelpRegister");
	clearTimeout(usernameCheckTimer);

	if (/[^a-zA-Z0-9_\-]/.test(userName)) {
		id.innerHTML = '<span class="form-text font-weight-bold text-danger mt-1">No special characters or spaces allowed.</span>';
	} else if (userName.length < 3) {
		id.innerHTML = '<span class="form-text font-weight-bold text-muted mt-1">Username must be at least 3 characters long.</span>';
	} else if (userName.length > 25) {
		id.innerHTML = '<span class="form-text font-weight-bold text-danger mt-1">Username must be 25 characters or less.</span>';
	} else {
		// Says nothing about the name until the site answers for it
		id.innerHTML = '';
		usernameCheckTimer = setTimeout(() => {
			fetch('/is_available/' + userName).then(res => res.ok ? res.json() : Promise.reject(new Error(`the site answered ${res.status}`)))
			.then(json => {
				// The answer is about a name the field may no longer hold
				if (field.value !== userName) return;
				if (json[userName] === true) {
					id.innerHTML = '<span class="form-text font-weight-bold text-success mt-1">Username is a-okay!</span>';
				} else if (json[userName] === false) {
					id.innerHTML = '<span class="form-text font-weight-bold text-danger mt-1">Username already taken :(</span>';
				} else {
					throw new Error(`the answer names no verdict for ${userName}`);
				}
			})
			.catch(error => {
				console.error("Couldn't check whether a username is taken:", error);
				if (field.value === userName) {
					id.innerHTML = '<span class="form-text font-weight-bold text-muted mt-1">Couldn\'t check whether that name is taken; signing up will say if it is.</span>';
				}
			});
		}, USERNAME_CHECK_DELAY_MS);
	}
});
