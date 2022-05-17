
function markdown(first, second) {
	var input = document.getElementById(first).value;
	input = input.replace(/\|\|(.*?)\|\|/g, '<span class="spoiler">$1</span>')
	
	var emojis = Array.from(input.matchAll(/:([^\s]{1,31}):/gi))
	if(emojis != null){
		for(i = 0; i < emojis.length; i++){
			var old = emojis[i][0];
			if (old.includes('marseyrandom')) continue
			var emoji = old.replace(/[:!@#]/g,'').toLowerCase();
			var mirroredClass = old.indexOf('!') == -1 ? '' : 'mirrored';
			var emojiClass = old.indexOf('#') == -1 ? 'emoji' : 'emoji-lg';
			if (emoji.endsWith('pat')) {
				emoji = emoji.substr(0, emoji.length - 3);
				var url = old.indexOf('@') != -1 ? `/@${emoji}/pic` : `/e/${emoji}.webp`;
				input = input.replace(old, `<span class="pat-container ${mirroredClass}"><img class="pat-hand" src="/assets/images/hand.webp"><img pat class="${emojiClass}" src="${url}"></span>`);
			} else {
				input = input.replace(old, `<img class="${emojiClass} ${mirroredClass}" src="/e/${emoji}.webp">`);
			}
		}
	}

	if (!first.includes('edit'))
	{
		var options = Array.from(input.matchAll(/\s*\$\$([^\$\n]+)\$\$\s*/gi))
		if(options != null){
			for(i = 0; i < options.length; i++){
				var option = options[i][0];
				var option2 = option.replace(/\$\$/g, '').replace(/\n/g, '')
				input = input.replace(option, '');
				input += '<div class="custom-control"><input type="checkbox" class="custom-control-input" id="' + option2 + '"><label class="custom-control-label" for="' + option2 + '">' + option2 + ' - <a>0 votes</a></label></div>';
			}
		}
		var options = Array.from(input.matchAll(/\s*&&([^\$\n]+)&&\s*/gi))
		if(options != null){
			for(i = 0; i < options.length; i++){
				var option = options[i][0];
				var option2 = option.replace(/&&/g, '').replace(/\n/g, '')
				input = input.replace(option, '');
				input += '<div class="custom-control"><input type="radio" name="choice" class="custom-control-input" id="' + option2 + '"><label class="custom-control-label" for="' + option2 + '">' + option2 + ' - <a>0 votes</a></label></div>';
			}
		}
	}
	
	document.getElementById(second).innerHTML = marked(input)
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
