from PIL import Image, ImageOps
from webptools import gifwebp
import subprocess

def process_image(filename=None, resize=0):
	
	i = Image.open(filename)

	exif = i.getexif()
	for k in exif.keys():
		if k != 0x0112:
			exif[k] = None
			del exif[k]
	i.info["exif"] = exif.tobytes()

	if resize:
		subprocess.call(['convert',filename,'-coalesce','-layers', 'TrimBounds','-resize', f'{resize}x>',filename])
	elif i.format.lower() != "webp":
		if i.format.lower() == "gif":
			gifwebp(input_image=filename, output_image=filename, option="-mixed -metadata none -f 100 -mt -m 6")
		else:
			i = ImageOps.exif_transpose(i)
			i.save(filename, format="WEBP", method=6)

	return f'/static{filename}'