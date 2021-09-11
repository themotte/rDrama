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

def upload_ibb(filepath=None, file=None, resize=False):
	
	if file:
		format = file.filename.split('.')[-1].lower().replace('jpg','png').replace('jpeg','png')
		filepath = f"image.{format}"
		file.save(filepath)
	else: format = filepath.split('.')[-1].lower().replace('jpg','png').replace('jpeg','png')

	if resize:
		i = IImage.open(filepath)
		size = 100, 100
		frames = ImageSequence.Iterator(i)

		def thumbnails(frames):
			for frame in frames:
				thumbnail = frame.copy()
				thumbnail.thumbnail(size, IImage.ANTIALIAS)
				yield thumbnail

		frames = thumbnails(frames)

		om = next(frames)
		om.info = i.info
		filepath = f"image.{i.format}"
		try: om.save(filepath, save_all=True, append_images=list(frames), loop=0, optimize=True, quality=30)
		except Exception as e:
			print(e)
			return
	elif format != "gif":
		i = IImage.open(filepath)
		filepath = f"image.{i.format}"
		i.save(filepath, optimize=True, quality=30)

	try:
		with open(filepath, 'rb') as f:
			data={'image': base64.b64encode(f.read())} 
			req = requests.post(f'https://api.imgbb.com/1/upload?key={IBB_KEY}', data=data)
		resp = req.json()['data']
		url = resp['url']
	except Exception as e:
		print(e)
		if req: print(req.json())
		return

	return url


def upload_imgur(filepath=None, file=None, resize=False):
	
	if file:
		format = file.filename.split('.')[-1].lower().replace('jpg','png').replace('jpeg','png')
		filepath = f"image.{format}"
		file.save(filepath)
	else: format = filepath.split('.')[-1].lower().replace('jpg','png').replace('jpeg','png')

	if resize:
		# if format = "gif":
		# new_image = Image.new("RGBA", image.size, "WHITE") # Create a white rgba background
		# new_image.paste(image, (0, 0), image)              # Paste the image on the background. Go to the links given below for details.
		# new_image.convert('RGB').save('test.jpg', "JPEG")  # Save as JPEG

		i = IImage.open(filepath)
		size = 100, 100
		frames = ImageSequence.Iterator(i)

		def thumbnails(frames):
			for frame in frames:
				thumbnail = frame.copy()
				thumbnail.thumbnail(size, IImage.ANTIALIAS)
				yield thumbnail

		frames = thumbnails(frames)

		om = next(frames)
		om.info = i.info
		filepath = f"image.{i.format}"
		try: om.save(filepath, save_all=True, append_images=list(frames), loop=0, optimize=True, quality=30)
		except Exception as e:
			print(e)
			return
	elif format != "gif":
		i = IImage.open(filepath)
		filepath = f"image.{i.format}"
		i.save(filepath, optimize=True, quality=30)

	try:
		with open(filepath, 'rb') as f:
			data={'image': base64.b64encode(f.read())} 
			req = requests.post('https://api.imgur.com/3/upload.json', headers = {"Authorization": f"Client-ID {IMGUR_KEY}"}, data=data)
		resp = req.json()['data']
		url = resp['link']
		if not "_d." in url:
			url = url.replace(".png", "_d.png").replace(".jpg", "_d.jpg").replace(".jpeg", "_d.jpeg")
			if "_d." in url: url += "?maxwidth=9999"
	except Exception as e:
		print(e)
		if req: print(req.json())
		return

	new_image = Image(text=url, deletehash=resp["deletehash"])
	g.db.add(new_image)
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