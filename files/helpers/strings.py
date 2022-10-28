
# clean strings for searching
def sql_ilike_clean(my_str):
	return my_str.replace(r'\\', '').replace('_', r'\_').replace('%', '').strip()