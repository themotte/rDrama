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