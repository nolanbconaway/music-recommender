"""Test the flask application using much monkeypatch.

I don't want to deal with the search index at test. If it matters the functions
accessing the index should also be tested.
"""

import json

import pytest

import app
import app.routes as routes


@pytest.fixture
def client():
    """Application fixture."""
    application = app.create_app(config_file=None)

    with application.test_client() as cli:
        yield cli


def test_blank_page(client):
    """Test no results when there is no query."""
    rv = client.get("/")
    assert b"Search Results" not in rv.data


def test_search(client, monkeypatch):
    """Test page with mocked search results."""
    monkeypatch.setattr(routes, "search", lambda *x: [1])
    monkeypatch.setattr(
        routes,
        "enrich_groups",
        lambda *x: [dict(group_id=1, name="Group 1 Title", artist_name="Group One"),],
    )

    rv = client.get("/", query_string="q=something")
    assert b"Search Results" in rv.data
    assert b"Group One" in rv.data
    assert b"Group 1 Title" in rv.data


def test_search_single_result(client, monkeypatch):
    """Test page with mocked search results.
    
    Testing case of only one result, there was an uncaught error previously.
    """
    monkeypatch.setattr(routes, "search", lambda *x: [1])
    monkeypatch.setattr(
        routes,
        "enrich_groups",
        lambda *x: dict(group_id=1, name="Group 1 Title", artist_name="Group One"),
    )

    rv = client.get("/", query_string="q=something")
    assert b"Search Results" in rv.data
    assert b"Group One" in rv.data
    assert b"Group 1 Title" in rv.data


def test_search_no_results(client, monkeypatch):
    """Test page with mocked search results.
    
    Testing case of no results, as special handlers are needed.
    """
    monkeypatch.setattr(routes, "search", lambda *x: [])
    monkeypatch.setattr(
        routes, "enrich_groups", lambda *x: [],
    )

    rv = client.get("/", query_string="q=something")
    assert b"Search Results" not in rv.data


def test_recs(client, monkeypatch):
    """Test page with mocked recommendation results."""
    monkeypatch.setattr(routes, "recommendations", lambda *x: [1])
    monkeypatch.setattr(
        routes,
        "enrich_groups",
        lambda *x: [dict(group_id=1, name="Group 1 Title", artist_name="Group One"),],
    )

    rv = client.get("/recs/1")
    assert b"Recommendations for" in rv.data
    assert b"Group One" in rv.data
    assert b"Group 1 Title" in rv.data


def test_recs_api(client, monkeypatch):
    """Test api with mocked recommendation results."""
    monkeypatch.setattr(routes, "recommendations", lambda *x: [1])
    monkeypatch.setattr(
        routes, "enrich_groups", lambda *x: "VALUE",
    )

    expected = dict(antecedent="VALUE", consequents="VALUE", success=True,)
    rv = client.get("/api/recs", query_string="group_id=1")

    assert json.loads(rv.data.decode()) == expected
