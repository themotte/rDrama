function report_postModal(id) {
	const submitbutton = document.getElementById("reportPostButton");
	const wholeFormBefore = document.getElementById('reportPostFormBefore');
	const wholeFormAfter = document.getElementById('reportPostFormAfter');
	const reasonField = document.getElementById("reason-field");

	//The HTML is reused if the user makes multiple reports without a reload, so clean up
	//from any previous openings
	wholeFormBefore.classList.remove('d-none');
	wholeFormAfter.classList.add('d-none');
	submitbutton.disabled = true;
	submitbutton.innerHTML = 'Report post';
	submitbutton.classList.add('disabled');
	reasonField.value = "";
	reasonField.disabled = true;
	for (const radioButton of document.querySelectorAll('input[name="report-reason"]')) {
		radioButton.checked = false;
	}

	const otherButton = document.querySelector('input#other');
	function handleRadioButtonChange() {
		submitbutton.disabled = false;
		submitbutton.classList.remove('disabled');
		reasonField.disabled = !otherButton.checked;
		if (!otherButton.checked) {
			reasonField.value = "";
		}
	};
	wholeFormBefore.addEventListener('change', handleRadioButtonChange);

	submitbutton.onclick = function() {

		this.innerHTML = 'Reporting post';
		this.disabled = true;
		this.classList.add('disabled');

		const xhr = new XMLHttpRequest();
		xhr.open("POST", '/report/post/'+id);
		xhr.setRequestHeader('xhr', 'xhr');
		var form = new FormData();
		form.append("formkey", formkey());
		let reasonValue;
		if (otherButton.checked) {
			reasonValue = reasonField.value;
		} else {
			reasonValue = document.querySelector('input[name="report-reason"]:checked').value;
		}
		form.append("reason", reasonValue);

		xhr.onload=function() {
			wholeFormBefore.classList.add('d-none');
			wholeFormAfter.classList.remove('d-none');
			wholeFormBefore.removeEventListener('change', handleRadioButtonChange);
		};

		xhr.onerror=function(){alert(errortext)};
		xhr.send(form);

	}
};
