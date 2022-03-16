import json
import sys
from datetime import date
from typing import Iterator

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse


RANKING_URL = "https://www.hltv.org/ranking/teams/"


def get_ranking_html_content() -> BeautifulSoup:
    response = requests.get(RANKING_URL)
    assert response.status_code == 200
    return BeautifulSoup(response.content, features="html.parser")


def iterate_teams(html_content: BeautifulSoup) -> Iterator[str]:
    for div in html_content.select(".ranking .ranked-team"):
        yield div.select_one(".ranking-header .name").text


def get_ranking_date(html_content: BeautifulSoup) -> date:
    date_text = html_content.select_one(".regional-ranking-header").text.strip()
    prefix = "CS:GO World ranking on "
    date_text = date_text[len(prefix):]
    return parse(date_text).date()


def format_list(teams: Iterator[str]) -> str:
    return json.dumps(list(teams), indent=4)


def main(output: str) -> str:
    html_content = get_ranking_html_content()
    ranking_date = get_ranking_date(html_content)
    team_iterator = iterate_teams(html_content)
    result = format_list(team_iterator)

    with open(output, "w") as f:
        f.write(result)
    return ranking_date.isoformat()


if __name__ == "__main__":
    try:
        output_path = sys.argv[1]
    except IndexError:
        print(f"Usage {sys.argv[0]} <output_path>")
        sys.exit(1)
    print(main(output_path))

