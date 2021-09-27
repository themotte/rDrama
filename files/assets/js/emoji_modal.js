var commentFormID;
function commentForm(form) {
        commentFormID = form;
};

const TEXTAREA_POS_ATTR = 'data-curr-pos'

function getEmoji(searchTerm, form) {
    const commentBox = document.getElementById(form);
    const old = commentBox.value;
    const curPos = parseInt(commentBox.getAttribute(TEXTAREA_POS_ATTR));

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

    commentBox.setAttribute(TEXTAREA_POS_ATTR, newPos);
}

function loadEmojis(form) {

    const emojis = [
    {
        type:'marsey',
        emojis: ['marseywhirlyhat','marsey173','marseycthulhu','marseycuck','marseyemperor','marseyface','marseyjohnson','marseykneel','marseymummy','marseymummy2','marseypanda','marseypumpkin','marseyskeletor','marseystein','marseyvampire','marseyvengeance','marseywitch3','marseylong1','marseylong2','marseylong3','marseypop','marseyqueenlizard','marseyagree','marseybane','marseybog','marseybux','marseycommitted','marseydisagree','marseydizzy','marseyfunko','marseyhealthy','marseykaiser','marseykyle','marseymask','marseymeds','marseykvlt','marseyn8','marseynietzsche','marseyobey','marseypatriot','marseypedo','marseypony','marseypuke','marseyqueen','marseyrage','marseysnek','marseytinfoil','marseywitch2','marseycenter','marseyauthleft','marseyauthright','marseylibleft','marseylibright','marseybinladen','marseycool','marseyjanny2','marseyjones','marseynapoleon','marseysanders','marseyshrug','marseysnoo','marseysoypoint','marseybiting','marseyblush','marseybountyhunter','marseycoonass','marseyfinger','marseyglancing','marseyhappy','marseyhearts','marseyluther','marseypizzashill','marseypokerface','marseypopcorn','marseyrasta','marseysad2','marseysmirk','marseysurprised','marseythomas','marseywitch','marseyyawn','marcusfootball','marje','marmsey','marsey1984','marsey420','marsey4chan','marsey69','marseyakshually','marseyandmarcus','marseyangel','marseyasian','marseybattered','marseybiden','marseybingus','marseyblm','marseyblowkiss','marseybluecheck','marseybong','marseybooba','marseyboomer','marseybrainlet','marseybride','marseyburger','marseybush','marseycamus','marseycanned','marseycarp','marseycatgirl','marseychef','marseychonker','marseychu','marseyclown','marseycomrade','marseyconfused','marseycoomer','marseycop','marseycope','marseycorn','marseycowboy','marseycry','marseycumjar1','marseycumjar2','marseycumjar3','marseycwc','marseydead','marseydepressed','marseydespair','marseydeux','marseydildo','marseydoomer','marseydrunk','marseydynamite','marseyexcited','marseyeyeroll','marseyfacepalm','marseyfamily','marseyfbi','marseyfeet','marseyfeminist','marseyflamethrower','marseyflamewar','marseyfloyd','marseyfug','marseygasp','marseyghost','marseygift','marseygigaretard','marseygigavaxxer','marseyglam','marseyglow','marseygodfather','marseygoodnight','marseygrass','marseygrilling','marseyhacker','marseyhmm','marseyhmmm','marseyilluminati','marseyinabox','marseyira','marseyisis','marseyjam','marseyjamming','marseyjanny','marseyjunkie','marseyking','marseykkk','marseylaugh','marseylawlz','marseylifting','marseylizard','marseylolcow','marseylove','marseymad','marseymanlet','marseymaoist','marseymcarthur','marseymerchant','marseymermaid','marseymommy','marseymouse','marseymyeisha','marseyneckbeard','marseyniqab','marseynpc','marseynun','marseynut','marseyorthodox','marseyowow','marseypainter','marseypanties','marseyparty','marseypat','marseypeacekeeper','marseypharaoh','marseypickle','marseypinochet','marseypipe','marseypirate','marseypoggers','marseypope','marseyproctologist','marseypsycho','marseyqoomer','marseyradioactive','marseyrain','marseyrat','marseyreading','marseyready','marseyrealwork','marseyreich','marseyrentfree','marseyretard','marseyrick','marseyrope','marseyrowling','marseysad','marseysadcat','marseyscarf','marseyschizo','marseyseethe','marseyshisha','marseyshook','marseysick','marseysleep','marseysmug','marseysneed','marseysociety','marseyspider','marseysrdine','marseystroke','marseysus','marseytaliban','marseytank','marseytankushanka','marseytea','marseythonk','marseythumbsup','marseytrain','marseysipping','marseytrans','marseytrans2','marseytroll','marseytrump','marseytwerking','marseyunabomber','marseyuwuw','marseyvan','marseyvaxmaxx','marseywave','marseyworried','marseyxd','marseyyeezus','marseyzoomer','marseyzwei','marsoy','marsoyhype']
    },
    {
        type:'platy',
        emojis: ['platyabused','platyblizzard','platyboxer','platydevil','platyfear','platygirlmagic','platygolong','platyhaes','platyking','platylove','platyneet','platyold','platypatience','platypopcorn','platyrich','platysarcasm','platysilly','platysleeping','platythink','platytired','platytuxedomask','platyblush','platybruh','platycaveman','platycheer','platydown','platyeyes','platyheart','platylol','platymicdrop','platynooo','platysalute','platyseethe','platythumbsup','platywave']
    },
    {
        type:'tay',
        emojis: ['tayaaa','tayadmire','taycat','taycelebrate','taychefkiss','taychristmas','tayclap','taycold','taycrown','tayflex','tayflirt','taygrimacing','tayhappy','tayheart','tayhmm','tayhuh','tayhyperdab','tayjammin','taylaugh','taymindblown','tayno','taynod','taypeace','taypray','tayrun','tayscrunch','tayshake','tayshrug','taysilly','tayslide','taysmart','taystop','taytantrum','taytea','taythink','tayvibin','taywhat','taywine','taywine2','taywink','tayyes']
    },
    {
        type:'classic',
        emojis: ['2thumbsup','aliendj','ambulance','angry','angrywhip','argue','aroused','ashamed','badass','banana','band','banghead','batman','bigeyes','bite','blind','blowkiss','blush','bong','bounce','bow','breakheart','bs','cartwheel','cat','celebrate','chainsaw','cheers','clap','cold','confused','crazyeyes','cry','cthulhu','cute','D','daydream','ddr','deadpool','devilsmile','diddle','die','distress','disturbing','dizzy','domo','doughboy','drink','drool','dudeweedlmao','edward','electro','elephant','embarrassed','emo','emo2','evil','evilclown','evilgrin','facepalm','fap','flamethrower','flipbird','flirt','frown','gasp','glomp','go','gooby','grr','gtfo','guitar','haha','handshake','happydance','headbang','heart','heartbeat','hearts','highfive','hmm','hmph','holdhands','horny','hug','hugging','hugs','hump','humpbed','hysterical','ily','inlove','jason','jawdrop','jedi','jester','kaboom','kick','kiss','kitty','laughchair','lick','link','lol','lolbeat','loving','makeout','medal','megaman','megamanguitar','meow','metime','mooning','mummy','na','nauseous','nervous','ninja','nod','nono','omg','onfire','ooo','orly','p','paddle','panda','pandabutt','paranoid','party','pat','peek','pikachu','pimp','plzdie','poke','popcorn','pout','probe','puke','punch','quote','raccoon','roar','rofl','roflmao','rolleyes','sad','sadeyes','sadhug','samurai','sarcasm','scoot','scream','shmoopy','shrug','skull','slap','slapfight','sleepy','smackfish','smackhead','smh','smile','smoke','sonic','spank','sparta','sperm','spiderman','stab','star','stare','stfu','suicide','surprisehug','suspicious','sweat','swordfight','taco','talk2hand','tantrum','teehee','thinking','threesome','throw','throwaway','tickle','typing','uhuh','vampbat','viking','violin','vulgar','wah','wat','whip','whipping','wink','witch','wizard','woah','worm','woo','work','worship','wow','XD','yay','zzz']
    },
    {
        type:'rage',
        emojis: ['troll','bitchplease','spit','challengeaccepted','contentiouscereal','cryingatcuteness','derp','derpcornsyrup','derpcrying','derpcute','derpdumb','derpeuphoria','derpinahd','derpinapokerface','derpinasnickering','derpprocessing','derprealization','derpsnickering','derptalking','derpthinking','derpthumbsup','derpunimpressed','derpwhy','donotwant','epicfacefeatures','fancywithwine','fffffffuuuuuuuuuuuu','flipthetable','foreveralone','foreveralonehappy','hewillnever','idontknow','interuptedreading','iseewhatyoudidthere','killherkillher','ledesire','leexcited','legenius','lelolidk','lemiddlefinger','lemindblown','leokay','lepanicrunning','lepokerface','lepokerface2','lerageface','leseriousface','likeaboss','lolface','longwhiskers','manymiddlefingers','megusta','motherfucker','motherofgod','mysides','ohgodwhy','pervertedspiderman','picard','ragestrangle','rukiddingme','tfwyougettrolled','trollolol','truestorybro','xallthey','yuno']
    },
    {
        type:'wojak',
        emojis: ['gigachad','gigachad2','chadyes','chadno','abusivewife','ancap','bardfinn','bloomer','boomer','boomermonster','brainletbush','brainletcaved','brainletchair','brainletchest','brainletmaga','brainletpit','chad','chadarab','chadasian','chadblack','chadjesus','chadjew','chadjihadi','chadlatino','chadlibleft','chadnordic','chadsikh','chadusa','coomer','doomer','doomerfront','doomergirl','ethot','fatbrain','fatpriest','femboy','gogetter','grug','monke','nazijak','npc','npcfront','npcmaga','psychojak','ragejak','ragemask','ramonajak','soyjackwow','soyjak','soyjakfront','soyjakhipster','soyjakmaga','soyjakyell','tomboy','zoomer','zoomersoy']
    },
    {
        type:'flags',
        emojis: ['niger', 'lgbt', 'saudi', 'animesexual','blacknation','blm','blueline','dreamgender','fatpride','incelpride','israel','kazakhstan','landlordlove','scalperpride','superstraight','trans','translord','transracial','usa']
    }
    ]

    let search_bar = document.getElementById("emoji_search");
    let search_container = document.getElementById('emoji-tab-search')

    if(search_bar.value == ""){
        let container = document.getElementById(`EMOJIS_favorite`)
        container.innerHTML = container.innerHTML.replace(/@form@/g, form)

        const commentBox = document.getElementById(form);
        commentBox.setAttribute(TEXTAREA_POS_ATTR, commentBox.selectionStart);

        for (i=0; i < emojis.length; i++) {

            let container = document.getElementById(`EMOJIS_${emojis[i].type}`)
            let str = ''
            let arr = emojis[i].emojis

            for (j=0; j < arr.length; j++) {
                if(arr[j].match(search_bar.value)){
                    str += `<button class="btn m-1 px-0 emoji" onclick="getEmoji(\'${arr[j]}\', \'${form}\')" style="background: None!important; width:60px; overflow: hidden; border: none;" data-bs-toggle="tooltip" title=":${arr[j]}:" delay:="0"><img loading="lazy" width=50 src="/assets/images/emojis/${arr[j]}.webp" alt="${arr[j]}-emoji"/></button>`;
                }
            }

            container.innerHTML = str
            search_container.innerHTML = ""
        }
    }else{
        let str = ''
        for (i=0; i < emojis.length; i++) {
            let arr = emojis[i].emojis
            let container = document.getElementById(`EMOJIS_${emojis[i].type}`)
            for (j=0; j < arr.length; j++) {
                if(arr[j].match(search_bar.value.toLowerCase())){
                str += `<button class="btn m-1 px-0 emoji" onclick="getEmoji(\'${arr[j]}\', \'${form}\')" style="background: None!important; width:60px; overflow: hidden; border: none;" data-bs-toggle="tooltip" title=":${arr[j]}:" delay:="0"><img loading="lazy" width=50 src="/assets/images/emojis/${arr[j]}.webp" alt="${arr[j]}-emoji"/></button>`;
                }
            }
            container.innerHTML = ""
        }
        search_container.innerHTML = str
    }
    search_bar.oninput = function(){loadEmojis(form);};
}
