(function() {
	const event = InputEvent
		? function(type, attrs) {
			return new InputEvent(type, attrs);
		}
		: function(type) {
			e = document.createEvent('event');
			e.initEvent(type, false, false);
			return e;
		};

	const escape = (str) => (
		str.replace(/./g, '[$&]').replace(/[\\^]|]]/g, '\\$&')
	);

	const wrap = (callback) => (
		(id) => {
			const form = document.getElementById(id);
			if (callback(form)) {
				const e = event('input', { inputType: 'insertReplacementText' });
				form.dispatchEvent(e);
			}
		}
	);

	const select = (callback) => (
		(form) => {
			const begin = form.selectionStart, end = form.selectionEnd;
			if (begin == end)
				return false;
			form.value = form.value.substring(0, begin)
				+ callback(form.value.substring(begin, end))
				+ form.value.substring(end);
			return true;
		}
	);

	const enclose = (mark) => {
		const re = (() => {
			const pat = escape(mark);
			return new RegExp(pat + '(\\S([^](?!\\s' + pat + '\\S))*?\\S|\\S)' + pat, 'g');
		})();
		return select((selection) => (
			selection.replace(/[^]*?(?=\n{2,})|[^]*/g, (selection) => {
				let replacement = selection.replace(re, '$1');
				for (var old = Infinity;
				     replacement.length < old;
				     replacement = replacement.replace(re, '$1'))
					old = replacement.length;
				if (replacement.length == selection.length)
					replacement = replacement.replace(/\S[^]*\S|\S/, (str) => {
						return mark + str + mark;
					})
				return replacement;
			})
		));
	};

	const quote = select((selection) => {
		const lines = selection.split('\n');
		if (lines.some((line) => /^\s*[^\s>]/.test(line)))
			return '>' + lines.join('\n>');
		else
			return lines.map(
				(line) => line.substring(line.indexOf('>') + 1)
			).join('\n');
	});

	const link = select((selection) => `[${selection}]()`);

	makeItalics = wrap(enclose('*'));
	makeBold = wrap(enclose('**'));
	makeQuote = wrap(quote);
	makeLink = wrap(link);

})()
