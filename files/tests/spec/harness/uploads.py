'''
Files for upload tests, as (filename, bytes, content type) tuples ready for a client's `files=`.
'''
import os
import struct
import zlib
from io import BytesIO

from PIL import Image, PngImagePlugin


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


_TYPES = {"JPEG": ("photo.jpg", "image/jpeg"), "PNG": ("photo.png", "image/png"), "WEBP": ("photo.webp", "image/webp"), "GIF": ("image.gif", "image/gif")}


def _metadata(marker: str, orientation: int) -> tuple[Image.Exif, bytes]:
	exif = Image.Exif()
	exif[0x010F] = f"{marker} make"
	exif[0x0131] = f"{marker} software"
	exif[0x0112] = orientation
	gps = exif.get_ifd(0x8825)
	gps[1], gps[2] = "N", (1.0, 2.0, 3.0)
	xmp = f'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description xmlns:tiff="http://ns.adobe.com/tiff/1.0/" tiff:Model="{marker} model"/></rdf:RDF></x:xmpmeta>'
	return exif, xmp.encode()


def photo(image_format: str, width: int, height: int, marker: str, orientation: int = 1):
	'''A red photo in `image_format` (JPEG, PNG or WEBP) carrying identifying metadata that names `marker`: EXIF camera make, software and a GPS position, an XMP packet and, in a PNG, a text chunk. `orientation` is its EXIF orientation (6: to be turned a quarter clockwise).'''
	exif, xmp = _metadata(marker, orientation)
	options = {"exif": exif}
	if image_format == "PNG":
		info = PngImagePlugin.PngInfo()
		info.add_text("Author", f"{marker} author")
		info.add_itxt("XML:com.adobe.xmp", xmp.decode())
		options["pnginfo"] = info
	else:
		options["xmp"] = xmp
	data = BytesIO()
	Image.new("RGB", (width, height), "red").save(data, format=image_format, **options)
	name, content_type = _TYPES[image_format]
	return (name, data.getvalue(), content_type)


def multi_picture_jpeg(width: int, height: int, orientation: int):
	'''A JPEG holding a second picture (MPO), as some phones save photos: a red one, then a blue one, with EXIF orientation `orientation`.'''
	exif, _ = _metadata("mpo", orientation)
	data = BytesIO()
	Image.new("RGB", (width, height), "red").save(data, format="MPO", save_all=True, append_images=[Image.new("RGB", (width, height), "blue")], exif=exif)
	return ("photo.jpg", data.getvalue(), "image/jpeg")


def animation(image_format: str, durations: list[int], loop: int):
	'''An animated GIF or WebP of 8x8 frames, one a duration, each shown that many milliseconds, played `loop` times (0: forever).'''
	frames = [Image.new("RGB", (8, 8), (40 * n % 256, 0, 255 - 40 * n % 256)) for n in range(len(durations))]
	data = BytesIO()
	frames[0].save(data, format=image_format, save_all=True, append_images=frames[1:], duration=durations, loop=loop)
	name, content_type = _TYPES[image_format]
	return (name, data.getvalue(), content_type)


def unreadable_exif_webp():
	'''A 64x64 WebP whose EXIF block isn't EXIF.'''
	data = BytesIO()
	Image.new("RGB", (64, 64), "red").save(data, format="WEBP", exif=b"Exif\x00\x00not exif")
	return ("photo.webp", data.getvalue(), "image/webp")


def too_wide_png():
	'''A PNG 16384 pixels wide, one more than WebP holds.'''
	data = BytesIO()
	Image.new("L", (16384, 1)).save(data, format="PNG")
	return ("wide.png", data.getvalue(), "image/png")


def truncated_gif(width: int, height: int):
	'''A three-frame animated GIF whose first frame is whole and whose last is cut short.'''
	frames = [Image.frombytes("RGB", (width, height), os.urandom(width * height * 3)) for _ in range(3)]
	data = BytesIO()
	frames[0].save(data, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
	whole = data.getvalue()
	return ("image.gif", whole[:len(whole) * 3 // 4], "image/gif")


def grey_16_bit_png(level: int):
	'''An 8x8 PNG of 16-bit grey at `level` (of 65535).'''
	data = BytesIO()
	Image.new("I;16", (8, 8), level).save(data, format="PNG")
	return ("grey.png", data.getvalue(), "image/png")
