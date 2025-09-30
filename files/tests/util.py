
from bs4 import BeautifulSoup
import json
import random
import re
import string

def formkey_from(text):
    soup = BeautifulSoup(text, 'html.parser')
    formkey = next(tag for tag in soup.find_all("input") if tag.get("name") == "formkey").get("value")
    return formkey

def post_with_formkey(client, post_url, data):
    """
    Helper function to GET a page for formkey, then POST with that formkey.
    Also extracts timestamp field if present (for anti-bot protection).

    The formkey is session-based (not page-specific), so any authenticated page
    will return the same formkey for the session. This automatically determines
    which page to GET based on the POST URL.

    Args:
        client: The test client to use
        post_url: URL to POST to with the formkey
        data: Dict of POST data (formkey will be added automatically)

    Returns:
        Tuple of (post_response, get_response)
    """
    # Determine which page to GET for the formkey
    # For signup, we need the signup page (has special formkey with timestamp)
    # For everything else, use /submit (requires auth, returns session formkey)
    if post_url == "/signup":
        get_url = "/signup"
    else:
        get_url = "/submit"

    # GET the page to extract formkey
    get_response = client.get(get_url)
    assert get_response.status_code == 200, f"Failed to GET {get_url}: {get_response.status_code}"

    # Extract and add formkey to POST data
    data['formkey'] = formkey_from(get_response.text)

    # Also extract timestamp field if present (for anti-bot protection)
    soup = BeautifulSoup(get_response.text, 'html.parser')
    timestamp_input = soup.find("input", attrs={"name": "now"})
    if timestamp_input and timestamp_input.get("value"):
        data['now'] = timestamp_input.get("value")

    # Make the POST request
    post_response = client.post(post_url, data=data)

    return post_response, get_response

def post_json_with_formkey(client, get_url, post_url, json_data):
    """
    Helper function to GET a page for formkey, then POST JSON with that formkey.

    Args:
        client: The test client to use
        get_url: URL to GET for extracting the formkey
        post_url: URL to POST to with the formkey
        json_data: Dict that will be JSON-serialized (formkey will be added automatically)

    Returns:
        Tuple of (post_response, get_response)
    """
    # GET the page to extract formkey
    get_response = client.get(get_url)
    assert get_response.status_code == 200, f"Failed to GET {get_url}: {get_response.status_code}"

    # Extract and add formkey to JSON data
    json_data['formkey'] = formkey_from(get_response.text)

    # Make the POST request with JSON
    import json
    post_response = client.post(post_url,
                               data=json.dumps(json_data),
                               content_type='application/json')

    return post_response, get_response

# not cryptographically secure, deal with it
def generate_text():
    return ''.join(random.choices(string.ascii_lowercase, k=40))


# this is meant to be a utility class that stores post and comment references so you can use them in other calls
# it's pretty barebones and will probably be fleshed out
class ItemData:
    id: str | None = None
    id_full: str | None = None
    url: str | None = None

    @staticmethod
    def from_html(text):
        soup = BeautifulSoup(text, 'html.parser')
        url = soup.find("meta", property="og:url")["content"]

        match = re.search(r'/post/(\d+)/', url)
        if match is None:
            return None
        
        result = ItemData()
        result.id = match.group(1)  	# this really should get yanked out of the JS, not the URL
        result.id_full = f"post_{result.id}"
        result.url = url
        return result

    @staticmethod
    def from_json(text):
        data = json.loads(text)

        soup = BeautifulSoup(data["comment"], 'html.parser')
        divid = soup.find("div")["id"]

        match = re.search(r'comment-(\d+)', divid)
        if match is None:
            return None
        
        result = ItemData()
        result.id = match.group(1)  	# this really should get yanked out of the JS, not the HTML
        result.id_full = f"comment_{result.id}"
        result.url = f"/comment/{result.id}"
        return result
