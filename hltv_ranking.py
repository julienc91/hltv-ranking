import json
import locale
import re
import sys
from datetime import date, timedelta
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


def _extract_attribute(
    team_div: Tag,
    selector: str,
    getter: Callable[[Tag], str] = lambda tag: str(tag.text),
    parser: Callable[[str], T] = lambda val: val,
) -> T:
    container = team_div.select_one(selector)
    value = getter(container)
    return parser(value)


class HLTVRanking:
    BASE_URL = "https://www.hltv.org"
    LATEST_RANKING_PATH = "/ranking/teams/"

    def _get_ranking_url(self, ranking_at: date | None) -> str:
        url = self.BASE_URL + self.LATEST_RANKING_PATH
        if ranking_at is None:
            return url

        ranking_date = ranking_at - timedelta(days=date.weekday(ranking_at))
        return f"{url}{ranking_date.year}/{ranking_date.strftime('%B').lower()}/{ranking_date.day}"

    def _get_ranking_html_content(self, ranking_at: date | None) -> BeautifulSoup:
        ranking_url = self._get_ranking_url(ranking_at)
        response = requests.get(ranking_url)
        assert response.status_code == 200, ranking_url
        return BeautifulSoup(response.text, features="html.parser")

    def _get_teams(self, html_content: BeautifulSoup) -> list[Team]:
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
                "players": self._get_players(div),
                "url": _extract_attribute(
                    div,
                    ".lineup-con .more a.moreLink:not(.details)",
                    getter=lambda tag: str(tag["href"]),
                    parser=lambda val: f"https://www.hltv.org{val}",
                ),
            }
            teams.append(team)
        return teams

    def _get_players(self, team_div: Tag) -> list[Player]:
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

    def _get_ranking_date(self, html_content: BeautifulSoup) -> date:
        date_text = html_content.select_one(".regional-ranking-header").text.strip()
        prefix = "CS:GO World ranking on "
        date_text = date_text[len(prefix) :]
        return parse(date_text).date()

    def _format_export(self, ranking_date: date, teams: list[Team]) -> Ranking:
        return {
            "version": VERSION,
            "date": ranking_date.isoformat(),
            "source": "hltv.org",
            "type": "world",
            "teams": teams,
        }

    @staticmethod
    def format_output_path(template_path: str, ranking: Ranking) -> str:
        mapping = {
            "{{ranking_date}}": ranking["date"],
        }
        for key, value in mapping.items():
            template_path = template_path.replace(key, value)
        return template_path

    def export_to_dict(self, ranking_at: date | None = None) -> Ranking:
        html_content = self._get_ranking_html_content(ranking_at)
        ranking_date = self._get_ranking_date(html_content)
        teams = self._get_teams(html_content)
        return self._format_export(ranking_date, teams)

    def export_to_file(self, template_path: str, ranking_at: date | None = None) -> str:
        ranking = self.export_to_dict(ranking_at)
        path = self.format_output_path(template_path, ranking)
        data = json.dumps(ranking, indent=4, ensure_ascii=False)
        with open(path, "w") as f:
            f.write(data)
        return path


def print_usage():
    print(f"Usage {sys.argv[0]} <output_path> [<ranking_at>]")


if __name__ == "__main__":
    try:
        output_path = sys.argv[1]
    except IndexError:
        print_usage()
        sys.exit(1)

    ranked_at = None
    try:
        ranked_at = parse(sys.argv[2]).date()
    except IndexError:
        pass
    except ValueError:
        print_usage()
        sys.exit(1)

    locale.setlocale(locale.LC_TIME, "en_US.UTF-8")
    exporter = HLTVRanking()
    print(exporter.export_to_file(output_path, ranked_at))
