'''
Files for upload tests, as (filename, bytes, content type) tuples ready for a client's `files=`.
'''
import struct
import zlib
from io import BytesIO

from PIL import Image


def _png_bytes(width, height, rows: bytes | None = None) -> bytes:
	def chunk(kind, data):
		return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
	if rows is None:
		rows = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
	return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def png(width: int, height: int):
	'''A valid solid-red RGB PNG.'''
	return ("image.png", _png_bytes(width, height), "image/png")


def not_an_image():
	'''Claims to be a PNG but isn't one.'''
	return ("image.png", b"not an image", "image/png")


def truncated_png():
	'''A PNG whose pixel data is cut short.'''
	data = _png_bytes(64, 64)
	return ("image.png", data[:len(data) // 2], "image/png")


def oversized_png():
	'''A tiny file declaring 100000x100000 pixels, far past any sane decoding limit.'''
	return ("image.png", _png_bytes(100_000, 100_000, rows=b"\x00"), "image/png")


def text_file():
	return ("notes.txt", b"hello", "text/plain")



def gif(width: int, height: int):
	'''A valid two-frame animated GIF.'''
	frames = [Image.new("RGB", (width, height), color) for color in ("red", "blue")]
	data = BytesIO()
	frames[0].save(data, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
	return ("image.gif", data.getvalue(), "image/gif")
