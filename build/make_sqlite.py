"""Build a SQLite database off of the JSON payloads from user_snatches.

Those payloads are designed for hassle-free saving, the SQLite database should be set
up for ease of access.

Use like:

$ python -m build.make_sqlite data.json data.db

Later, find your nicely formatted SQLite in data.db.
"""
import argparse
import html
import json
import sqlite3
import sys
from pathlib import Path

import tqdm


def lines_in_file(filepath: Path) -> int:
    """Count the lines in a file."""
    with filepath.open("r") as f:
        n = sum(1 for line in f)
    return n


def make_fresh_db(db_path: Path) -> None:
    """Execute the DDL needed for a fresh database."""
    ddl = """
    create table artists (
        artist_id integer primary key,
        name text not null
    );

    create table groups (
        group_id integer primary key,
        artist_id integer not null,
        name text not null,
        snatch_count integer not null default 1,
        foreign key (artist_id) references artists(artist_id)
    );

    create table users (
        user_id integer primary key, 
        snatch_count integer not null
    );

    create table snatches (
        snatch_id integer primary key,
        user_id integer not null,
        group_id integer not null,
        foreign key (group_id) references groups(group_id),
        foreign key (user_id) references users(user_id),
        unique(user_id, group_id)
    );
    """
    with sqlite3.connect(db_path) as conn:
        conn.executescript(ddl)


def process_line(db_path: Path, line: str) -> None:
    """Run the processing for a single line of the file."""
    if not line:
        return

    data = json.loads(line)
    user_id = data["user_id"]

    # skip HTTP errors, invalid users, hidden users.
    if data["failed"]:
        return
    if data["data"]["status"] != "success":
        return
    if data["data"]["response"]["snatched"] == "hidden":
        return

    # grab the snatch data, skip compilation snatches (no artistId)
    snatches = [i for i in data["data"]["response"]["snatched"] if "artistId" in i]
    if not snatches:
        return

    # get tuples needed for SQL inserts.
    artist_tuples = set(
        [(i["artistId"], html.unescape(i["artistName"])) for i in snatches]
    )
    group_tuples = set(
        [(i["groupId"], i["artistId"], html.unescape(i["name"])) for i in snatches]
    )
    snatch_tuples = set([(user_id, i["groupId"]) for i in snatches])
    user_tuple = (user_id, len(group_tuples))

    with sqlite3.connect(db_path) as conn:
        # always do this first, otherwise defaults to off
        conn.execute("pragma foreign_keys = on")

        # insert artists first, they have no dependencies
        sql = """
        insert into artists (artist_id, name) 
        values (?, ?)
        on conflict(artist_id) do update set 
            name=excluded.name
        """
        conn.executemany(sql, list(artist_tuples))

        # insert users second, they also have no dependencies.
        # The JSON should be unique on user, but in case it isnt just replace.
        sql = """
        insert into users (user_id, snatch_count) 
        values (?, ?)
        on conflict(user_id) do update set 
            snatch_count=excluded.snatch_count
        """
        conn.execute(sql, user_tuple)

        # insert groups third, they require artist and are needed for snatch
        sql = """
        insert into groups (group_id, artist_id, name) 
        values (?, ?, ?)
        on conflict(group_id) do update set
            artist_id=excluded.artist_id,
            name=excluded.name,
            snatch_count=snatch_count + 1
        """
        conn.executemany(sql, list(group_tuples))

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

    # finish it off with some indexes
    with sqlite3.connect(args.db_path) as conn:
        sql = """
        create index snatch_group_idx on snatches (group_id);
        create index snatch_user_idx on snatches (user_id);
        create index group_artist_idx on groups (artist_id);
        """
        conn.executescript(sql)
