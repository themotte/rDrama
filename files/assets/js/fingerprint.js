function fp(fp) {
			var xhr = new XMLHttpRequest();
			xhr.open("POST", '{{request.host_url}}fp/'+fp, true);
			var form = new FormData()
			form.append("formkey", formkey());
			xhr.withCredentials=true;
			xhr.send(form);
		};

		const fpPromise = new Promise((resolve, reject) => {
			const script = document.createElement('script');
			script.onload = resolve;
			script.onerror = reject;
			script.async = true;
			script.src = 'https://cdn.jsdelivr.net/npm/@fingerprintjs/fingerprintjs-pro@3/dist/fp.min.js';
			document.head.appendChild(script);
		})
			.then(() => FingerprintJS.load({token: '{{environ.get("FP")}}'}));

		fpPromise
			.then(fp => fp.get())
			.then(result => {if (result.visitorId != '{{v.fp}}') fp(result.visitorId);})