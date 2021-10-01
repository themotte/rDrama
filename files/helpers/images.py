import requests
from os import environ
from PIL import Image as IImage, ImageSequence
from files.classes.images import *
from webptools import gifwebp

CATBOX_KEY = environ.get("CATBOX_KEY", "").strip()

def upload_ibb(file=None, resize=False):
	
	if file: file.save("image.webp")

	i = IImage.open("image.webp")

	if resize:
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
		om.save("image.webp", save_all=True, append_images=list(frames), loop=0)
	elif i.format.lower() != "webp":
		if i.format.lower() == "gif": gifwebp(input_image="image.webp", output_image="image.webp", option="-q 80")
		else: i.save("image.webp")


	with open("image.webp", 'rb') as f:
		req = requests.post('https://catbox.moe/user/api.php', data={'userhash':CATBOX_KEY, 'reqtype':'fileupload'}, files={'fileToUpload':f})

	return req.text