import os
import secrets
import subprocess
import time

from PIL import Image, ImageOps
from webptools import gifwebp

from files.helpers.config.environment import IMAGES_DIR

IMAGES_URL_PREFIX = "/images/"


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
	i = Image.open(filename)

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
			gifwebp(input_image=filename, output_image=filename, option="-mixed -metadata none -f 100 -mt -m 6")
		else:
			i = ImageOps.exif_transpose(i)
			i.save(filename, format="WEBP", method=6)

	return image_url(filename)
