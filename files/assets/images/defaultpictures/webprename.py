from os import listdir, rename

for filename in listdir():
	newname = filename.lower().replace('.gif','.webp').replace('.png','.webp').replace('.jpeg','.webp').replace('.jpg','.webp')
	if "webp" not in filename and newname not in listdir(): rename(filename, newname)