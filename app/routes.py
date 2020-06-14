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


@bp.route("/")
def search_form():
    """Present a search form and handle results."""
    query = request.args.get("q", None)
    if query is None or not query:
        return render_template("search.html")
    return render_template("search.html", search_results=search(query))


def recommendations(group_id) -> typing.Iterable[dict]:
    """Query the db for recommendations."""


@bp.route("/recs/<int:group_id>")
def show_recs(group_id):
    """Show the recommendations given a group id."""
    group = Groups.query.get(group_id)
    recommended_groups = [g.recommended_group for g in group.recommendations]

    return render_template(
        "recs.html",
        group=dict(name=group.name, artist_name=group.artist_name),
        recs=[
            dict(group_id=g.group_id, name=g.name, artist_name=g.artist_name,)
            for g in recommended_groups
        ],
    )
