"""Minimal robots.txt checker.

Python's urllib.robotparser does not understand '*' wildcards (for example
BHX has 'Disallow: *st='), so we implement the simple Google-style rules:
- read the 'User-agent: *' group,
- '*' matches any characters, '$' anchors the end,
- the longest matching rule wins; Allow wins a tie.
"""
import re
import urllib.request
from urllib.parse import urlsplit


def parse_rules(robots_text: str) -> list[tuple[str, str]]:
    """Return [(directive, pattern)] for the 'User-agent: *' group."""
    rules, in_star_group, last_was_agent = [], False, False
    for raw_line in robots_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            # consecutive User-agent lines share one group
            in_star_group = (value == "*") or (in_star_group and last_was_agent)
            last_was_agent = True
            continue
        last_was_agent = False
        if in_star_group and key in ("allow", "disallow") and value:
            rules.append((key, value))
    return rules


def _pattern_to_regex(pattern: str) -> re.Pattern:
    anchored = pattern.endswith("$")
    body = re.escape(pattern.rstrip("$")).replace(r"\*", ".*")
    return re.compile(body + ("$" if anchored else ""))


def is_allowed(robots_text: str, url: str) -> bool:
    parts = urlsplit(url)
    path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    best_len, allowed = -1, True
    for directive, pattern in parse_rules(robots_text):
        # Patterns without a leading '/' or '*' are matched from the start of the path.
        regex = _pattern_to_regex(pattern if pattern.startswith(("/", "*")) else "/" + pattern)
        if regex.match(path):
            length = len(pattern)
            if length > best_len or (length == best_len and directive == "allow"):
                best_len, allowed = length, directive == "allow"
    return allowed


def fetch_robots(base_url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(base_url.rstrip("/") + "/robots.txt",
                                 headers={"User-Agent": "ADY201m-student-project"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")
