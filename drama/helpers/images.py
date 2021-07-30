import requests
from os import environ
from PIL import Image as IImage
import base64
import io
from drama.classes.images import *

CF_KEY = environ.get("CLOUDFLARE_KEY").strip()
CF_ZONE = environ.get("CLOUDFLARE_ZONE").strip()
imgurkey = environ.get("imgurkey").strip()


def upload_file(file=None, resize=None):
	
	if file: file.save("image.gif")
	i = IImage.open("image.gif")


	if resize:
		org_ratio = i.width / i.height
		new_ratio = resize[0] / resize[1]

		if new_ratio > org_ratio:
			crop_height = int(i.width / new_ratio)
			box = (0, (i.height // 2) - (crop_height // 2),
				i.width, (i.height // 2) + (crop_height // 2))
		else:
			crop_width = int(new_ratio * i.height)
			box = ((i.width // 2) - (crop_width // 2), 0,
				(i.width // 2) + (crop_width // 2), i.height)

		i = i.resize(resize, box=box)


	img = io.BytesIO()
	i.save(img, format='GIF')
	req = requests.post('https://api.imgur.com/3/upload.json', headers = {"Authorization": f"Client-ID {imgurkey}"}, data = {'image': base64.b64encode(img.getvalue())})
	try: resp = req.json()['data']
	except Exception as e:
		print(req.text)
		return
	
	try: url = resp['link'].replace(".png", "_d.png").replace(".jpg", "_d.jpg").replace(".jpeg", "_d.jpeg") + "?maxwidth=9999"
	except Exception as e:
		print(req.text)
		return

	new_image = Image(text=url, deletehash=resp["deletehash"])
		
	g.db.add(new_image)
	return(url)