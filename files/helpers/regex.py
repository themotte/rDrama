import re

# usernames

valid_username_chars = 'a-zA-Z0-9_\\-'
valid_username_regex = re.compile("^[a-zA-Z0-9_\\-]{3,25}$", flags=re.A)
mention_regex = re.compile('(^|\\s|<p>)@(([a-zA-Z0-9_\\-]){1,25})', flags=re.A)
mention_regex2 = re.compile('<p>@(([a-zA-Z0-9_\\-]){1,25})', flags=re.A)

valid_password_regex = re.compile("^.{8,100}$", flags=re.A)

marsey_regex = re.compile("[a-z0-9]{1,30}", flags=re.A)

tags_regex = re.compile("[a-z0-9: ]{1,200}", flags=re.A)

valid_sub_regex = re.compile("^[a-zA-Z0-9_\\-]{3,20}$", flags=re.A)

query_regex = re.compile("(\\w+):(\\S+)", flags=re.A)

title_regex = re.compile("[^\\w ]", flags=re.A)

based_regex = re.compile("based and (.{1,20}?)(-| )pilled", flags=re.I|re.A)

controversial_regex = re.compile('["> ](https:\\/\\/old\\.reddit\\.com/r/[a-zA-Z0-9_]{3,20}\\/comments\\/[\\w\\-.#&/=\\?@%+]{5,250})["< ]', flags=re.A)

fishylinks_regex = re.compile("https?://\\S+", flags=re.A)

spoiler_regex = re.compile('''\\|\\|(.+)\\|\\|''', flags=re.A)
reddit_regex = re.compile('(^|\\s|<p>)\\/?((r|u)\\/(\\w|-){3,25})(?![^<]*<\\/(code|pre|a)>)', flags=re.A)
sub_regex = re.compile('(^|\\s|<p>)\\/?(h\\/(\\w|-){3,25})', flags=re.A)

# Bytes that shouldn't be allowed in user-submitted text
# U+200E is LTR toggle,  U+200F is RTL toggle, U+200B and U+FEFF are Zero-Width Spaces,
# and U+1242A is a massive and terrifying cuneiform numeral
unwanted_bytes_regex = re.compile("\u200e|\u200f|\u200b|\ufeff|\U0001242a")

whitespace_regex = re.compile('\\s+')

strikethrough_regex = re.compile('''~{1,2}([^~]+)~{1,2}''', flags=re.A)

mute_regex = re.compile("/mute @([a-z0-9_\\-]{3,25}) ([0-9])+", flags=re.A)

emoji_regex = re.compile(f"[^a]>\\s*(:[!#@]{{0,3}}[{valid_username_chars}]+:\\s*)+<\\/", flags=re.A)
emoji_regex2 = re.compile(f"(?<!\"):([!#@{valid_username_chars}]{{1,31}}?):", flags=re.A)
emoji_regex3 = re.compile(f"(?<!\"):([!@{valid_username_chars}]{{1,31}}?):", flags=re.A)

snappy_url_regex = re.compile('<a href=\\"(https?:\\/\\/[a-z]{1,20}\\.[\\w:~,()\\-.#&\\/=?@%;+]{5,250})\\" rel=\\"nofollow noopener noreferrer\\" target=\\"_blank\\">([\\w:~,()\\-.#&\\/=?@%;+]{5,250})<\\/a>', flags=re.A)

# Technically this allows stuff that is not a valid email address, but realistically
# we care "does this email go to the correct person" rather than "is this email
# address syntactically valid", so if we care we should be sending a confirmation
# link, and otherwise should be pretty liberal in what we accept here.
email_regex = re.compile('[^@]+@[^@]+\\.[^@]+', flags=re.A)

utm_regex = re.compile('utm_[a-z]+=[a-z0-9_]+&', flags=re.A)
utm_regex2 = re.compile('[?&]utm_[a-z]+=[a-z0-9_]+', flags=re.A)


# uRLs

youtube_regex = re.compile('(<p>[^<]*)(https:\\/\\/youtube\\.com\\/watch\\?v\\=([a-z0-9-_]{5,20})[\\w\\-.#&/=\\?@%+]*)', flags=re.I|re.A)

yt_id_regex = re.compile('[a-z0-9-_]{5,20}', flags=re.I|re.A)

image_regex = re.compile("(^|\\s)(https:\\/\\/[\\w\\-.#&/=\\?@%;+]{5,250}(\\.png|\\.jpg|\\.jpeg|\\.gif|\\.webp|maxwidth=9999|fidelity=high))($|\\s)", flags=re.I|re.A)

linefeeds_regex = re.compile("([^\\n])\\n([^\\n])", flags=re.A)

html_title_regex = re.compile(r"<title>(.{1,200})</title>", flags=re.I)

css_url_regex = re.compile(r'url\(\s*[\'"]?(.*?)[\'"]?\s*\)', flags=re.I|re.A)
