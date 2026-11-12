'''
Where pages lead: on a run of the whole spec tier, each page a spec test's browser clients receive (answered 200 with HTML; API clients' answers aside) may lead, by its links, its forms and what it embeds, only to a route of the table (routes.match) or to what the site serves beside the spec (routes.off_spec). A run fails on any that leads elsewhere.

Not checked:
- addresses users wrote, anywhere in what's stored (the rendered text of the *_html columns and users.customtitle, and link posts' URLs), which are theirs, not the page's: an address any of them names isn't checked on any page, by its path;
- the target of a form with its own submit handler (onsubmit), whose script may send it elsewhere or not at all (one that submits as written all the same goes unchecked);
- in an HTML fragment a script fetches (a request with an "xhr" header), addresses that aren't absolute paths or URLs, which the browser reads against the page the fragment goes into.
Nor does it see what a page's scripts request, redirects' targets, mail's links, srcset, formaction, SVG or CSS addresses, or pages answered with another status than 200.
'''
from urllib.parse import urljoin, urlsplit

import lxml.html
from sqlalchemy import text

from files.tests.spec.harness import config, db
from files.tests.spec.harness.routes import match, off_spec

LINKS = "//a/@href | //area/@href"
EMBEDS = "//img/@src | //img/@data-src | //source/@src | //script/@src | //iframe/@src | //link/@href"
STORED_TEXT_COLUMNS = "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public' AND (column_name LIKE '%\\_html' OR (table_name = 'users' AND column_name = 'customtitle'))"
_DEFAULT_PORTS = {"http": 80, "https": 443}

_dead: set[str] = set()
_failures: set[str] = set()
_stored_text_columns: list[tuple[str, str]] | None = None


def site_address(url: str, page_url: str, host: str) -> str | None:
	'''The address on the site `url` (as written on the page at `page_url`) leads to, as a path with any query, or None if it leads off the site.'''
	if url.strip().lower().startswith("javascript:"): return None
	parts = urlsplit(urljoin(page_url, url.strip()))
	try:
		port = parts.port
	except ValueError:
		return None
	if parts.scheme not in _DEFAULT_PORTS or parts.hostname != host.lower() or port not in (None, _DEFAULT_PORTS[parts.scheme]): return None
	return parts.path + (f"?{parts.query}" if parts.query else "")


def form_method(form) -> str | None:
	'''The method a form is sent with (an unknown one is GET, as browsers have it), None for a dialog's, which is sent nowhere.'''
	method = (form.get("method") or "get").strip().lower()
	if method == "dialog": return None
	return method.upper() if method in ("get", "post") else "GET"


def leads(document, page_url: str, host: str, *, fragment: bool = False) -> list[tuple[str, str, str]]:
	'''(kind, method, address on the site) of each link and embed of a page, and each form its browser sends as written; of a `fragment`, only addresses written as absolute paths or URLs.'''
	def address(value):
		if value.startswith("#") or (fragment and not value.strip().startswith(("/", "http:", "https:"))): return None
		return site_address(value, page_url, host)
	found = []
	for kind, xpath in (("link", LINKS), ("embed", EMBEDS)):
		found += [(kind, "GET", a) for a in map(address, document.xpath(xpath)) if a]
	for form in document.xpath("//form[not(@onsubmit)]"):
		method = form_method(form)
		if method and (a := address(form.get("action") or "")):
			found.append(("form", method, a))
	return found


def _written(page_url: str, host: str) -> set[str]:
	'''The paths on the site that what users wrote leads to.'''
	global _stored_text_columns
	with db.engine().connect() as conn:
		if _stored_text_columns is None:
			_stored_text_columns = [tuple(row) for row in conn.execute(text(STORED_TEXT_COLUMNS))]
		values = [value for table, column in _stored_text_columns for (value,) in conn.execute(text(f'SELECT "{column}" FROM "{table}" WHERE "{column}" ILIKE \'%href=%\' OR "{column}" ILIKE \'%src=%\''))]
		urls = [url for (url,) in conn.execute(text("SELECT url FROM submissions WHERE url IS NOT NULL"))]
	for value in values:
		urls += lxml.html.fragment_fromstring(value, create_parent="div").xpath(".//@href | .//@src")
	return {address.partition("?")[0] for address in (site_address(url, page_url, host) for url in urls) if address}


def see(page_label: str, target: str, body: bytes, *, fragment: bool):
	'''Checks where the page answering `target` leads; `page_label` names it in what's reported.'''
	try:
		html = body.decode()
		if not html.strip(): return
		host = config.site_host()
		page_url = target if target.startswith(("http://", "https://")) else config.site_url() + target
		written = None
		for kind, method, address in leads(lxml.html.document_fromstring(html), page_url, host, fragment=fragment):
			path = address.partition("?")[0]
			if match(method, address) or off_spec(path):
				continue
			if written is None:
				written = _written(page_url, host)
			if path not in written:
				_dead.add(f"{page_label}: {kind} {method} {address}")
	except Exception as e:
		# Reported with the run's other findings, failing it
		_failures.add(f"{page_label}: {e!r}")


def output() -> dict:
	return {"dead": sorted(_dead), "failures": sorted(_failures)}


def problems(outputs: list[dict]) -> dict[str, list[str]]:
	'''What fails the run, by heading.'''
	merged = {key: sorted({x for o in outputs for x in o[key]}) for key in ("dead", "failures")}
	return {heading: merged[key] for key, heading in (("dead", "pages leading where no route answers"), ("failures", "pages the harness couldn't read")) if merged[key]}
