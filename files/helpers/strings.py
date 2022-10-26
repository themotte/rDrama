
# clean strings for searching
def clean_string(my_str):
	return my_str.replace(r'\\', '').replace('_', r'\_').replace('%', '').strip()