'''
Files for upload tests, as (filename, bytes, content type) tuples ready for a client's `files=`.
'''
import os
import struct
import zlib
from io import BytesIO

from PIL import Image


def _png_chunk(kind, data):
	return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def _png_from_idat(width, height, idat: bytes) -> bytes:
	return b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


def _png_bytes(width, height, rows: bytes | None = None) -> bytes:
	if rows is None:
		rows = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
	return _png_from_idat(width, height, zlib.compress(rows))


def png(width: int, height: int):
	'''A valid solid-red RGB PNG.'''
	return ("image.png", _png_bytes(width, height), "image/png")


def large_png(width: int, height: int):
	'''A valid solid-red RGB PNG of many pixels, built without holding its pixels in memory.'''
	row = b"\x00" + b"\xff\x00\x00" * width
	compressor = zlib.compressobj()
	idat = b"".join(compressor.compress(row) for _ in range(height)) + compressor.flush()
	return ("image.png", _png_from_idat(width, height, idat), "image/png")


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


def huge_png():
	'''A tiny file declaring 10000x10000 pixels: past the usual decoding limit, though short of what decoders refuse outright as a bomb.'''
	return ("image.png", _png_bytes(10_000, 10_000, rows=b"\x00"), "image/png")


def text_file():
	return ("notes.txt", b"hello", "text/plain")


def empty():
	'''What a browser sends for a file input left empty: no name and no content.'''
	return ("", b"", "application/octet-stream")



def gif(width: int, height: int):
	'''A valid two-frame animated GIF.'''
	frames = [Image.new("RGB", (width, height), color) for color in ("red", "blue")]
	data = BytesIO()
	frames[0].save(data, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
	return ("image.gif", data.getvalue(), "image/gif")


def noisy_png(width: int, height: int):
	'''A valid PNG of random pixels, which barely compresses: about 3 bytes per pixel.'''
	data = BytesIO()
	Image.frombytes("RGB", (width, height), os.urandom(width * height * 3)).save(data, format="PNG", compress_level=0)
	return ("noise.png", data.getvalue(), "image/png")
