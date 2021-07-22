from flask import abort

def base36encode(number, alphabet='0123456789abcdefghijklmnopqrstuvwxyz'):
	"""Converts an integer to a base36 string."""
	if not isinstance(number, int):
		raise TypeError('number must be an integer')

	base36 = ''
	sign = ''

	if number < 0:
		sign = '-'
		number = -number

	if 0 <= number < len(alphabet):
		return sign + alphabet[number]

	while number != 0:
		number, i = divmod(number, len(alphabet))
		base36 = alphabet[i] + base36

	return sign + base36


def base36decode(number):
	try:
		return int(str(number), 36)
	except ValueError:
		abort(400)


def base_encode(number, base):

	alphabet = '0123456789abcdefghijklmnopqrstuvwxyz'[0:base]

	output = ''
	sign = ''

	if number < 0:
		sign = '-'
		number = -number

	if 0 <= number < len(alphabet):
		return sign + alphabet[number]

	while number != 0:
		number, i = divmod(number, len(alphabet))
		output = alphabet[i] + output

	return sign + output

#got this one from stackoverflow
def hex2bin(hexstr): 
	value = int(hexstr, 16) 
	bindigits = [] 
	 
	# Seed digit: 2**0 
	digit = (value % 2) 
	value //= 2 
	bindigits.append(digit) 
	 
	while value > 0: 
		# Next power of 2**n 
		digit = (value % 2) 
		value //= 2 
		bindigits.append(digit) 
		 
	return ''.join([str(d) for d in bindigits])