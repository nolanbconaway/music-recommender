"""Compute recommendations off the sqlite database.

This can take awhile so it is done as an extra step and stored within the sqlite
database. It assumes make_sqlite has already been run. 

Larger batch sizes take exponentially longer to run due to the resource intensive algo.

Use like:

$ python -m build.make_recommendations data.db --batch 100

Later, find the recommendations table in the sqlite database.
"""

import argparse
import os
import sqlite3
import typing
from pathlib import Path

import tqdm

# see those ?s that need to be filled ?
APRIORI_SQL = """
insert into recommendations (
    group_id, recommendation_group_id, recommendation_number
) 

with config as (
	select
		15 as min_support,
        0.0 as alpha,
	    100.0 as beta,
	    ? as lower, --inclusive
	    ? as upper, --exclusive
		count(*) as total_snatches

	from snatches
),

apriori as (
    -- this one is narsty so comments a lot
    select
        referent.group_id as referent_id,
        consequent.group_id as consequent_id,
        max(consequent_group.snatch_count + alpha) / max(config.total_snatches + alpha + beta) as consequent_support,
        (
            -- lift = confidence  / consequent support
            -- confidence = p(b | a) / p(a)
            -- consequent support = p(b)
            -- therefore lift = (p(b | a) / p(a)) / p(b)
            ((count(*) + max(alpha)) / max(referent_group.snatch_count + alpha + beta))
            / (max(consequent_group.snatch_count + alpha) / max(config.total_snatches + alpha + beta))
        ) as lift

    from config

    -- join referent, add group and filter for min support
    cross join snatches as referent
    inner join groups as referent_group
        on referent.group_id=referent_group.group_id
        and referent_group.snatch_count >= min_support
        and referent.group_id >= lower
        and referent.group_id < upper

    -- join consequent, add group and filter for min support
    -- also ensure the artists are not the same
    inner join snatches as consequent
        on referent.user_id = consequent.user_id
        and referent.group_id != consequent.group_id
    inner join groups as consequent_group
        on consequent.group_id=consequent_group.group_id
        and consequent_group.snatch_count >= min_support
        and consequent_group.artist_id != referent_group.artist_id

    group by 1, 2
),

ranked as (
    select
        row_number() over (partition by referent_id order by lift desc, consequent_support desc) as rn
        , *
    from apriori
    where lift > 1
)

select
    referent_id as group_id,
    consequent_id as recommendation_id,
    rn as recommendation_number
from ranked
where rn <= 5
"""


def parse_args():
    """Parse CLI args."""
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "db_path", type=Path, help="Path to the location of the SQLite DB.",
    )
    p.add_argument(
        "--batch", type=int, default=100, help="Set the batch size.",
    )
    return p.parse_args()


def rebuild_table(db_path):
    """Rebuild the recommendations table."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("drop table if exists recommendations")
        sql = """
        create table recommendations (
            group_id integer not null,
            recommendation_group_id integer not null,
            recommendation_number integer not null,
            foreign key (group_id) references groups(group_id),
            foreign key (recommendation_group_id) references groups(group_id)
        )
        """
        conn.execute(sql)


def make_batch_limits(iterable, n):
    """Convert a sorted iterable into lower/upper values of batches of size n."""
    l = len(iterable)
    for ndx in range(0, l, n):
        chunk = iterable[ndx : min(ndx + n, l)]
        yield (chunk[0], chunk[-1] + 1)


if __name__ == "__main__":
    args = parse_args()

    # get list of group IDs to insert
    with sqlite3.connect(args.db_path) as conn:
        max_group_id = conn.execute("select max(group_id) + 1 from groups").fetchone()[
            0
        ]

        sql = """
            select group_id 
            from groups 
            where group_id >= ? and group_id < ?
            order by 1
        """
        group_ids = [i for (i,) in conn.execute(sql, (1, max_group_id)).fetchall()]

    rebuild_table(args.db_path)

    batches = list(make_batch_limits(group_ids, args.batch))
    for lower, upper in tqdm.tqdm(batches):
        with sqlite3.connect(args.db_path) as conn:
            conn.execute(APRIORI_SQL, (lower, upper))

    # finish off with indexes
    with sqlite3.connect(args.db_path) as conn:
        conn.execute(
            """
            create unique index uidx 
            on recommendations (group_id, recommendation_group_id)
            """
        )
        conn.execute("""create index group_idx on recommendations (group_id)""")
        conn.execute(
            """create index rgroup_idx on recommendations (recommendation_group_id)"""
        )
