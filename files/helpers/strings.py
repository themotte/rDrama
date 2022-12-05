
import typing

# clean strings for searching
def sql_ilike_clean(my_str):
	return my_str.replace(r'\\', '').replace('_', r'\_').replace('%', '').strip()

# this will also just return a bool verbatim
def bool_from_string(input: typing.Union[str, bool]) -> bool:
	if isinstance(input, bool):
		return input
	if input.lower() in ("yes", "true", "t", "on", "1"):
		return True
	if input.lower() in ("no", "false", "f", "off", "0"):
		return False
	raise ValueError(f"'{input}' is neither a bool nor a recognized string")
