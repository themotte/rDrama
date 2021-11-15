from PIL import Image
from os import listdir
from webptools import gifwebp

for filename in listdir():
	if filename.startswith("webp"): continue
	i = Image.open(filename)
	if i.format.lower() != "webp":
		if i.format.lower() == "gif": gifwebp(input_image=filename, output_image=filename, option="-q 80")
		else: i.save(filename, format="WEBP")