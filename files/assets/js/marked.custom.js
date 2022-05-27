function appendToken(parentElement, childToken) {
	var childElement = tokenToHTMLElement(childToken);
	if (typeof childElement === 'string') {
		parentElement.textContent += childElement;
	} else if (childElement !== null) {
		parentElement.appendChild(childElement)
	}
}

function appentTextOrElement(parentElement, textOrElement) {
	if (typeof textOrElement === 'string') {
		parentElement.textContent += textOrElement;
	} else {
		parentElement.appendChild(textOrElement);
	}
}

function motteSpecialMarkdown(text) {
	if (typeof text !== 'string') {
		return '';
	}

	var spoilerMatch = text.match(/^(.*?)\|\|(.*?)\|\|(.*)$/);

	if (spoilerMatch) {
		var left = spoilerMatch[1];
		var mid = spoilerMatch[2];
		var right = spoilerMatch[3];
		var parentSpan = document.createElement('span');
		var leftSpan = document.createElement('span');
		var spoilerSpan = document.createElement('span');
		var rightSpan = document.createElement('span');
		spoilerSpan.textContent = mid;
		spoilerSpan.classList.add('spoiler');
		appentTextOrElement(leftSpan, motteSpecialMarkdown(left));
		appentTextOrElement(rightSpan, motteSpecialMarkdown(right));
		parentSpan.appendChild(leftSpan);
		parentSpan.appendChild(spoilerSpan);
		parentSpan.appendChild(rightSpan);
		return parentSpan;
	} else {
		return text;
	}
}

function tokenToHTMLElement(token) {
	var element = null;

	if (token.type === 'space') {
		element = document.createElement('span');
		element.textContent = ' ';
		return element;
	} else if (typeof token.type === 'undefined' || token.type === 'text') {
		element = document.createElement('span');
		appentTextOrElement(element, motteSpecialMarkdown(token.text));
		return element;
	} else if (token.type === 'hr') {
		return document.createElement('hr');
	} else if (token.type === 'br') {
		return document.createElement('br');
	} else if (token.type === 'heading') {
		element = document.createElement('h' + Math.floor(Math.max(1, Math.min(6, token.depth))));
	} else if (token.type === 'code') {
		element = document.createElement('pre');
		element.setAttribute('data-lang', token.lang);
	} else if (token.type === 'list_item') {
		element = document.createElement('li');
	} else if (token.type === 'blockquote') {
		element = document.createElement('blockquote');
	} else if (token.type === 'list') {
		if (token.ordered) {
			element = document.createElement('ol');
		} else {
			element = document.createElement('ul');
		}
	} else if (token.type === 'table') {
		var table, thead, tbody, tr, th, td;
		table = document.createElement('table');
		table.classList.add('table');
		thead = document.createElement('thead');
		tbody = document.createElement('thead');
		tr = document.createElement('tr');
		for (var x = 0; x < token.header.length; x++) {
			th = document.createElement('th');
			appendToken(th, token.header[x]);
			tr.appendChild(th);
		}
		thead.appendChild(tr);
		table.appendChild(thead);
		for (var y = 0; y < token.rows.length; y++) {
			row = token.rows[y];
			tr = document.createElement('tr');
			for (var x = 0; x < row.length; x++) {
				td = document.createElement('td');
				appendToken(td, row[x]);
				tr.appendChild(td);
			}
			tbody.appendChild(tr);
		}
		table.appendChild(tbody);
		return table;
	} else if (token.type === 'paragraph') {
		element = document.createElement('p');
	} else if (token.type === 'div') {
		element = document.createElement('div');
	} else if (token.type === 'em') {
		element = document.createElement('i');
	} else if (token.type === 'strong') {
		element = document.createElement('b');
	} else if (token.type === 'del') {
		element = document.createElement('del');
	} else if (token.type === 'codespan') {
		element = document.createElement('code');
		element.textContent = token.text;
		return element;
	} else if (token.type === 'escape') {
	} else if (token.type === 'link') {
		element = document.createElement('a');
		element.setAttribute('href', token.href);
		element.textContent = token.text;
		return element;
	} else if (token.type === 'image') {
		element = document.createElement('img');
		element.setAttribute('src', token.href);
		element.setAttribute('alt', token.text);
		return element;
	} else {
		console.log(token);
		element = document.createElement('div');
	}

	var children = (token.tokens || token.items || []);
	if (element !== null && children.length > 0) {
		for (var i = 0; i < children.length; i++) {
			var childElement = tokenToHTMLElement(children[i]);
			if (childElement.outerHTML.match(/"spoiler"/g)) {
				console.log(element, token, childElement, children[i]);
			}
			appendToken(element, children[i]);
		}
	} else if (element.children.length === 0 && element.textContent === '') {
		element.textContent += token.text;
	}

	return element;
}

function safeMarkdown(input) {
	var seenTokens = [];
	var outputToken = {"type": "div", "raw": input, "text": "", "tokens": []};
	function seeRecursive(token) {
		seenTokens.push(token);
		var children = (
			token.tokens
			|| token.items
			|| (token.header||[]).concat(token.rows||[])
			|| []
		);
		if (token.header) {
			children = children.concat(token.header);
		}
		for (var y = 0; y < (token.rows||[]).length; y++) {
			children = children.concat(token.rows[y]);
		}
		for (var i = 0; i < children.length; i++) {
			seeRecursive(children[i]);
		}
	}
	marked.use({
		walkTokens: function(token) {
			if (!seenTokens.includes(token)) {
				outputToken.tokens.push(token);
				seeRecursive(token);
			}
		},
	});
	marked(input);
	marked.use({
		walkTokens: false,
		tokenizer: false,
	});

	[ 'escape', 'del', ];

	return tokenToHTMLElement(outputToken);
}

setTimeout(() => markdown('post-text','preview'), 200);

function markdown(first, second) {
	var input = document.getElementById(first).value;
	
	var dest = document.getElementById(second);
	for (var i = 0; i < dest.children.length; i++) {
		dest.removeChild(dest.children[i]);
	}
	document.getElementById(second).appendChild(safeMarkdown(input));
}

function charLimit(form, text) {

	var input = document.getElementById(form);

	var text = document.getElementById(text);

	var length = input.value.length;

	var maxLength = input.getAttribute("maxlength");

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
