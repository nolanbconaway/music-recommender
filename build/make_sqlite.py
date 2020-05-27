"""Build a SQLite database off of the JSON payloads from user_snatches.

Those payloads are designed for hassle-free saving, the SQLite database should be set
up for ease of access.

Use like:

$ python -m make_sqlite data.json data.db

Later, find your nicely formatted SQLite in data.db.
"""
import argparse
import json
import sqlite3
import sys
import typing
from pathlib import Path

import requests
import tqdm


def lines_in_file(filepath: Path) -> int:
    """Count the lines in a file."""
    with filepath.open("r") as f:
        n = sum(1 for line in f)
    return n


def make_fresh_db(db_path: Path) -> None:
    """Clear out the tables needed for the database, then rebuild."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("drop table if exists snatches")
        conn.execute("drop table if exists groups")
        sql = """
        create table groups (
            group_id integer primary key,
            name text not null,
            artist_name text not null
        )
        """
        conn.execute(sql)
        sql = """
        create table snatches (
            snatch_id integer primary key,
            user_id integer not null,
            group_id integer not null,
            foreign key (group_id) references groups(group_id),
            unique(user_id, group_id)
        )
        """
        conn.execute(sql)
        sql = """
        create view support as 
        select group_id, count(*) as freq, count(*) / (n + 0.0) as p
        from snatches
        cross join (select count(*) as n from snatches) as t
        group by 1
        """
        conn.execute(sql)


def process_line(db_path: Path, line: str) -> None:
    """Run the processing for a single line of the file."""
    if not line:
        return

    data = json.loads(line)

    # skip HTTP errors, invalid users, hidden users.
    if data["failed"]:
        return
    if data["data"]["status"] != "success":
        return
    if data["data"]["response"]["snatched"] == "hidden":
        return

    snatches = data["data"]["response"]["snatched"]

    group_tuples = [(i["groupId"], i["name"], i["artistName"]) for i in snatches]
    snatch_tuples = [(data["user_id"], i["groupId"]) for i in snatches]
    with sqlite3.connect(db_path) as conn:
        # always do this first, otherwise defaults to off
        conn.execute("pragma foreign_keys = on")

        # insert groups first for foreign key support
        # update on uniqueness violation
        sql = """
        insert into groups (group_id, name, artist_name) 
        values (?, ?, ?)
        on conflict(group_id) do update set
            name=excluded.name,
            artist_name=excluded.artist_name
        """
        conn.executemany(sql, group_tuples)

        # add snatches, ignore duplicates.
        sql = """
        insert into snatches (user_id, group_id) values (?, ?)
        on conflict do nothing
        """
        conn.executemany(sql, snatch_tuples)


def parse_args():
    """Parse CLI args."""
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "json_path", type=Path, help="Path to the raw JSON data.",
    )
    p.add_argument(
        "db_path", type=Path, help="Path to the location of the SQLite DB.",
    )
    p.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="Option to disable prompt on overwrite.",
    )
    return p.parse_args()


#  do it
if __name__ == "__main__":

    args = parse_args()

    # make sure the user wants to overwrite.
    if args.db_path.exists() and not args.force:
        r = input(f"{args.db_path} will be overwritten. press y to continue.\n")
        if r.lower().strip() != "y":
            print("abort.")
            sys.exit(0)

    # delete it, and make a new one
    if args.db_path.exists():
        args.db_path.unlink()
    make_fresh_db(args.db_path)

    # need this for the progress bar
    total_lines = lines_in_file(args.json_path)

    # process JSON
    with args.json_path.open("r") as f:
        for line in tqdm.tqdm(f, total=total_lines):
            process_line(args.db_path, line)

    # finish off with some additional indexes, views
    with sqlite3.connect(args.db_path) as conn:
        conn.execute("create index group_idx on snatches (group_id)")
