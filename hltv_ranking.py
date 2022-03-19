import json
import sys
from datetime import date
from typing import TypedDict

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse

VERSION = "1.0"
RANKING_URL = "https://www.hltv.org/ranking/teams/"


class Ranking(TypedDict):
    version: str
    date: str
    source: str
    type: str
    teams: list["Team"]


class Team(TypedDict):
    name: str


def get_ranking_html_content() -> BeautifulSoup:
    response = requests.get(RANKING_URL)
    assert response.status_code == 200
    return BeautifulSoup(response.content, features="html.parser")


def get_teams(html_content: BeautifulSoup) -> list[Team]:
    teams = []
    for div in html_content.select(".ranking .ranked-team"):
        team_name = div.select_one(".ranking-header .name").text
        teams.append({"name": team_name})
    return teams


def get_ranking_date(html_content: BeautifulSoup) -> date:
    date_text = html_content.select_one(".regional-ranking-header").text.strip()
    prefix = "CS:GO World ranking on "
    date_text = date_text[len(prefix) :]
    return parse(date_text).date()


def format_export(ranking_date: date, teams: list[Team]) -> Ranking:
    return {
        "version": VERSION,
        "date": ranking_date.isoformat(),
        "source": "hltv.org",
        "type": "world",
        "teams": teams,
    }


def main() -> Ranking:
    html_content = get_ranking_html_content()
    ranking_date = get_ranking_date(html_content)
    teams = get_teams(html_content)
    return format_export(ranking_date, teams)


if __name__ == "__main__":
    try:
        output_path = sys.argv[1]
    except IndexError:
        print(f"Usage {sys.argv[0]} <output_path>")
        sys.exit(1)

    data = main()
    with open(output_path, "w") as f:
        f.write(json.dumps(data, indent=4))
    print(data["date"])
