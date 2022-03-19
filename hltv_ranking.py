import json
import re
import sys
from datetime import date
from typing import Callable, TypedDict, TypeVar

import requests
from bs4 import BeautifulSoup, Tag
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
    rank: int
    name: str
    logo_url: str
    points: int
    change: int
    players: list["Player"]
    url: str


class Player(TypedDict):
    name: str
    full_name: str
    country_code: str
    picture_url: str
    url: str


T = TypeVar("T")


def get_ranking_html_content() -> BeautifulSoup:
    response = requests.get(RANKING_URL)
    assert response.status_code == 200
    return BeautifulSoup(response.text, features="html.parser")


def _extract_attribute(
    team_div: Tag,
    selector: str,
    getter: Callable[[Tag], str] = lambda tag: str(tag.text),
    parser: Callable[[str], T] = lambda val: val,
) -> T:
    container = team_div.select_one(selector)
    value = getter(container)
    return parser(value)


def get_teams(html_content: BeautifulSoup) -> list[Team]:
    teams: list[Team] = []
    for i, div in enumerate(html_content.select(".ranking .ranked-team"), start=1):
        team: Team = {
            "rank": i,
            "name": _extract_attribute(div, ".ranking-header .name"),
            "points": _extract_attribute(
                div,
                ".ranking-header .points",
                parser=lambda val: int(re.sub(r"\D", "", val)),
            ),
            "change": _extract_attribute(
                div,
                ".ranking-header .change",
                parser=lambda val: 0 if val == "-" else int(val),
            ),
            "logo_url": _extract_attribute(
                div, ".team-logo img", getter=lambda tag: str(tag["src"])
            ),
            "players": get_players(div),
            "url": _extract_attribute(
                div,
                ".lineup-con .more a.moreLink:not(.details)",
                getter=lambda tag: str(tag["href"]),
                parser=lambda val: f"https://www.hltv.org{val}",
            ),
        }
        teams.append(team)
    return teams


def get_players(team_div: Tag) -> list[Player]:
    players: list[Player] = []
    for div in team_div.select(".lineup .player-holder"):
        name: str = _extract_attribute(div, ".nick")
        player: Player = {
            "name": _extract_attribute(div, ".nick"),
            "full_name": _extract_attribute(
                div,
                ".playerPicture",
                getter=lambda tag: str(tag["alt"]),
                parser=lambda val: val.replace(f" '{name}' ", " "),
            ),
            "country_code": _extract_attribute(
                div,
                ".flag",
                getter=lambda tag: str(tag["src"]),
                parser=lambda val: val.split("/")[-1].split(".")[0],
            ),
            "picture_url": _extract_attribute(
                div, ".playerPicture", getter=lambda tag: str(tag["src"])
            ),
            "url": _extract_attribute(
                div,
                "a.pointer",
                getter=lambda tag: str(tag["href"]),
                parser=lambda val: f"https://www.hltv.org{val}",
            ),
        }
        players.append(player)
    players.sort(key=lambda p: p["name"].lower())
    return players


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
        f.write(json.dumps(data, indent=4, ensure_ascii=False))
    print(data["date"])
