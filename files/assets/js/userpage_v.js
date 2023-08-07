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

	postToast(null, `/@${username}/transfer_coins`, "POST",
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

	postToast(null, `/@${username}/transfer_bux`, "POST",
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
	for (elementId in ['message', 'message-mobile', 'message-preview', 'message-preview-mobile']) {
		const element = document.getElementById(elementId);
		if (element !== null) {
			element.classList.add("d-none");
		}
	}
	
	const form = e.target;
	postToast(null, form.getAttribute("action"), "POST", form, null);
	return false;
}
