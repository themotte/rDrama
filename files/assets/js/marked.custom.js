
marked.use({
	extensions: [
		{
			name: 'spoiler',
			level: 'block',
			start: function(src){
				const match = src.match(/\|\|/);
				return match != null ? match.index : -1;
			},
			tokenizer: function(src) {
				const rule  = /^\|\|([\s\S]*?)\|\|/;
				const match = rule.exec(src);
				if(match){
					const token = {             // Token to generate
						type: 'spoiler',        // Should match "name" above
						raw:  match[0],         // Text to consume from the source
						text: match[0].trim(),  // Additional custom properties
						tokens: []              // Array where child inline tokens will be generated
					};
					this.lexer.inline(
						token.text.slice(2,-2), 
						token.tokens
					);
					return token;
				}
			},
			renderer(token) {
				const content = this.parser.parseInline(token.tokens);
				return `<span class="spoiler">${content}</span>`;
			}
		},
		{
			name: 'mention',
			level: 'inline',
			start: function(src){
				const match = src.match(/@[a-zA-Z0-9_\-]+/);
				return match != null ? match.index : -1;
			},
			tokenizer: function(src) {
				const rule  = /^@[a-zA-Z0-9_\-]+/;
				const match = rule.exec(src);
				if(match){
					return {
						type: 'mention',
						raw:  match[0],
						text: match[0].trim().slice(1),
						tokens: []
					};
				}
			},
			renderer(token) {
				const u = token.raw;
				return `<a href="/${u}"><img src="/${u}/pic" class="pp20"> ${u}</a>`;
			}
		}
	]
});

function markdown(input) {
	const dest = input.parentElement.parentElement.querySelector('.preview');
	if (dest) {
		dest.innerHTML = '';
		const html = marked.parse(input.value);
		// https://github.com/themotte/rDrama/issues/139
		// Remove disallowed tags completely.
		dest.innerHTML = DOMPurify.sanitize(html, {FORBID_TAGS: ['img', 'video', 'source']});
	}
}

function charLimit(input) {
	const display = input.parentElement.querySelector('.charcount');
	if (display) {
		const length = input.value.length;
		const maxLength = input.getAttribute("maxlength");
		display.innerText = `${length} / ${maxLength}`;
		if (length >= maxLength) {
			display.style.color = "#E53E3E";
		}
		else if (length >= maxLength * .72) {
			display.style.color = "#FFC107";
		}
		else {
			display.style.color = "#A0AEC0";
		}
	}
}
