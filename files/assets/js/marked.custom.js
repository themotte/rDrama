
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

function markdown(first, second) {
	var input = document.getElementById(first);
	var dest = document.getElementById(second);
	if(dest && input && input.value.trim() !== ''){
		for (var i = 0; i < dest.children.length; i++) {
			dest.removeChild(dest.children[i]);
		}
		const html = marked.parse(input.value);
		// https://github.com/themotte/rDrama/issues/139
		// Remove disallowed tags completely.
		dest.innerHTML = DOMPurify.sanitize(html, {FORBID_TAGS: ['img', 'video', 'source']});
	}
}

function charLimit(form, content) {
	let input = document.getElementById(form);
	let text = document.getElementById(content);
	let length = input.value.length;
	let maxLength = input.getAttribute("maxlength");

	if (length >= maxLength) {
		text.style.color = "#E53E3E";
	}
	else if (length >= maxLength * .72){
		text.style.color = "#FFC107";
	}
	else {
		text.style.color = "#A0AEC0";
	}
	text.innerText = length + ' / ' + maxLength;
}

setTimeout(() => markdown('post-text','preview'), 200);
