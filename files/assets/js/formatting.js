(function() {
	var event = InputEvent
		? function(type, attrs) {
			return new InputEvent(type, attrs);
		}
		: function(type) {
			e = document.createEvent('event');
			e.initEvent(type, false, false);
			return e;
		};
	var escape = function(str) {
		return str.replace(/./g, '[$&]').replace(/[\\^]|]]/g, '\\$&');
	};
	var wrap = function(cb) {
		return function(id) {
			var form = document.getElementById(id);
			if (cb(form)) {
				var e = event('input', { inputType: 'insertReplacementText' });
				form.dispatchEvent(e);
			}
		}
	};
	var select = function(cb) {
		return function(form) {
			var begin = form.selectionStart, end = form.selectionEnd;
			if (begin == end)
				return false;
			form.value = form.value.substring(0, begin)
				+ cb(form.value.substring(begin, end))
				+ form.value.substring(end);
			return true;
		};
	};
	var enclose = function(mark) {
		var re = new RegExp(escape(mark) + '(\\S.*?\\S|\\S)' + escape(mark), 'g');
		return select(function(selection) {
			var replacement = selection.replace(re, '$1');
			if (replacement.length == selection.length)
				replacement = mark + replacement + mark;
			return replacement;
		});
	};
	var quote = select(function(selection) {
		var lines = selection.split('\n');
		if (lines.some(function(line) { return /^\s*[^\s>]/.test(line) }))
			return '>' + lines.join('\n>');
		else
			return lines.map(function(line) {
				return line.substring(line.indexOf('>') + 1);
			}).join('\n');
	});
	makeItalics = wrap(enclose('*'));
	makeBold = wrap(enclose('**'));
	makeQuote = wrap(quote);
})()
