#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import time

import requests
from lxml import html

# loading configuration from external file
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

user = CONFIG['del_archive_user']
pwd = CONFIG['del_archive_pass']

SCORER_URL = "/".join((CONFIG['del_archive_base_url'], "topscorer_%d.html"))

TGT_DIR = os.path.join(CONFIG['base_data_dir'], 'archive', 'player_games')

if not os.path.isdir(TGT_DIR):
    os.makedirs(TGT_DIR)

if __name__ == '__main__':

    processed_plrs = [
        int(x.replace(".json", "")) for
        x in os.listdir(TGT_DIR) if x.endswith(".json")]

    plr_ids_done = set(processed_plrs)

    for season_id in range(34, 70):
        url = SCORER_URL % season_id
        r = requests.get(url, auth=(user, pwd))
        doc = html.fromstring(r.text)

        season_info = doc.xpath("//button[@id='btnGroupDrop1']/text()")
        try:
            season = int(season_info[0].split()[-1].split("/")[0])
        except Exception:
            print("+ Unable to retrieve season from page content")
            continue
        season_type = season_info[1].strip()
        print("+ Collecting scorer stats for %s %d" % (season_type, season))

        plrs = doc.xpath(
            "//h2/following-sibling::table/tbody/tr/td[2]/a/text()")[:]
        plr_links = doc.xpath(
            "//h2/following-sibling::table/tbody/tr/td[2]/a/@href")[:]

        for plr, plr_link in zip(plrs, plr_links):
            plr_id = int(plr_link.replace(".html", "").split("_")[-1])
            if plr_id in plr_ids_done:
                print("+ Player %s [%d] already processed" % (plr, plr_id))
                continue
            print("+ Retrieving player games for %s [%d]" % (plr, plr_id))
            portrait_url = "/".join((CONFIG['del_archive_base_url'], plr_link))

            r = requests.get(portrait_url, auth=(user, pwd))
            portrait_doc = html.fromstring(r.text)

            position = portrait_doc.xpath(
                "//td[text() = 'Position:']/following-sibling::td/text()"
            ).pop()

            if position == 'G':
                plr_ids_done.add(plr_id)
                continue

            seasons = portrait_doc.xpath(
                "//table[@class='table mt-2'][1]/tbody/tr/td[1]/a/text()"
            )[::-1]
            season_links = portrait_doc.xpath(
                "//table[@class='table mt-2'][1]/tbody/tr/td[1]/a/@href"
            )[::-1]

            player_games = list()

            tgt_path = os.path.join(TGT_DIR, "%d.json" % plr_id)

            for season, season_link in zip(seasons, season_links):
                season_url = "/".join(
                    (CONFIG['del_archive_base_url'], season_link))
                print("\t+ %s" % season)
                r = requests.get(season_url, auth=(user, pwd))
                season_doc = html.fromstring(r.text)
                season_info = season_doc.xpath(
                    "//button[@id='btnGroupDrop1']/text()")
                try:
                    season = int(season_info[0].split()[-1].split("/")[0])
                except Exception:
                    print("+ Unable to retrieve season from page content")
                    continue
                season_type = season_info[1].strip()

                games_in_season_trs = season_doc.xpath(
                    "//table[@class='table mt-2'][2]/tbody/tr")

                for tr in games_in_season_trs:
                    tds = tr.xpath("td/descendant-or-self::*/text()")
                    single_season_player_game = dict()

                    single_season_player_game['player_id'] = plr_id
                    single_season_player_game['player_name'] = plr
                    single_season_player_game['season'] = season
                    single_season_player_game['season_type'] = season_type
                    single_season_player_game['round'] = tds[0].strip()
                    single_season_player_game['game_date'] = tds[1]
                    single_season_player_game['opp_team'] = tds[2]

                    result = tds[3]
                    ot_game = False
                    so_game = False
                    nc_game = False
                    if "(" in result:
                        result, game_end_type = result.replace(
                            ")", "").split("(")
                        if game_end_type == 'OT':
                            ot_game = True
                        elif game_end_type == 'SO':
                            so_game = True
                        elif game_end_type == 'OR':
                            nc_game = True
                        else:
                            print("Unknown game end type %s" % game_end_type)
                    single_season_player_game['result'] = result
                    single_season_player_game['overtime_game'] = ot_game
                    single_season_player_game['shootout_game'] = so_game
                    single_season_player_game['no_contest_game'] = nc_game
                    single_season_player_game['goals'] = int(tds[4])
                    single_season_player_game['assists'] = int(tds[5])
                    single_season_player_game['points'] = int(tds[6])
                    single_season_player_game['plus_minus'] = int(tds[7])

                    toi = tds[8]
                    mins, secs = [int(x) for x in toi.split(":")]
                    single_season_player_game['toi'] = mins * 60 + secs

                    single_season_player_game['pim'] = int(tds[9])
                    single_season_player_game['ppg'] = int(tds[10])
                    single_season_player_game['shg'] = int(tds[11])
                    single_season_player_game['sog'] = int(tds[12])
                    single_season_player_game['sh%'] = float(
                        tds[13].replace("%", "").replace(",", "."))

                    player_games.append(single_season_player_game)

                time.sleep(0.1)

            open(tgt_path, 'w').write(json.dumps(player_games, indent=2))
            plr_ids_done.add(plr_id)
