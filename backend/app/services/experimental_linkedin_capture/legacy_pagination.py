from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def set_results_start(url: str, start: int) -> str:
    if not url:
        return ""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.pop("currentJobId", None)
    query["start"] = str(max(0, start))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def next_results_page_url(url: str, page_index: int, results_per_page: int = 25) -> str:
    return set_results_start(url, page_index * results_per_page)
