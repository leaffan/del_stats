#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import time

from datetime import datetime
from collections import defaultdict

import requests
from lxml import html

# loading configuration from external file
CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'config.yml')))

SCORER_URL = "/".join((CONFIG['del_archive_base_url'], "topscorer_%d.html"))
TGT_DIR = os.path.join(CONFIG['base_data_dir'], 'archive', 'player_games2')
CURRENT_PLRS_SRC = os.path.join(CONFIG['tgt_processing_dir'], 'del_players.json')

if not os.path.isdir(TGT_DIR):
    os.makedirs(TGT_DIR)


def load_current_players():
    """
    Loads current players (i.e. from currently used organization scheme) into a dictionary using either dates of birth
    or full names (if date of birth is not available). This dictionary serves as a registry to map archive players IDs
    to currently used ones.
    """
    current_plrs_registry = defaultdict(list)

    # loading current players from corresponding file
    current_plrs = json.loads(open(CURRENT_PLRS_SRC).read())

    for current_plr_id in current_plrs:
        current_plr = current_plrs[current_plr_id]
        # setting up tuple containing most basic information about current player
        current_plr_info = (current_plr['first_name'], current_plr['last_name'], int(current_plr_id))

        # trying to retrieve date of birth for current player
        dob = current_plr.get('dob')
        # using date of birth as key in registry (if available)
        if dob and int(current_plr_id) != 1015:
            current_plrs_registry[dob].append(current_plr_info)
        # otherwise using full name as key
        else:
            full_name = " ".join((current_plr['first_name'], current_plr['last_name']))
            current_plrs_registry[full_name].append(current_plr_info)

    return current_plrs_registry


if __name__ == '__main__':

    user = CONFIG['del_archive_user']
    pwd = CONFIG['del_archive_pass']

    current_plrs_registry = load_current_players()

    processed_plrs = [int(x.replace(".json", "")) for x in os.listdir(TGT_DIR) if x.endswith(".json")]

    plr_ids_done = set(processed_plrs)

    for season_id in range(65, 64, -1):
        url = SCORER_URL % season_id
        print("+ Retrieving top scorer list from %s" % url)
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

        # retrieving table rows containing scorer information
        plr_trs = doc.xpath("//h2/following-sibling::table/tbody/tr")
        # plrs = doc.xpath("//h2/following-sibling::table/tbody/tr/td[2]/a/text()")[:]
        # plr_links = doc.xpath("//h2/following-sibling::table/tbody/tr/td[2]/a/@href")[:]

        for plr_tr in plr_trs[:20]:
            # retrieving player name, link to player page and position (if available)
            plr = plr_tr.xpath("td[2]/a/text()").pop(0)
            plr_link = plr_tr.xpath("td[2]/a/@href").pop(0)
            raw_plr_position = plr_tr.xpath("td[7]/text()")
            if raw_plr_position:
                plr_position = raw_plr_position.pop(0)
            else:
                plr_position = ''

            # retrieving player id from link to player page
            plr_id = int(plr_link.replace(".html", "").split("_")[-1])
            # if plr_position != 'G' and plr_id in plr_ids_done:
            #     print("+ Player %s [%d] already processed" % (plr, plr_id))
            #     continue
            print("+ Retrieving player games for %s [%d]" % (plr, plr_id))

            # setting up container to hold player information
            single_plr = dict()
            single_plr['archive_id'] = plr_id
            single_plr['full_name'] = plr
            single_plr['last_position'] = plr_position

            # retrieving content of player page
            portrait_url = "/".join((CONFIG['del_archive_base_url'], plr_link))
            r = requests.get(portrait_url, auth=(user, pwd))
            portrait_doc = html.fromstring(r.text)
            # identifying player's position
            position = portrait_doc.xpath("//td[text() = 'Position:']/following-sibling::td/text()").pop()
            raw_dob = portrait_doc.xpath("//td[text() = 'Geburtsdatum:']/following-sibling::td/text()")
            if raw_dob:
                dob = raw_dob.pop(0).split("-")[0].strip()
                dob = str(datetime.strptime(dob, '%d.%m.%Y').date())
                single_plr['dob'] = dob

            if dob in current_plrs_registry:
                for first_name, last_name, current_plr_id in current_plrs_registry[dob]:
                    if plr == " ".join((first_name, last_name)):
                        # print("Player '%s' [%d] from archive found among current players via date of birth: %s [%d]" % (
                        #     plr, plr_id, " ".join((first_name, last_name)), current_plr_id))
                        single_plr['current_id'] = current_plr_id
            elif plr in current_plrs_registry:
                for first_name, last_name, current_plr_id in current_plrs_registry[plr]:
                    if plr == " ".join((first_name, last_name)):
                        # print("Player '%s' [%d] from archive found among current players via full name: %s [%d]" % (
                        #     plr, plr_id, " ".join((first_name, last_name)), current_plr_id))
                        single_plr['current_id'] = current_plr_id
            else:
                print("Player '%s' [%d] from archive not found among current players" % (plr, plr_id))

            # continue

            # if position == 'G':
            #     plr_ids_done.add(plr_id)
            #     if plr_id != 2115:
            #         continue

            # if position == 'G':
            #     raw_game_log_head = portrait_doc.xpath("//div[@class='box_head']/h3[contains(text(), 'Spielü')]/text()")
            #     if raw_game_log_head:
            #         seasons = [raw_game_log_head[0].split(" - ", maxsplit=1)[-1]]
            #         season_links = [portrait_url]
            #         print(seasons)
            #         print(season_links)
            #     else:
            #         seasons = list()
            #         season_links = list()
            # else:
            #     seasons = portrait_doc.xpath("//table[@class='table mt-2'][1]/tbody/tr/td[1]/a/text()")[::-1]
            #     season_links = portrait_doc.xpath("//table[@class='table mt-2'][1]/tbody/tr/td[1]/a/@href")[::-1]

            tgt_path = os.path.join(TGT_DIR, "%d.json" % plr_id)

            # if os.path.isfile(tgt_path):
            #     player_games = json.loads(open(tgt_path).read())
            # else:
            #     player_games = list()

            # for season, season_link in zip(seasons, season_links):
            #     season_url = "/".join((CONFIG['del_archive_base_url'], season_link))
            #     print(season_url)
            #     print("\t+ %s" % season)
            #     if position != 'G':
            #         r = requests.get(season_url, auth=(user, pwd))
            #         season_doc = html.fromstring(r.text)
            #     else:
            #         season_doc = portrait_doc
            #     season_info = season_doc.xpath("//button[@id='btnGroupDrop1']/text()")
            #     try:
            #         season = int(season_info[0].split()[-1].split("/")[0])
            #     except Exception:
            #         print("+ Unable to retrieve season from page content")
            #         continue
            #     season_type = season_info[1].strip()

            #     games_in_season_trs = season_doc.xpath("//table[@class='table mt-2'][2]/tbody/tr")

            #     print(season_info, season, season_type)
            #     print(games_in_season_trs)

            #     for tr in games_in_season_trs:
            #         tds = tr.xpath("td/descendant-or-self::*/text()")
            #         single_season_player_game = dict()

            #         single_season_player_game['player_id'] = plr_id
            #         single_season_player_game['player_name'] = plr
            #         single_season_player_game['season'] = season
            #         single_season_player_game['season_type'] = season_type
            #         single_season_player_game['round'] = tds[0].strip()
            #         single_season_player_game['game_date'] = tds[1]
            #         single_season_player_game['opp_team'] = tds[2]

            #         result = tds[3]
            #         ot_game = False
            #         so_game = False
            #         nc_game = False
            #         if "(" in result:
            #             result, game_end_type = result.replace(")", "").split("(")
            #             if game_end_type == 'OT':
            #                 ot_game = True
            #             elif game_end_type == 'SO':
            #                 so_game = True
            #             elif game_end_type == 'OR':
            #                 nc_game = True
            #             else:
            #                 print("Unknown game end type %s" % game_end_type)
            #         single_season_player_game['result'] = result
            #         single_season_player_game['overtime_game'] = ot_game
            #         single_season_player_game['shootout_game'] = so_game
            #         single_season_player_game['no_contest_game'] = nc_game

            #         if position != 'G':
            #             single_season_player_game['goals'] = int(tds[4])
            #             single_season_player_game['assists'] = int(tds[5])
            #             single_season_player_game['points'] = int(tds[6])
            #             single_season_player_game['plus_minus'] = int(tds[7])

            #             toi = tds[8]
            #             mins, secs = [int(x) for x in toi.split(":")]
            #             single_season_player_game['toi'] = mins * 60 + secs

            #             single_season_player_game['pim'] = int(tds[9])
            #             single_season_player_game['ppg'] = int(tds[10])
            #             single_season_player_game['shg'] = int(tds[11])
            #             single_season_player_game['sog'] = int(tds[12])
            #             single_season_player_game['sh%'] = float(tds[13].replace("%", "").replace(",", "."))
            #         else:
            #             toi = tds[4]
            #             mins, secs = [int(x) for x in toi.split(":")]
            #             single_season_player_game['toi'] = mins * 60 + secs
            #             single_season_player_game['ga'] = int(tds[5])
            #             single_season_player_game['sv'] = int(tds[6])
            #             single_season_player_game['sa'] = (
            #                 single_season_player_game['ga'] + single_season_player_game['sv'])

            #         player_games.append(single_season_player_game)

            time.sleep(0.2)

            # open(tgt_path, 'w').write(json.dumps(player_games, indent=2))
            open(tgt_path, 'w').write(json.dumps(single_plr, indent=2, default=str))
            # if position != 'G':
            #     plr_ids_done.add(plr_id)
