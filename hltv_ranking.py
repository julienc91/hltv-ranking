import json
import sys
from typing import Iterator

import requests
from bs4 import BeautifulSoup


RANKING_URL = "https://www.hltv.org/ranking/teams/"


def iterate_teams() -> Iterator[str]:
    response = requests.get(RANKING_URL)
    assert response.status_code == 200

    parsed_html = BeautifulSoup(response.content, features="html.parser")
    for div in parsed_html.select(".ranking .ranked-team"):
        yield div.select_one(".ranking-header .name").text


def format_list(teams: Iterator[str]) -> str:
    return json.dumps(list(teams), indent=4)


def main(output: str) -> None:
    team_iterator = iterate_teams()
    result = format_list(team_iterator)

    with open(output, "w") as f:
        f.write(result)


if __name__ == "__main__":
    try:
        output_path = sys.argv[1]
    except IndexError:
        print(f"Usage {sys.argv[0]} <output_path>")
        sys.exit(1)
    main(output_path)

