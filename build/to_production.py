"""Migrate the relevant data in the sqlite database to a production datastore.

The datastore is designed to make it quick to retrieve recommendations given a group ID
and to make it easy to search for groups. Requires that the mysql database uri is 
exported via SQLALCHEMY_DATABASE_URI.

This assumes you have already run make_recommendations on the source sqlite data. Set 
the batch size to control the number of groups of data that is migrated at a time.

Use like:

$ python -m build.to_production data.db

Then keep an eye on your production datastore for your data.
"""

import argparse
import os
import sqlite3
import typing
from pathlib import Path

import tqdm
from sqlalchemy import create_engine


def parse_args():
    """Parse CLI args."""
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "db_path", type=Path, help="Path to the location of the SQLite DB.",
    )
    p.add_argument(
        "--batch", type=int, default=10000, help="Set the batch size.",
    )
    return p.parse_args()


def rebuild_tables(engine):
    """Rebuild the groups table."""
    with engine.connect() as conn:
        # need to drop recs to drop groups
        conn.execute("drop table if exists recommendations")
        conn.execute("drop table if exists groups")
        sql = """
        create table groups (
            group_id integer primary key,
            artist_name varchar(10000) not null,
            name varchar(10000) not null,
            fulltext (artist_name),
            fulltext (name),
            fulltext (artist_name, name)
        )
        charset=utf8
        """
        conn.execute(sql)

        sql = """
        create table recommendations (
            recommendation_id integer primary key auto_increment,
            group_id integer not null,
            recommendation_group_id integer not null,
            recommendation_number integer not null,
            foreign key (group_id) references groups(group_id),
            foreign key (recommendation_group_id) references groups(group_id),
            index (group_id),
            index (recommendation_group_id),
            unique key (group_id, recommendation_group_id) 
        )
        """
        conn.execute(sql)


def insert_groups(sqlite_path, engine, lower: int, upper: int):
    """Insert groups into the database."""
    with sqlite3.connect(sqlite_path) as sqlite_conn, engine.connect() as prod_conn:
        sql = """
        select 
            groups.group_id, 
            artists.name as artist_name, 
            groups.name
        from groups
        inner join artists
            on groups.artist_id = artists.artist_id
        where groups.group_id >= ?
        and groups.group_id < ?
        """
        sqlite_res = sqlite_conn.execute(sql, (lower, upper)).fetchall()

        sql = """
            insert into groups (group_id, artist_name, name) 
            values (%s, %s, %s) 
        """
        prod_conn.execute(sql, sqlite_res)


def insert_recommendations(sqlite_path, engine, lower: int, upper: int):
    """Insert recommendations into the database."""
    with sqlite3.connect(sqlite_path) as sqlite_conn, engine.connect() as prod_conn:
        sql = """
        select 
            group_id, 
            recommendation_group_id, 
            recommendation_number
        from recommendations
        where group_id >= ? and group_id < ?
        """
        sqlite_res = sqlite_conn.execute(sql, (lower, upper)).fetchall()

        sql = """
            insert into recommendations (
                group_id, 
                recommendation_group_id, 
                recommendation_number) 
            values (%s, %s, %s) 
        """
        prod_conn.execute(sql, sqlite_res)


def make_batch_limits(iterable, n):
    """Convert sorted iterable into lower/upper values of batches of size n."""
    l = len(iterable)
    for ndx in range(0, l, n):
        chunk = iterable[ndx : min(ndx + n, l)]
        yield (chunk[0], chunk[-1] + 1)


if __name__ == "__main__":
    engine = create_engine(os.environ["SQLALCHEMY_DATABASE_URI"])
    args = parse_args()

    # get list of group IDs to insert
    with sqlite3.connect(args.db_path) as conn:
        sql = """
        select group_id 
        from groups 
        order by 1
        """
        group_ids = [i for (i,) in conn.execute(sql)]

    # erase and start from scratch
    rebuild_tables(engine)

    batches = list(make_batch_limits(group_ids, args.batch))

    print("Inserting groups data")
    for lower, upper in tqdm.tqdm(batches):
        insert_groups(args.db_path, engine, lower, upper)

    print("Inserting recommendations data")
    for lower, upper in tqdm.tqdm(batches):
        insert_recommendations(args.db_path, engine, lower, upper)
