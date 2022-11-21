
# clean strings for searching
def sql_ilike_clean(my_str):
	return my_str.replace(r'\\', '').replace('_', r'\_').replace('%', '').strip()

def bool_from_string(str_in: str) -> bool:
	if str_in.lower() in ("yes", "true", "t", "1"):
		return True
	if str_in.lower() in ("no", "false", "f", "0"):
		return False
	raise ValueError()
