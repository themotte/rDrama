import math
from PIL import Image
import io

pat_frames = [
	Image.open("files/assets/images/pat/0.gif").convert("RGBA"),
	Image.open("files/assets/images/pat/1.gif").convert("RGBA"),
	Image.open("files/assets/images/pat/2.gif").convert("RGBA"),
	Image.open("files/assets/images/pat/3.gif").convert("RGBA"),
	Image.open("files/assets/images/pat/4.gif").convert("RGBA"),
	Image.open("files/assets/images/pat/5.gif").convert("RGBA"),
	Image.open("files/assets/images/pat/6.gif").convert("RGBA"),
	Image.open("files/assets/images/pat/7.gif").convert("RGBA"),
	Image.open("files/assets/images/pat/8.gif").convert("RGBA"),
	Image.open("files/assets/images/pat/9.gif").convert("RGBA")
]

def getPat(avatar_file, format="webp"):
	avatar_x = 5
	avatar_y = 5
	avatar_width = 150
	avatar_height = 150
	image_width = 160
	image_height = 160
	hand_x = 0
	hand_y = 0
	delay = 30

	y_scale = [
		1,
		0.95,
		0.9,
		0.85,
		0.8,
		0.8,
		0.85,
		0.9,
		0.95,
		1
	]

	x_scale = [
		0.80,
		0.85,
		0.90,
		0.95,
		1,
		1,
		0.95,
		0.90,
		0.85,
		0.80
	]

	frames = []
	avatar_img = Image.open(avatar_file)
	for i in range(0, 10):
		avatar_actual_x = math.ceil((1 - x_scale[i]) * avatar_width / 2 + avatar_x)
		avatar_actual_y = math.ceil((1 - y_scale[i]) * avatar_height + avatar_y)
		avatar_actual_width = math.ceil(avatar_width * x_scale[i])
		avatar_actual_height = math.ceil(avatar_height * y_scale[i])

		scaled_avatar_img = avatar_img.resize((avatar_actual_width, avatar_actual_height))
		frame = Image.new(mode="RGBA", size=(image_width, image_height))
		frame.paste(scaled_avatar_img, (avatar_actual_x, avatar_actual_y))
		frame.paste(pat_frames[i], (hand_x, hand_y), pat_frames[i])
		frames.append(frame)
	
	output = io.BytesIO()
	frames[0].save(output, format, 
		save_all = True,
		append_images = frames[1:],
		duration = delay,
		loop = 0
	)
	return output


def pat(emoji):
	stream = getPat(open(f'files/assets/images/emojis/{emoji}.webp', "rb"), "webp")
	stream.seek(0)
	open(f'files/assets/images/emojis/{emoji}pat.webp', "wb").write(stream.read())