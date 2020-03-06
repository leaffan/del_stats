#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from collections import defaultdict

import requests

from utils import get_game_info

GAME_SRC = 'del_games.json'
PLR_SRC = 'del_players.json'

BASE_URL = 'https://www.del.org/live-ticker'
EVENTS_SUFFIX = "matches/%d/period-events.json"

TGT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

pk_forwards_gf_by_team = dict()
pk_forwards_ga_by_team = dict()

if __name__ == '__main__':
    # setting up source and target paths
    src_path = os.path.join(TGT_DIR, GAME_SRC)
    plr_src_path = os.path.join(TGT_DIR, PLR_SRC)

    # loading games and shots
    games = json.loads(open(src_path).read())
    players = json.loads(open(plr_src_path).read())

    for game in games[:]:
        print(
            "Retrieving penalty killing units " +
            "in game %s" % get_game_info(game))
        events_path = EVENTS_SUFFIX % game['game_id']
        events_url = "%s/%s" % (BASE_URL, events_path)

        r = requests.get(events_url)
        events_data = r.json()

        for period in events_data:
            for event in events_data[period]:
                if event['type'] == 'goal':
                    balance = event['data']['balance']
                    # skipping even strength, penalty shot and shootout goals
                    if balance[:2] not in ('PP', 'SH'):
                        continue
                    # retrieving teams
                    home_road = event['data']['team']
                    if home_road == 'home':
                        gf_team = game['home_abbr']
                        ga_team = game['road_abbr']
                    else:
                        gf_team = game['road_abbr']
                        ga_team = game['home_abbr']

                    # if necessary creating new goal counters for current teams
                    if gf_team not in pk_forwards_gf_by_team:
                        pk_forwards_gf_by_team[gf_team] = defaultdict(int)
                    if gf_team not in pk_forwards_ga_by_team:
                        pk_forwards_ga_by_team[gf_team] = defaultdict(int)
                    if ga_team not in pk_forwards_ga_by_team:
                        pk_forwards_ga_by_team[ga_team] = defaultdict(int)
                    if ga_team not in pk_forwards_gf_by_team:
                        pk_forwards_gf_by_team[ga_team] = defaultdict(int)

                    gf_on_ice = list()
                    ga_on_ice = list()

                    if balance.startswith('SH'):
                        for plr in event['data']['attendants']['positive']:
                            plr_id = plr['playerId']
                            plr_pos = players[str(plr_id)]['position']
                            # skipping goaltenders
                            if plr_pos == 'GK':
                                continue
                            # adding forwards to list of players forcing a
                            # shorthanded goal
                            if plr_pos == 'FO':
                                gf_on_ice.append(plr_id)

                    if balance.startswith('PP'):
                        for plr in event['data']['attendants']['negative']:
                            plr_id = plr['playerId']
                            plr_pos = players[str(plr_id)]['position']
                            # skipping goaltenders
                            if plr_pos == 'GK':
                                continue
                            # adding forwards to list of players allowing a
                            # powerplay goal
                            if plr_pos == 'FO':
                                ga_on_ice.append(plr_id)

                    # sorting collected player ids
                    gf_on_ice = sorted(gf_on_ice)
                    ga_on_ice = sorted(ga_on_ice)

                    if gf_on_ice:
                        pk_forwards_gf_by_team[gf_team][tuple(gf_on_ice)] += 1
                        pk_forwards_ga_by_team[gf_team][tuple(gf_on_ice)] += 0
                    if ga_on_ice:
                        pk_forwards_ga_by_team[ga_team][tuple(ga_on_ice)] += 1
                        pk_forwards_gf_by_team[ga_team][tuple(ga_on_ice)] += 0

    output = list()

    for team in pk_forwards_ga_by_team:
        for key in pk_forwards_ga_by_team[team]:
            plrs_on_ice = sorted(
                [players[str(plr_id)]['last_name'] for plr_id in key])
            plrs_on_ice = ", ".join(plrs_on_ice)
            output.append(";".join((
                team, plrs_on_ice,
                "+%d" % pk_forwards_gf_by_team[team][key],
                "-%d" % pk_forwards_ga_by_team[team][key])))

    # dumping results to csv file
    open("data/pkers_on_ice.csv", 'w', encoding='utf-8').write(
        "\n".join(output))
