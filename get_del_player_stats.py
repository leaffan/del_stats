#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
from datetime import timedelta, date

import requests
from lxml import html

"""
Retrieves aggregated DEL player statistics directly from official webpage.
"""

BASE_URL = "https://www.del.org/statistik"
TGT_DIR = "data"
TGT_FILE = "%s_del_player_stats.csv" % date.today()

# dictionary to link statistic attributes with column indexes in source table
ATTR_COL_INDEX = {
    'team': 3, 'position': 4, 'shoots': 5, 'games_played': 6, 'goals': 7,
    'assists': 8, 'points': 9, 'plus_minus': 10, 'pim': 15, 'ppg': 18,
    'shots_on_goal': 16, 'sh_pctg': 17, 'shifts_per_game': 12,
    'faceoffs_won': 13, 'faceoffs_lost': 14, 'toi_per_game': 11
}

if __name__ == '__main__':

    r = requests.get(BASE_URL)
    doc = html.fromstring(r.text)

    # retrieving all table rows with player statistics
    trs = doc.xpath(
        "//div[@data-category='player-statistics']/div/table/tbody/tr")

    players = list()

    for tr in trs[:]:
        single_player_dict = dict()

        # retrieving player id
        single_player_dict['id'] = int(
            tr.xpath("td[2]/a/@href").pop().split("/")[-2].split("-")[-1])

        # retrieving player name
        single_player_dict['first_name'] = tr.xpath(
            "td[2]/a/div[@class='pname']/text()").pop().strip()
        single_player_dict['last_name'] = tr.xpath(
            "td[2]/a/div[@class='pname']/span/text()").pop()
        single_player_dict['full_name'] = " ".join((
            single_player_dict['first_name'], single_player_dict['last_name']))

        # retrieving team, position and handedness
        for key in ['team', 'position', 'shoots']:
            td_xpath_expr = "td[%d]/text()" % ATTR_COL_INDEX[key]
            single_player_dict[key] = tr.xpath(td_xpath_expr).pop()

        # skipping goaltenders
        if single_player_dict['position'] == 'GK':
            continue

        # retrieving basic integer stats
        for key in [
                'games_played', 'goals', 'assists', 'points', 'plus_minus',
                'pim', 'ppg', 'shots_on_goal']:
            td_xpath_expr = "td[%d]/text()" % ATTR_COL_INDEX[key]
            single_player_dict[key] = int(tr.xpath(td_xpath_expr).pop())

        # retrieving shooting percentage
        single_player_dict['sh_pctg'] = float(tr.xpath(
            "td[%d]/text()" % ATTR_COL_INDEX['sh_pctg']).
            pop().replace(",", "."))

        # retrieving and calculating faceoff statistics
        for key in ['faceoffs_won', 'faceoffs_lost']:
            td_xpath_expr = "td[%d]/text()" % ATTR_COL_INDEX[key]
            single_player_dict[key] = int(tr.xpath(td_xpath_expr).pop())
        # summarizing faceoffs taken
        single_player_dict['faceoffs'] = (
            single_player_dict['faceoffs_won'] +
            single_player_dict['faceoffs_lost']
        )
        # calculating faceoff percentage
        if single_player_dict['faceoffs']:
            single_player_dict['faceoff_pctg'] = (
                single_player_dict['faceoffs_won'] /
                single_player_dict['faceoffs'] * 100.
            )
        else:
            single_player_dict['faceoff_pctg'] = 0.0

        # retrieving shifts and time one ice per game
        single_player_dict['shifts_per_game'] = int(tr.xpath(
            "td[%d]/text()" % ATTR_COL_INDEX['shifts_per_game']).pop())
        toi_p_game_str = tr.xpath(
            "td[%d]/text()" % ATTR_COL_INDEX['toi_per_game']).pop()
        min_p_game, sec_p_game = [int(x) for x in toi_p_game_str.split(":")]
        single_player_dict['toi_p_game'] = timedelta(
            seconds=(min_p_game * 60 + sec_p_game))

        # calculating overall time on ice
        single_player_dict['toi_overall'] = (
            single_player_dict['games_played'] *
            single_player_dict['toi_p_game']
        )
        single_player_dict['min_overall'] = (
            single_player_dict['toi_overall'].total_seconds() / 60.
        )

        # calculating points per 60
        single_player_dict['pts_per_60'] = (
            single_player_dict['points'] /
            single_player_dict['min_overall'] * 60
        )

        players.append(single_player_dict)

    if players:
        keys = players[0].keys()

        tgt_path = os.path.join(TGT_DIR, TGT_FILE)

        with open(tgt_path, 'w', encoding='utf-8') as output_file:
            output_file.write('\ufeff')
            dict_writer = csv.DictWriter(
                output_file, keys, delimiter=';', lineterminator='\n')
            dict_writer.writeheader()
            dict_writer.writerows(players)
