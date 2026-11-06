import typing


def sql_like_literal(text: str) -> str:
	'''`text` escaped to match only itself inside a LIKE pattern, whose wildcards (% and _) and escape character (\\) it may hold.'''
	return text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


# this will also just return a bool verbatim
def bool_from_string(input: typing.Union[str, int, bool]) -> bool:
	if isinstance(input, bool):
		return input
	elif isinstance(input, int):
		return bool(input)
	if input.lower() in ("yes", "true", "t", "on", "1"):
		return True
	if input.lower() in ("no", "false", "f", "off", "0"):
		return False
	raise ValueError(f"'{input}' is neither a bool nor a recognized string")
