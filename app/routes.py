"""Routes for searching for groups and getting recommendations."""
import typing

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import or_
from sqlalchemy.sql.expression import func

from .models import Groups

bp = Blueprint("routes", __name__)


def search(query: str) -> typing.Iterable[dict]:
    """Run the search query and process results accordingly."""
    return [
        dict(group_id=row.group_id, artist_name=row.artist_name, name=row.name,)
        for row in Groups.query.filter(
            or_(Groups.artist_name.match(query), Groups.name.match(query))
        )
        .order_by(Groups.artist_name.match(query) + Groups.name.match(query))
        .limit(200)
    ]


def recommendations(group_id: int) -> typing.Iterable[dict]:
    """Query the db for recommendations."""
    group = Groups.query.get(group_id)
    return [g.recommendation_group_id for g in group.recommendations]


def enrich_groups(*group_ids: typing.Iterable[int]) -> typing.Iterable[dict]:
    """Enrich group IDs with metadata from the db."""
    groups = [Groups.query.get(g) for g in group_ids]
    result = [
        dict(group_id=g.group_id, name=g.name, artist_name=g.artist_name,)
        for g in groups
    ]
    if len(result) == 1:
        return result[0]
    return result


@bp.route("/")
def search_form():
    """Present a search form and handle results."""
    query = request.args.get("q", None)
    if query is None or not query:
        return render_template("search.html")
    return render_template("search.html", search_results=search(query))


@bp.route("/recs/<int:group_id>")
def show_recs(group_id: int):
    """Show the recommendations given a group id."""
    return render_template(
        "recs.html",
        group=enrich_groups(group_id),
        recs=enrich_groups(*recommendations(group_id)),
    )


@bp.route("/api/recs/<int:group_id>")
def recs_api(group_id: int):
    """Provide an API for recommendations."""
    return jsonify(dict(antecedent=group_id, consequents=recommendations(group_id)))
