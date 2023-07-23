function toggleElement(id, id2) {
	for(let el of document.getElementsByClassName('toggleable')) {
		if(el.id != id) {
			el.classList.add('d-none');
		}
	}

	document.getElementById(id).classList.toggle('d-none');
	document.getElementById(id2).focus()
}

let TRANSFER_TAX = document.getElementById('tax').innerHTML

function updateTax(mobile=false) {
	let suf = mobile ? "-mobile" : "";
	let amount = parseInt(document.getElementById("coin-transfer-amount" + suf).value);
	if(amount > 0) document.getElementById("coins-transfer-taxed" + suf).innerText = amount - Math.ceil(amount*TRANSFER_TAX);
}

function updateBux(mobile=false) {
	let suf = mobile ? "-mobile" : "";
	let amount = parseInt(document.getElementById("bux-transfer-amount" + suf).value);
	if(amount > 0) document.getElementById("bux-transfer-taxed" + suf).innerText = amount;
}

function transferCoins(mobile=false) {
	for(let el of document.getElementsByClassName('toggleable')) {
		el.classList.add('d-none');
	}

	this.disabled = true;

	let amount = parseInt(document.getElementById("coin-transfer-amount").value);
	let transferred = amount - Math.ceil(amount*TRANSFER_TAX);
	let username = document.getElementById('username').innerHTML

	postToastCallback2(null, `/@${username}/transfer_coins`, "POST",
		{
			"amount": document.getElementById(mobile ? "coin-transfer-amount-mobile" : "coin-transfer-amount").value
		},
		(xhr) => {
		if(xhr.status == 200) {
			document.getElementById("user-coins-amount").innerText = parseInt(document.getElementById("user-coins-amount").innerText) - amount;
			document.getElementById("profile-coins-amount-mobile").innerText = parseInt(document.getElementById("profile-coins-amount-mobile").innerText) + transferred;
			document.getElementById("profile-coins-amount").innerText = parseInt(document.getElementById("profile-coins-amount").innerText) + transferred;
		}
		}
	);

	setTimeout(_ => this.disabled = false, 2000);
}

function transferBux(mobile=false) {
	for(let el of document.getElementsByClassName('toggleable')) {
		el.classList.add('d-none');
	}

	this.disabled = true;

	let amount = parseInt(document.getElementById("bux-transfer-amount").value);
	let username = document.getElementById('username').innerHTML

	postToastCallback2(null, `/@${username}/transfer_bux`, "POST",
		{"amount": document.getElementById(mobile ? "bux-transfer-amount-mobile" : "bux-transfer-amount").value},
		(xhr) => {
		if(xhr.status == 200) {
			document.getElementById("user-bux-amount").innerText = parseInt(document.getElementById("user-bux-amount").innerText) - amount;
			document.getElementById("profile-bux-amount-mobile").innerText = parseInt(document.getElementById("profile-bux-amount-mobile").innerText) + amount;
			document.getElementById("profile-bux-amount").innerText = parseInt(document.getElementById("profile-bux-amount").innerText) + amount;
		}
		}
	);

	setTimeout(_ => this.disabled = false, 2000);
}

function submitFormAjax(e) {
	document.getElementById('message').classList.add('d-none');
	document.getElementById('message-mobile').classList.add('d-none');
	document.getElementById('message-preview').classList.add('d-none');
	document.getElementById('message-preview-mobile').classList.add('d-none');
	
	const form = e.target;
	const xhr = new XMLHttpRequest();
	e.preventDefault();

	formData = new FormData(form);

	formData.append("formkey", formkey());
	if(typeof data === 'object' && data !== null) {
		for(let k of Object.keys(data)) {
			form.append(k, data[k]);
		}
	}
	actionPath = form.getAttribute("action");

	xhr.open("POST", actionPath);
	xhr.setRequestHeader('xhr', 'xhr');

	xhr.onload = function() {
		if (xhr.status >= 200 && xhr.status < 300) {
			let data = JSON.parse(xhr.response);
			try {
				document.getElementById('toast-post-success-text').innerText = data["message"];
			} catch(e) {
				document.getElementById('toast-post-success-text').innerText = "Action successful!";
			}
			var myToast = bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-success'));
			myToast.show();
			return true
		} else {
			document.getElementById('toast-post-error-text').innerText = "Error, please try again later."
			try {
				let data=JSON.parse(xhr.response);
				var myToast = bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error'));
				myToast.show();
				if (data && data["error"]) document.getElementById('toast-post-error-text').innerText = data["error"];
				if (data && data["details"]) document.getElementById('toast-post-error-text').innerText = data["details"];
			} catch(e) {
				var myToast = bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-success'));
				myToast.hide();
				var myToast = bootstrap.Toast.getOrCreateInstance(document.getElementById('toast-post-error'));
				myToast.show();
			}
		}
	};

	xhr.send(formData);

	return false
}
