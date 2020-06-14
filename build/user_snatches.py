"""Get user snatches from the API.

This program checks for data for all user IDs in a range, in order. It saves to a file 
and prints out a progress bar. 

It requires that you export an env variable, API_KEY, with your api key. Also a 
variable, API_URL, with the url to the API.

Use like:

$ python -m build.user_snatches 1 100 users.json

That invocation would grab the data for all users with IDs between 1 and 100 
(inclusive), then save to the specified file. The file will have one JSON payload per 
line.
"""
import argparse
import json
import os
import sys
import time
import typing
from pathlib import Path

import requests
import tqdm

API_URL = os.environ["API_URL"]
API_KEY = os.environ["API_KEY"]
TIMEOUT_SECONDS = 2.0
GET_ATTEMPTS = 100


def get_user_snatches(user_id: int):
    """Get snatched data for a user ID.
    
    Returns a dictionary payload with the a user_id flag and a failure flag (on http 
    error). If success the `data` key will be populated with a nonempty dict.
    """

    def f():
        r = requests.get(
            API_URL,
            params=dict(
                action="user_torrents", id=user_id, type="snatched", limit=10000000000
            ),
            headers={"Authorization": API_KEY},
        )
        time.sleep(TIMEOUT_SECONDS)

        # invalid user raises HTTP error, so exit early.
        if "no such user" in r.content.decode():
            return r

        r.raise_for_status()
        return r

    attempts = 0
    while True:
        try:
            data = f().json()
            break
        except (requests.HTTPError, requests.ConnectionError):
            attempts += 1
            if attempts == GET_ATTEMPTS:
                return dict(user_id=user_id, failed=True, data=dict())
    return dict(user_id=user_id, failed=False, data=data)


def parse_args():
    """Parse CLI args."""
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "start_id", type=int, help="Starting user ID to check (inclusive).",
    )
    p.add_argument(
        "end_id", type=int, help="Final user ID to check (inclusive).",
    )
    p.add_argument("filepath", type=Path, help="Save destination path.")
    p.add_argument(
        "--append",
        action="store_true",
        default=False,
        help="Append to the end of the file rather than overwrite. default no append.",
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
    if args.filepath.exists() and not args.append and not args.force:
        r = input(f"{args.filepath} will be overwritten. press y to continue.\n")
        if r.lower().strip() != "y":
            print("abort.")
            sys.exit(0)

    # touch the file to make sure it exists, empty it out if not appending.
    args.filepath.touch()
    if not args.append:
        args.filepath.write_text("")

    # do the scraping
    for user_id in tqdm.tqdm(range(args.start_id, args.end_id + 1)):
        data = get_user_snatches(user_id)
        with args.filepath.open("a") as fh:
            fh.write(json.dumps(data))
            fh.write("\n")
