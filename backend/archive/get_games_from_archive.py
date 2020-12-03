#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import json
import yaml
import requests

from collections import defaultdict

from lxml import html

from dateutil.parser import parse

from utils import read_del_team_names


# loading configuration from external file
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '..', 'config.yml')))

user = CONFIG['del_archive_user']
pwd = CONFIG['del_archive_pass']

SCHEDULE_URL = "/".join((CONFIG['del_archive_base_url'], "spielplan_%d.html"))
MONTHLY_SCHEDULE_URL = "/".join((
    CONFIG['del_archive_base_url'], "spielplan_%d_%02d__.html"))
MONTHS = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]

TEAM_ABBRS_BY_ID = {
    1: 'KEC', 2: 'WOB', 3: 'HHF', 4: 'EBB', 5: 'KEV', 6: 'IEC', 7: 'DEG',
    8: 'MAN', 9: 'NIT', 10: 'ING', 11: 'STR', 12: 'AEV', 13: 'SWW', 14: 'RBM',
    15: 'HAN', 16: 'SBR', 17: 'KAS', 18: 'FRA', 19: 'MUC', 20: 'CAP',
    21: 'RLO', 22: 'MOS', 24: 'WFR', 25: 'ECH', 26: 'ESV', 27: 'EVL',
    28: 'MAD', 29: 'ECR', 30: 'ESG', 31: 'SCR', 32: 'ERD', 33: 'NEU',
    34: 'DUI', 35: 'BHV',
}
TEAM_IDS_BY_ABBR = {abbr: t_id for t_id, abbr in TEAM_ABBRS_BY_ID.items()}

TEAM_LOOKUP = read_del_team_names()


def get_regular_season(season_id):

    games = list()

    for month in MONTHS:
        url = MONTHLY_SCHEDULE_URL % (season_id, month)
        print("\t+ Working on %s" % url)

        r = requests.get(url, auth=(user, pwd))
        doc = html.fromstring(r.text)

        season_info = doc.xpath("//button[@id='btnGroupDrop1']/text()")
        season = int(season_info[0].split()[-1].split("/")[0])
        season_type = season_info[1].strip()

        trs = doc.xpath("//table/tbody/tr")
        for tr in trs:
            single_game = get_single_game(tr, season, season_type)
            if single_game:
                games.append(single_game)

        time.sleep(0.5)

    print("+ %d games collected" % len(games))
    return games


def get_single_game(tr, season, season_type):

    single_game = dict()

    tds = tr.xpath("td")
    try:
        season_id, game_id = [
            int(x) for
            x in tds[7].xpath("a/@href")[0].replace(".html", "").split("_")[1:]
        ]
    except Exception:
        return
    game_date, game_time = [td.xpath("text()").pop(0) for td in tds[:2]]
    game_date = parse(game_date.split()[-1], dayfirst=True).date()
    single_game['game_id'] = game_id
    single_game['season_id'] = season_id
    single_game['season'] = season
    single_game['season_type'] = season_type
    match_day = tds[6].xpath("text()").pop(0).strip()
    if match_day:
        single_game['round'] = int(match_day)
    else:
        single_game['round'] = None
    single_game['game_date'] = str(game_date)
    single_game['game_time'] = game_time.split()[0]
    result = tds[7].xpath("a/text()").pop(0)
    home_score, road_score = [int(score) for score in result.split("-")]
    home_team = tds[3].xpath("a/text()").pop(0)
    home_team_id = int(tds[3].xpath("a/@href").pop(0).split("_")[-1].replace(".html", ""))
    single_game['home_id'] = home_team_id
    single_game['home_team'] = home_team
    single_game['home_abbr'] = TEAM_ABBRS_BY_ID[home_team_id]
    single_game['home_score'] = home_score
    road_team = tds[5].xpath("a/text()").pop(0)
    road_team_id = int(tds[5].xpath("a/@href").pop(0).split("_")[-1].replace(".html", ""))
    single_game['road_id'] = road_team_id
    single_game['road_team'] = road_team
    single_game['road_abbr'] = TEAM_ABBRS_BY_ID[road_team_id]
    single_game['road_score'] = road_score
    overtime_shootout = tds[7].xpath("text()").pop(0).strip()
    single_game['overtime'] = False
    single_game['shootout'] = False
    single_game['armchair'] = False
    if overtime_shootout == '(OT)':
        single_game['overtime'] = True
    elif overtime_shootout == '(SO)':
        single_game['overtime'] = True
        single_game['shootout'] = True
    elif overtime_shootout == '(OR)':
        single_game['armchair'] = True

    return single_game


def get_playoff_games(season_id):

    games = list()

    url = SCHEDULE_URL % season_id
    r = requests.get(url, auth=(user, pwd))
    doc = html.fromstring(r.text)

    print("\t+ Working on %s" % url)

    season_info = doc.xpath("//button[@id='btnGroupDrop1']/text()")
    season = int(season_info[0].split()[-1].split("/")[0])
    season_type = season_info[1].strip()

    rounds = doc.xpath("//h2/text()")

    for i in range(len(rounds)):
        round_divs = doc.xpath(
            "//h2/following-sibling::div[count(preceding-sibling::h2)" +
            "=%d]/div" % (i + 1))
        round_title = doc.xpath(
            "//h2/following-sibling::div[count(preceding-sibling::h2)" +
            "=%d]/preceding-sibling::h2[1]/text()" % (i + 1)).pop(0)
        for round_div in round_divs:
            # round_home, round_road = round_div.xpath("div/div/div/div/a/text()")
            round_home_score, round_road_score = [
                int(token) for token in round_div.xpath("div/div/div/div/span/text()")]
            round_type = max(round_home_score, round_road_score) * 2 - 1
            round_type = "best-of-%d" % round_type
            # round_roster_links = round_div.xpath("div/div/div/div/a/@href")
            # round_home_id, round_road_id = [
            #     int(token.split("_")[-1].replace(".html", "")) for token in round_roster_links]
            round_game_divs = round_div.xpath("div/div/div")[2:]
            game_cnt = 0
            for round_game_div in round_game_divs:
                game_cnt += 1
                single_game = dict()

                season_id, game_id = [
                    int(x) for x in round_game_div.xpath(
                        "div[@class='col-sm-3']/descendant-or-self::a/@href")[0].replace(".html", "").split("_")[1:]
                ]

                single_game['game_id'] = game_id
                single_game['season_id'] = season_id
                single_game['season'] = season
                single_game['season_type'] = season_type
                single_game['round'] = round_title
                single_game['round_type'] = round_type
                game_date = round_game_div.xpath("div[@class='col-sm-4']/text()").pop(0)
                game_date = parse(game_date, dayfirst=True).date()
                single_game['game_no'] = game_cnt
                single_game['game_date'] = str(game_date)
                single_game['game_time'] = None
                game_teams = round_game_div.xpath("div[@class='col-sm-5']/strong/text()").pop(0)
                game_home, game_road = [token.strip() for token in game_teams.split(":")]
                game_result = round_game_div.xpath("div[@class='col-sm-3']/descendant-or-self::*/text()")
                game_result = [r.strip() for r in game_result if r.strip()]
                score_home, score_road = [int(token) for token in game_result[0].split(":")]
                single_game['home_id'] = TEAM_IDS_BY_ABBR[game_home]

                home_team_abbr, home_team_name = TEAM_LOOKUP[(single_game['home_id'], season)]

                single_game['home_team'] = home_team_name
                single_game['home_abbr'] = home_team_abbr
                single_game['home_score'] = score_home
                single_game['road_id'] = TEAM_IDS_BY_ABBR[game_road]

                road_team_abbr, road_team_name = TEAM_LOOKUP[(single_game['road_id'], season)]

                single_game['road_team'] = road_team_name
                single_game['road_abbr'] = road_team_abbr
                single_game['road_score'] = score_road
                single_game['overtime'] = False
                single_game['shootout'] = False
                if len(game_result) == 2:
                    if game_result[-1] == 'OT':
                        single_game['overtime'] = True
                    elif game_result[-1] == 'SO':
                        single_game['overtime'] = True
                        single_game['shootout'] = True
                # print(single_game)
                games.append(single_game)

    print("+ %d games collected" % len(games))
    time.sleep(0.5)
    return games


if __name__ == '__main__':

    games_per_season = defaultdict(list)

    for season_id in range(1, 66):
        url = SCHEDULE_URL % season_id
        r = requests.get(url, auth=(user, pwd))
        doc = html.fromstring(r.text)

        season_info = doc.xpath("//button[@id='btnGroupDrop1']/text()")
        try:
            season = int(season_info[0].split()[-1].split("/")[0])
        except Exception:
            print("+ Unable to retrieve season from page content")
            continue
        season_type = season_info[1].strip()
        print("+ Collecting games for %s %d" % (season_type, season))

        if season_type in ['Hauptrunde', 'Qualifikationsrunde', 'Meisterrunde', 'Abstiegsrunde']:
            games = get_regular_season(season_id)
            games_per_season[season].extend(games)
        else:
            games = get_playoff_games(season_id)
            games_per_season[season].extend(games)

    for season in games_per_season:
        tgt_file = "games_%d.json" % season
        tgt_path = os.path.join(CONFIG['base_data_dir'], 'archive', tgt_file)
        open(tgt_path, 'w').write(json.dumps(games_per_season[season], indent=2))
