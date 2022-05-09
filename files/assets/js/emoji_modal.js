const fav = document.getElementById('EMOJIS_favorite')
const search_bar = document.getElementById('emoji_search')
const search_container = document.getElementById('emoji-tab-search')
let emojis = 1


function loadEmojis(form) {
	if (emojis == 1)
	{
		const xhr = new XMLHttpRequest();
		xhr.open("GET", '/marsey_list');
		xhr.setRequestHeader('xhr', 'xhr');
		var f = new FormData();
		xhr.onload = function() {
			emojis = {
				'marsey': JSON.parse(xhr.response),

				'marseyalphabet': ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','0','1','2','3','4','5','6','7','8','9','exclamationpoint','space','period','questionmark'],
		
				'platy': ['platytrans','platyfuckyou','plarsy','platyabused','platyblizzard','platyboxer','platydevil','platyfear','platygirlmagic','platygolong','platyhaes','platyking','platylove','platyneet','platyold','platypatience','platypopcorn','platyrich','platysarcasm','platysilly','platysleeping','platythink','platytired','platytuxedomask','platyblush','platybruh','platycaveman','platycheer','platydown','platyeyes','platyheart','platylol','platymicdrop','platynooo','platysalute','platyseethe','platythumbsup','platywave'],
		
				'tay': ['taylove','tayaaa','tayadmire','taycat','taycelebrate','taychefkiss','taychristmas','tayclap','taycold','taycrown','tayflex','tayflirt','taygrimacing','tayhappy','tayheart','tayhmm','tayhuh','tayhyperdab','tayjammin','taylaugh','taymindblown','tayno','taynod','taypeace','taypray','tayrun','tayscrunch','tayshake','tayshrug','taysilly','tayslide','taysmart','taystop','taytantrum','taytea','taythink','tayvibin','taywhat','taywine','taywine2','taywink','tayyes'],
		
				'classic': ['flowers','scootlgbt','idhitit','2thumbsup','aliendj','ambulance','angry','angrywhip','argue','aroused','ashamed','badass','banana','band','banghead','batman','bigeyes','bite','blind','blowkiss','blush','bong','bounce','bow','breakheart','bs','cartwheel','cat','celebrate','chainsaw','cheers','clap','cold','confused','crazyeyes','cry','cthulhu','cute','laughing','daydream','ddr','deadpool','devilsmile','diddle','die','distress','disturbing','dizzy','domo','doughboy','drink','drool','dudeweedlmao','edward','electro','elephant','embarrassed','emo','emo2','evil','evilclown','evilgrin','facepalm','fap','flamethrower','flipbird','flirt','frown','gasp','glomp','go','gooby','grr','gtfo','guitar','haha','handshake','happydance','headbang','heart','heartbeat','hearts','highfive','hmm','hmph','holdhands','horny','hug','hugging','hugs','hump','humpbed','hysterical','ily','inlove','jason','jawdrop','jedi','jester','kaboom','kick','kiss','kitty','laughchair','lick','link','lol','lolbeat','loving','makeout','medal','megaman','megamanguitar','meow','metime','mooning','mummy','na','nauseous','nervous','ninja','nod','nono','omg','onfire','ooo','orly','tongueout','paddle','panda','pandabutt','paranoid','party','pat','peek','pikachu','pimp','plzdie','poke','popcorn','pout','probe','puke','punch','quote','raccoon','roar','rofl','roflmao','rolleyes','sad','sadeyes','sadhug','samurai','sarcasm','scoot','scream','shmoopy','shrug','skull','slap','slapfight','sleepy','smackfish','smackhead','smh','smile','smoke','sonic','spank','sparta','sperm','spiderman','stab','star','stare','stfu','suicide','surprisehug','suspicious','sweat','swordfight','taco','talk2hand','tantrum','teehee','thinking','threesome','throw','throwaway','tickle','typing','uhuh','vampbat','viking','violin','vulgar','wah','wat','whip','whipping','wink','witch','wizard','woah','worm','woo','work','worship','wow','xd','yay','zzz'],
		
				'rage': ['trolldespair','clueless','troll','bitchplease','spit','challengeaccepted','contentiouscereal','cryingatcuteness','derp','derpcornsyrup','derpcrying','derpcute','derpdumb','derpeuphoria','derpinahd','derpinapokerface','derpinasnickering','derpprocessing','derprealization','derpsnickering','derptalking','derpthinking','derpthumbsup','derpunimpressed','derpwhy','donotwant','epicfacefeatures','fancywithwine','fffffffuuuuuuuuuuuu','flipthetable','foreveralone','foreveralonehappy','hewillnever','idontknow','interuptedreading','iseewhatyoudidthere','killherkillher','ledesire','leexcited','legenius','lelolidk','lemiddlefinger','lemindblown','leokay','lepanicrunning','lepokerface','lepokerface2','lerageface','leseriousface','likeaboss','lolface','longwhiskers','manymiddlefingers','megusta','motherfucker','motherofgod','mysides','ohgodwhy','pervertedspiderman','picard','ragestrangle','rukiddingme','tfwyougettrolled','trollolol','truestorybro','xallthey','yuno'],
		
				'wojak': ['purerage','naziseethe','holdupjak','ethottalking','chadwomanasian','chadwomanblack','chadwomanlatinx','chadwomannordic','trumpjaktalking','rdramajanny','soyreddit','doomerboy','npcsupport','npcoppse','grugthink','soyconsoomer','soyjaktalking','soyquack','tradboy','sciencejak','soyjakanimeglasses','soymad','boomerportrait','soycry','punchjak','seethejak','chadyes','chadno','abusivewife','ancap','bardfinn','bloomer','boomer','boomermonster','brainletbush','brainletcaved','brainletchair','brainletchest','brainletmaga','brainletpit','chad','chadarab','chadasian','chadblack','chadjesus','chadjew','chadjihadi','chadlatino','chadlibleft','chadnordic','chadsikh','chadusa','coomer','doomer','doomerfront','doomergirl','ethot','fatbrain','fatpriest','femboy','gogetter','grug','monke','nazijak','npc','npcfront','npcmaga','psychojak','ragejak','ragemask','ramonajak','soyjackwow','soyjak','soyjakfront','soyjakhipster','soyjakmaga','soyjakyell','tomboy','zoomer','zoomersoy'],
		
				'flags': ['russia','niger','lgbt','animesexual','blacknation','blm','blueline','dreamgender','fatpride','incelpride','israel','kazakhstan','landlordlove','scalperpride','superstraight','trans','translord','transracial','usa'],
					
				'wolf': ['wombiezolf','wolfdramanomicon','wolfamogus','wolfmarine','wolfromulusremus','wolfrope','wolftinfoil','wolfmarseymask','wolfputin','wolfdrama','wolfcumjar','wolflgbt','wolfmarseyhead','wolfnoir','wolfsherifssmoking','wolftrans','wolfvaporwave','wolfangry','wolfbrains','wolfcry','wolfdead','wolfdevilish','wolffacepalm','wolfhappy','wolfidea','wolfkoala','wolflaugh','wolflove','wolfmeditate','wolfphone','wolfrainbow','wolfroses','wolfsad','wolfsfear','wolfsleep','wolftear','wolfthink','wolfthumbsup','wolfupsidedown','wolfvictory','wolfwave','wolfwink'],
		
				'misc': ['chadyescapy','chadnocapy','capygitcommit','capysneedboat','chadbasedcapy','chadcopecapy','chaddilatecapy','chaddonekingcapy','chaddonequeencapy','chadfixedkingcapy','chadfixedqueencapy','chadokcapy','chadseethecapy','chadsneedcapy','chadthankskingcapy','chadthanksqueencapy','sherpat','xdoubt','gigachadjesus','yotsubafish','yotsubalol','sigmatalking','zoroarkconfused','zoroarkhappy','zoroarkpout','zoroarksleepy','casanovanova','deuxwaifu','flairlessmong','hardislife','redditgigachad','rfybear','etika','sneed','retardedchildren','bruh','autism','doot','kylieface','queenyes','wholesomeseal','gigachadglow','gigachadorthodox','gigachad','gigachad2','gigachad3']
			}

			cringetopia = document.getElementById('EMOJIS_cringetopia')
			if (cringetopia)
				emojis['cringetopia'] = ['19dollarfortnitecard','ahawow','ahayeah','alex','amogus','amogusbubble','amongpoop','amusing','anarchy','angelblob','angry','angryman','awaakesoyjack','backseatmodding','based','bassproshop','berkfail','berkstache','bert','bestmovieever','binface','blackpill','blingbob','blingbobhd','bluepill','booba','boof','boohoo','brainlet','britishmoment','brownnose','bruh','bruhsmoke','brunocheers','brunopog','bussin','byelol','canigetmod','car','cereal','cerkies','chad','chaddiscordmoderator','chadstare','cheeks','cheers','cheesed','cheeseu','chungus','chunky','clueless','cocka','cokeza','comeagain','coom','cope','coping','cryaboutit','cryingcool','cryrage','cum','cummies','cutelittledude','da','dab','dababy','datrolly','davyree','dayum','death','delight','disbelief','disgostang','disgust','donotdisturb','doritoberk','downisrael','downvote','downwert','drbob','drumtime','erotic','evilblob','face','facepalm','factsandlogic','fake','fatcryrage','fear','fedora','fistbumpl','fistbumpr','fjalsunna','floppacheers','floppagun','fluoride','flushspin','funwa','furrymurder','gas','getajob','gigachad','gigajammin','godiwishthatwereme','gogetter','goingcrazy','goinginsane','gold','gone','goofy','goonpog','goteem','grabhand','grind','gun','hahawyd','hatred','heart','heh','hehehe','hesapeonyouknow','hesepsteinyouknow','hesgayyouknow','hesretardedyouknow','hesrightyouknow','hitormiss','holy','hopeless','horny','hot','hulk','hunky','iloveyou','insanity','ipgrabber','irantroll','isawthat','itendsnow','itsover','itsoverseal','jewbob','joebiden','josh','kanyerant','keith','kill','kissin','laughing','lean','leftgun','lessgooooooooooo','lessgoooooooooooo','letsfuckinggooooooooooo','lick','light','like','littledrummerboy','lmao','logo','logoff','lolrage','love','madman','malding','maldinggif','manpain','march','me_lon','menendez','mewhen','mf','mhm','mhmdoubt','mlady','murder','nefarious','nefariousacts','newport','newport~1','nibburger_king','nigerianreaction','nooo','noooo','noose','noperms','normalize','ohwow','okboomer','orange','pain','pardon','payne','peepotalk','pepecringe','pepecringe2','pepeherrington','peperagecry','pepoboner','pepoojamm','phillip','pitchfork','pleading','please','pouroneout40','praiseallah','prayge','psycho','quagmirelet','ratio','real','really','redditnation','redpill','redwojack','regice','ricardosmile','ripbozo','sad','sadcat','sadge','sadtroll','salute','scare','schizothread','secretside','sheesh','shh','shocked','shotty','sigma','sigmamale','sigmasnap','simpjack','siren','skill_issue','slime','slow','smoketime','sniff','society','society2','soy','spit','spit2','splendid','squidwardno','stare','stare1','stfu','stoppedwert','stopwert','susamogus','suscoin','susge','susiety','tacobell','tempest','thanosd','thanoslol','thistbh','thonk','tiktokcoin','tiresome','tm06','troll','trollcrazy','trollcrazyfurry','trollcrazypoint','trollcrazyrussia','trollcrazyukraine','trolldisappointed','trollface','trollinsane','trollsus','truetrue','turbobrainlet','tuvvokmoment','twetwe','unblockme','updonda','upiran','upvote','upwert','vengeance','virgin','wa','waaaah','wallstreet','wertegg','wertpinion','what','whatdeath','whensus','wholesome','wolfcode','womanmoment','woohoo','wtff','xplode','yeeeees','yeet','yes','yeshoney','yet','you','zombie_phillip']
			
			loadEmojis(form);
		}
		xhr.send(f);
	}
	else {
		fav.setAttribute('data-form-destination', form)

		const commentBox = document.getElementById(form)
		commentBox.setAttribute('data-curr-pos', commentBox.selectionStart);
	
		if (fav.innerHTML == "")
		{
			let str = ""
			const favorite_emojis = JSON.parse(localStorage.getItem("favorite_emojis"))
			if (favorite_emojis)
			{
				const sortable = Object.fromEntries(
					Object.entries(favorite_emojis).sort(([,a],[,b]) => b-a)
				);
						
				for (const emoji of Object.keys(sortable).slice(0, 25))
					str += `<button class="btn m-1 px-0 emoji2" onclick="getEmoji('${emoji}')" data-bs-toggle="tooltip" title=":${emoji}:" delay:="0"><img loading="lazy" width=50 src="/e/${emoji}.webp" alt="${emoji}-emoji"></button>`
			
				fav.innerHTML = str
			}
		}
		if (search_bar.value == "") {
			search_container.innerHTML = ""
			document.getElementById("tab-content").classList.remove("d-none");
			if (document.getElementById("EMOJIS_marsey").innerHTML == "")
			{
				for (const [k, v] of Object.entries(emojis)) {
					let container = document.getElementById(`EMOJIS_${k}`)
					let str = ''
					if (k == 'marsey')
						{
							for (const e of v) {
								let k = e.toLowerCase().split(" : ")[0];
								str += `<button class="btn m-1 px-0 emoji2" onclick="getEmoji('${k}')" style="background: None!important; width:60px; overflow: hidden; border: none" data-bs-toggle="tooltip" title=":${k}:" delay:="0"><img loading="lazy" width=50 src="/e/${k}.webp" alt="${k}-emoji"></button>`;
							}
						}
					else {
						for (const e of v) {
							str += `<button class="btn m-1 px-0 emoji2" onclick="getEmoji('${e}')" style="background: None!important; width:60px; overflow: hidden; border: none" data-bs-toggle="tooltip" title=":${e}:" delay:="0"><img loading="lazy" width=50 src="/e/${e}.webp" alt="${e}-emoji"></button>`;
						}
					}
	
					container.innerHTML = str
				}
			}
		}
		else {
			let str = ''
			for (const [key, value] of Object.entries(emojis)) {
				if (key == "marsey")
				{
					for (const e of value) {
						let arr = e.toLowerCase().split(" : ");
						let k = arr[0];
						let v = arr[1];
						if (str.includes(`'${k}'`)) continue;
						if (k.match(search_bar.value.toLowerCase()) || search_bar.value.toLowerCase().match(k) || v.match(search_bar.value.toLowerCase())) {
							str += `<button class="btn m-1 px-0 emoji2" onclick="getEmoji('${k}')" data-bs-toggle="tooltip" title=":${k}:" delay:="0"><img loading="lazy" width=50 src="/e/${k}.webp" alt="${k}-emoji"></button>`;
						}
					}
				}
				else if (key != "marseyalphabet")
				{
					for (const e of value) {
						if (e.match(search_bar.value.toLowerCase()) || search_bar.value.toLowerCase().match(e)) {
							str += `<button class="btn m-1 px-0 emoji2" onclick="getEmoji('${e}')" style="background: None!important; width:60px; overflow: hidden; border: none" data-bs-toggle="tooltip" title=":${e}:" delay:="0"><img loading="lazy" width=50 src="/e/${e}.webp" alt="${e}-emoji"></button>`;
						}
					}
				}
			}
			document.getElementById("tab-content").classList.add("d-none");
			search_container.innerHTML = str
		}
		search_bar.oninput = function () {
			loadEmojis(form);
		};		
	}
}




function getEmoji(searchTerm) {
	const form = fav.getAttribute('data-form-destination')
	const commentBox = document.getElementById(form)
	const old = commentBox.value;
	const curPos = parseInt(commentBox.getAttribute('data-curr-pos'));

	const firstHalf = old.slice(0, curPos)
	const lastHalf = old.slice(curPos)

	let emoji = ':' + searchTerm + ':'
	const previousChar = firstHalf.slice(-1)
	if (firstHalf.length > 0 && previousChar !== " " && previousChar !== "\n") {
		emoji = " " + emoji
	}
	if (lastHalf.length > 0 && lastHalf[0] !== " ") {
		emoji = emoji + " "
	}

	commentBox.value = firstHalf + emoji + lastHalf;

	const newPos = curPos + emoji.length

	commentBox.setAttribute('data-curr-pos', newPos.toString());

	commentBox.dispatchEvent(new Event('input'));

	const favorite_emojis = JSON.parse(localStorage.getItem("favorite_emojis")) || {}
	if (favorite_emojis[searchTerm]) favorite_emojis[searchTerm] += 1
	else favorite_emojis[searchTerm] = 1
	localStorage.setItem("favorite_emojis", JSON.stringify(favorite_emojis))	
}