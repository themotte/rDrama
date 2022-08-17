document.getElementById('new_email').addEventListener('input', function () {
	document.getElementById("email-password").classList.remove("d-none");
	document.getElementById("email-password-label").classList.remove("d-none");
	document.getElementById("emailpasswordRequired").classList.remove("d-none");
});

document.getElementById('2faToggle').addEventListener('change', function () {
	const twoStepModal = new bootstrap.Modal(document.getElementById('2faModal'));
	twoStepModal.show();
});

function emailVerifyText() {
	document.getElementById("email-verify-text").innerHTML = "Verification email sent! Please check your inbox.";
}
