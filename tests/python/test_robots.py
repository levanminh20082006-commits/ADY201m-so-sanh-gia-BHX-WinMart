"""robots.txt rules, using a copy of the real BHX/WinMart rules saved on 2026-10-12."""
from report2.robots import is_allowed

BHX_RULES = """User-agent: *
Disallow: /gio-hang
Disallow: /sp/*
Disallow: /tim-kiem?key=*
Disallow: *st=
Allow: /sp/allowed-page
"""
WINMART_RULES = "User-agent: *\nDisallow: /_next/\n"


def test_category_pages_are_allowed():
    assert is_allowed(BHX_RULES, "https://www.bachhoaxanh.com/sua-tuoi")
    assert is_allowed(WINMART_RULES, "https://winmart.vn/sua-cac-loai--c08?storeCode=1535")


def test_disallowed_paths_and_wildcards():
    assert not is_allowed(BHX_RULES, "https://www.bachhoaxanh.com/gio-hang")
    assert not is_allowed(BHX_RULES, "https://www.bachhoaxanh.com/sp/abc")
    assert not is_allowed(BHX_RULES, "https://www.bachhoaxanh.com/sua-tuoi?st=1")   # '*st=' wildcard
    assert not is_allowed(WINMART_RULES, "https://winmart.vn/_next/data/x.json")


def test_longer_allow_rule_wins():
    assert is_allowed(BHX_RULES, "https://www.bachhoaxanh.com/sp/allowed-page")


def test_other_user_agent_groups_are_ignored():
    rules = "User-agent: Googlebot\nDisallow: /\n\nUser-agent: *\nDisallow: /private\n"
    assert is_allowed(rules, "https://example.com/public")
    assert not is_allowed(rules, "https://example.com/private/x")
