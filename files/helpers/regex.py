import re

youtube_regex = re.compile('(<p>[^<]*)(https:\\/\\/youtube\\.com\\/watch\\?v\\=([a-z0-9-_]{5,20})[\\w\\-.#&/=\\?@%+]*)', flags=re.I|re.A)

yt_id_regex = re.compile('[a-z0-9-_]{5,20}', flags=re.I|re.A)

image_regex = re.compile("(^|\\s)(https:\\/\\/[\\w\\-.#&/=\\?@%;+]{5,250}(\\.png|\\.jpg|\\.jpeg|\\.gif|\\.webp|maxwidth=9999|fidelity=high))($|\\s)", flags=re.I|re.A)

linefeeds_regex = re.compile("([^\\n])\\n([^\\n])", flags=re.A)

html_title_regex = re.compile(r"<title>(.{1,200})</title>", flags=re.I)

css_url_regex = re.compile(r'url\(\s*[\'"]?(.*?)[\'"]?\s*\)', flags=re.I|re.A)
