"""Routes for searching for groups and getting recommendations."""
import typing

from flask import Blueprint, current_app, jsonify, render_template, request

bp = Blueprint("routes", __name__)


def search(query: str) -> typing.Iterable[int]:
    """Run the search query and process results accordingly."""
    with current_app.config["SEARCH_INDEX"].searcher() as searcher:
        return [
            i["group_id"]
            for i in searcher.search(
                current_app.config["QUERY_PARSER"].parse(query), limit=20
            )
            if i.get("recommendations_str")
        ]


def enrich_groups(*group_ids: int) -> typing.Iterable[dict]:
    """Enrich group IDs with metadata."""
    result = []
    with current_app.config["SEARCH_INDEX"].searcher() as searcher:
        for g in group_ids:
            group_result = searcher.document(group_id=g)

            # convert rec groups string to list
            group_result["recommendations"] = [
                int(i) for i in group_result["recommendations_str"].split(",")
            ]
            del [group_result["recommendations_str"]]
            result.append(group_result)

    if len(result) == 1:
        return result[0]
    return result


def recommendations(group_id: int) -> typing.Iterable[int]:
    """Get recommendations for a group ID."""
    with current_app.config["SEARCH_INDEX"].searcher() as searcher:
        doc = searcher.document(group_id=group_id)

    if doc is None or not doc.get("recommendations_str"):
        return []

    return [int(i) for i in doc["recommendations_str"].split(",")]


@bp.route("/")
def search_form():
    """Present a search form and handle results."""
    query = request.args.get("q", None)
    if query is None or not query:
        return render_template("search.html")
    result = enrich_groups(*search(query))
    return render_template(
        "search.html", search_results=[result] if isinstance(result, dict) else result
    )


@bp.route("/recs/<int:group_id>")
def show_recs(group_id: int):
    """Show the recommendations given a group id."""
    recs = recommendations(group_id)
    if not recs:
        return f"No recommendations found for group {group_id}", 404
    return render_template(
        "recs.html",
        group=enrich_groups(group_id),
        recs=enrich_groups(*recs),
    )


@bp.route("/api/recs")
def recs_api():
    """Provide an API for recommendations.

    Pass in a single url param: group_id=<integer>. Get the enriched recommendations.
    That's all.
    """
    group_id = request.args.get("group_id")

    if group_id is None or not group_id.isdigit():
        return (
            jsonify(dict(success=False, message="No/invalid group_id provided.")),
            400,
        )

    group_id = int(group_id)
    recs = recommendations(group_id)

    if not recs:
        return jsonify(dict(success=False, message="No recommendations found."))

    return jsonify(
        dict(
            success=True,
            antecedent=enrich_groups(group_id),
            consequents=enrich_groups(*recs),
        )
    )
