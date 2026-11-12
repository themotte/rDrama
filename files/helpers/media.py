import os
import secrets
import time
from io import BytesIO

from flask import abort
from PIL import Image, ImageOps, ImageSequence
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest

from files.helpers.config.environment import IMAGES_DIR, SITE_FULL

IMAGES_URL_PREFIX = "/images/"


class UnreadableImage(BadRequest):
	'''An upload that isn't an image we can process. A 400 when raised during a request.'''
	description = "That file isn't an image we can read."


WEBP_MAX_SIDE = 16383
'''The most pixels a stored image may have on a side: WebP's limit.'''


class ImageTooLarge(UnreadableImage):
	'''An upload too large on a side to store. A 400 when raised during a request.'''
	description = f"That image is too large: images may be at most {WEBP_MAX_SIDE} pixels wide and high."


def attach_images(body:str, files:list[FileStorage]) -> tuple[bool, str]:
	'''Stores up to 4 uploaded images and adds links to them at the end of `body`; returns whether any were attached and the new body. Empty uploads are ignored. Refuses anything that isn't an image with 415.'''
	# An empty file input is sent as an empty upload
	files = [file for file in files if file][:4]
	if not files: return False, body

	for file in files:
		if not file.content_type.startswith('image/'):
			abort(415, "Image files only")
		name = new_image_path()
		file.save(name)
		image = process_image(name)
		body += f'\n\n<a href="{image}">{image}</a>'
	return True, body


def new_image_path() -> str:
	'''A fresh file path in the upload store for a .webp image.'''
	return os.path.join(IMAGES_DIR, f"{time.time_ns()}{secrets.token_hex(4)}.webp")


def image_url(path: str) -> str:
	return IMAGES_URL_PREFIX + os.path.basename(path)


def delete_uploaded_image(url: str | None):
	'''Deletes the stored file behind `url` if it is one of our uploads (a site-relative or same-site absolute /images/ URL); other URLs are left alone.'''
	if not url:
		return
	for prefix in (IMAGES_URL_PREFIX, SITE_FULL + IMAGES_URL_PREFIX):
		if url.startswith(prefix):
			break
	else:
		return
	path = os.path.join(IMAGES_DIR, os.path.basename(url[len(prefix):]))
	if os.path.isfile(path):
		os.remove(path)


def process_image(filename, resize=0) -> str:
	'''Converts the image stored at `filename` (in the upload store) to WebP in place, without the metadata it came with and turned upright, optionally shrinking it to `resize` pixels wide, and returns its URL. Raises UnreadableImage for an upload that can't be read whole, and ImageTooLarge for one too large to store, removing the file.'''
	try:
		_reencode(filename, resize)
	except BaseException as e:
		# Neither the upload nor a half-written result stays in the store
		if os.path.exists(filename): os.remove(filename)
		# PIL reports unreadable, truncated and corrupt images as OSErrors without an errno; real I/O failures have one and stay errors
		if isinstance(e, Image.DecompressionBombError) or (isinstance(e, OSError) and e.errno is None):
			raise UnreadableImage() from e
		raise
	return image_url(filename)


def _reencode(filename, width):
	'''Decodes the image whole and stores it again as WebP, which holds no metadata unless asked to: a GIF or an animated WebP with all its frames, their timing and its loop count, anything else from its first picture, turned by its EXIF orientation; shrunk to `width` pixels wide first if given and wider.'''
	# Decode from memory: frames are read lazily, and the result overwrites the source file
	with open(filename, "rb") as f:
		i = Image.open(BytesIO(f.read()))
	animated = i.format == "GIF" or (i.format == "WEBP" and getattr(i, "is_animated", False))
	if animated:
		frames, durations = [], []
		for frame in ImageSequence.Iterator(i):
			# A frame's timing is known once it is decoded
			frame.load()
			durations.append(frame.info.get("duration", 0))
			frames.append(frame.convert("RGBA"))
	else:
		frames = [_eight_bit(_upright(i))]
	if width and frames[0].width > width:
		size = (width, max(1, round(frames[0].height * width / frames[0].width)))
		frames = [frame.resize(size, Image.LANCZOS) for frame in frames]
	if max(frames[0].size) > WEBP_MAX_SIDE:
		raise ImageTooLarge()
	if animated:
		frames[0].save(filename, format="WEBP", save_all=True, append_images=frames[1:], duration=durations, loop=i.info.get("loop", 0), allow_mixed=True, quality=100, method=6)
	else:
		frames[0].save(filename, format="WEBP", method=6)


def _upright(i):
	'''The image turned by its EXIF orientation; as stored, when its EXIF can't be read.'''
	try:
		return ImageOps.exif_transpose(i)
	except SyntaxError:
		# What PIL raises for EXIF that isn't EXIF: the orientation is unknown, and the rest of the metadata is dropped anyway
		return i.copy()


def _eight_bit(i):
	'''The image with 8 bits a channel, as WebP holds: 16- and 32-bit greys scaled down rather than cut off.'''
	if i.mode.startswith("I"):
		return i.convert("I").point(lambda v: v / 257).convert("L")
	return i
