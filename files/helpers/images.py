import requests
from os import environ, path, remove
from PIL import Image as IImage, ImageSequence
import base64
from files.classes.images import *
from flask import g
from werkzeug.utils import secure_filename

CF_KEY = environ.get("CLOUDFLARE_KEY", "").strip()
CF_ZONE = environ.get("CLOUDFLARE_ZONE", "").strip()
IMGUR_KEY = environ.get("IMGUR_KEY", "").strip()
IBB_KEY = environ.get("IBB_KEY", "").strip()

def upload_ibb(file=None, resize=False):
	
	if file: file.save("image.webp")

	if resize:
		i = IImage.open("image.webp")
		size = 100, 100
		frames = ImageSequence.Iterator(i)

		def thumbnails(frames):
			for frame in frames:
				thumbnail = frame.copy()
				thumbnail.thumbnail(size)
				yield thumbnail

		frames = thumbnails(frames)

		om = next(frames)
		om.info = i.info
		try: om.save("image.webp", save_all=True, append_images=list(frames), loop=0, optimize=True, quality=30)
		except Exception as e:
			print(e)
			return






	else: 
		sequence = []
		im = IImage.open("image.webp")
		for frame in ImageSequence.Iterator(im):
			sequence.append(frame.copy())

		sequence[0].save("image.webp", save_all=True,  append_images = sequence[1:])









	try:
		with open("image.webp", 'rb') as f:
			data={'image': base64.b64encode(f.read())} 
			req = requests.post(f'https://api.imgbb.com/1/upload?key={IBB_KEY}', data=data)
		resp = req.json()['data']
		url = resp['url']
	except Exception as e:
		print(e)
		print(req.text)
		return

	return url


class UploadException(Exception):
	"""Custom exception to raise if upload goes wrong"""
	pass


def upload_video(file):

	file_path = path.join("temp", secure_filename(file.filename))
	file.save(file_path)

	headers = {"Authorization": f"Client-ID {IMGUR_KEY}"}
	with open(file_path, 'rb') as f:
		try:
			r = requests.post('https://api.imgur.com/3/upload', headers=headers, files={"video": f})

			r.raise_for_status()

			resp = r.json()['data']
		except requests.HTTPError as e:
			raise UploadException("Invalid video. Make sure it's 1 minute long or shorter.")
		except:
			raise UploadException("Error, please try again later.")
		finally:
			remove(file_path)

	link = resp['link']
	img = Image(text=link, deletehash=resp['deletehash'])
	g.db.add(img)

	return link