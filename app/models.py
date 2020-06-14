"""Data models."""
from . import db


class Groups(db.Model):
    """Data model for groups."""

    group_id = db.Column(db.Integer, primary_key=True)
    artist_name = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)


class Recommendations(db.Model):
    """Data model for recommendations."""

    recommendation_id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.group_id"), nullable=False)
    recommendation_group_id = db.Column(
        db.Integer, db.ForeignKey("groups.group_id"), nullable=False
    )
    recommendation_number = db.Column(db.Integer, nullable=False)

    group = db.relationship(
        "Groups", backref="recommendations", lazy=True, foreign_keys=group_id,
    )
    recommended_group = db.relationship(
        "Groups",
        backref="recommended",
        lazy=True,
        foreign_keys=recommendation_group_id,
    )
