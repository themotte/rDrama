'''
Assists with adding embeds to submissions. 

This module is not intended to be imported using the `from X import Y` syntax.

Example usage:

```py
import files.helpers.embeds as embeds
embeds.youtube("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
```
'''

import urllib.parse
from typing import Optional

import requests

from files.helpers.config.environment import YOUTUBE_KEY
from files.helpers.config.regex import yt_id_regex

__all__ = ('twitter', 'youtube',)

def twitter(url:str) -> Optional[str]:
	try: 
		return requests.get(
			url="https://publish.twitter.com/oembed", 
			params={"url":url, "omit_script":"t"}, timeout=5).json()["html"]
	except: 
		return None

def youtube(url:str) -> Optional[str]:
	url = urllib.parse.unquote(url).replace('?t', '&t')
	yt_id = url.split('https://youtube.com/watch?v=')[1].split('&')[0].split('%')[0]

	if not yt_id_regex.fullmatch(yt_id): return None

	try:
		req = requests.get(
			url=f"https://www.googleapis.com/youtube/v3/videos?id={yt_id}&key={YOUTUBE_KEY}&part=contentDetails", 
			timeout=5).json()
	except:
		return None
			
	if not req.get('items'): return None
			
	params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
	t = params.get('t', params.get('start', [0]))[0]
	if isinstance(t, str): t = t.replace('s','')

	embed = f'<lite-youtube videoid="{yt_id}" params="autoplay=1&modestbranding=1'
	if t:
		try: 
			embed += f'&start={int(t)}'
		except: 
			pass
		embed += '"></lite-youtube>'
	return embed
