import os
import secrets
import subprocess
import time
from io import BytesIO

from PIL import Image, ImageOps
from werkzeug.exceptions import BadRequest

from files.helpers.config.environment import IMAGES_DIR

IMAGES_URL_PREFIX = "/images/"


class UnreadableImage(BadRequest):
	'''An upload that isn't an image we can process. A 400 when raised during a request.'''
	description = "That file isn't an image we can read."


def new_image_path() -> str:
	'''A fresh file path in the upload store for a .webp image.'''
	return os.path.join(IMAGES_DIR, f"{time.time_ns()}{secrets.token_hex(4)}.webp")


def image_url(path: str) -> str:
	return IMAGES_URL_PREFIX + os.path.basename(path)


def delete_uploaded_image(url: str | None):
	'''Deletes the stored file behind `url` if it is one of our uploads; other URLs are left alone.'''
	if not url or IMAGES_URL_PREFIX not in url:
		return
	path = os.path.join(IMAGES_DIR, os.path.basename(url.split(IMAGES_URL_PREFIX)[1]))
	if os.path.isfile(path):
		os.remove(path)


def process_image(filename, resize=0) -> str:
	'''Converts the image stored at `filename` (in the upload store) to WebP in place, optionally shrinking it to `resize` pixels wide, and returns its URL.'''
	try:
		_convert_image(filename, resize)
	except (OSError, Image.DecompressionBombError) as e:
		# PIL reports unreadable, truncated and corrupt images as OSErrors without an errno; real I/O failures have one and stay errors
		if isinstance(e, OSError) and e.errno is not None:
			raise
		os.remove(filename)
		raise UnreadableImage() from e
	return image_url(filename)


def _convert_image(filename, resize):
	# Decode from memory: frames are read lazily, and the result overwrites the source file
	with open(filename, "rb") as f:
		i = Image.open(BytesIO(f.read()))

	if resize and i.width > resize:
		try: subprocess.call(["convert", filename, "-coalesce", "-resize", f"{resize}>", filename])
		except: pass
	elif i.format.lower() != "webp":

		exif = i.getexif()
		for k in exif.keys():
			if k != 0x0112:
				exif[k] = None
				del exif[k]
		i.info["exif"] = exif.tobytes()

		if i.format.lower() == "gif":
			i.save(filename, format="WEBP", save_all=True, allow_mixed=True, quality=100, method=6)
		else:
			i = ImageOps.exif_transpose(i)
			i.save(filename, format="WEBP", method=6)
