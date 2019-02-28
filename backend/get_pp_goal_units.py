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

pp_goals_by_team = dict()
pp_goals_by_team_forwards = dict()


def sort_player_list(data_dict, all_players):
    """
    Sorts player tuples in specified data dictionary using last names retrieved
    from provided dictionary of all players.
    """
    output = list()
    for team in data_dict:
        for key in data_dict[team]:
            # sorting players on ice by last name
            plrs_on_ice = sorted(
                [all_players[str(plr_id)]['last_name'] for plr_id in key])
            # putting players osn ice in comma-separated list
            plrs_on_ice = ", ".join(plrs_on_ice)
            # adding team, players on ice and number of goals scored to output
            output.append(
                "%s;%s;%d" % (team, plrs_on_ice, data_dict[team][key]))

    return output


if __name__ == '__main__':

    # setting up source and target paths
    src_path = os.path.join(TGT_DIR, GAME_SRC)
    plr_src_path = os.path.join(TGT_DIR, PLR_SRC)

    # loading games and shots
    games = json.loads(open(src_path).read())
    players = json.loads(open(plr_src_path).read())

    for game in games[:]:
        print(
            "Retrieving successful power play units " +
            "in game %s" % get_game_info(game))
        events_path = EVENTS_SUFFIX % game['game_id']
        events_url = "%s/%s" % (BASE_URL, events_path)

        r = requests.get(events_url)
        events_data = r.json()

        for period in events_data:
            for event in events_data[period]:
                if event['type'] == 'goal':
                    # skipping non power-play goals
                    if not event['data']['balance'].startswith('PP'):
                        continue
                    # retrieving scoring team
                    home_road = event['data']['team']
                    if home_road == 'home':
                        team = game['home_abbr']
                    else:
                        team = game['road_abbr']

                    # if necessary creating new goal counter for current team
                    if team not in pp_goals_by_team:
                        pp_goals_by_team[team] = defaultdict(int)
                        pp_goals_by_team_forwards[team] = defaultdict(int)

                    players_on_ice = list()
                    forwards_on_ice = list()

                    for plr in event['data']['attendants']['positive']:
                        plr_id = plr['playerId']
                        plr_pos = players[str(plr_id)]['position']
                        # skipping goaltenders
                        if plr_pos == 'GK':
                            continue
                        # singling out forwards
                        if plr_pos == 'FO':
                            forwards_on_ice.append(plr_id)
                        # adding player id to list of all player ids on ice for
                        # this goal
                        players_on_ice.append(plr_id)

                    # sorting collected player ids
                    players_on_ice = sorted(players_on_ice)
                    forwards_on_ice = sorted(forwards_on_ice)

                    # incrementing goal counter for current combination of
                    # players and forwards
                    pp_goals_by_team[team][tuple(players_on_ice)] += 1
                    pp_goals_by_team_forwards[
                        team][tuple(forwards_on_ice)] += 1

    # finally preparing output by sorting players by last name
    players_on_ice_output = sort_player_list(pp_goals_by_team, players)
    forwards_on_ice_output = sort_player_list(
        pp_goals_by_team_forwards, players)

    # dumping results to csv files
    open("data/players_on_ice.csv", 'w', encoding='utf-8').write(
        "\n".join(players_on_ice_output))
    open("data/forwards_on_ice.csv", 'w', encoding='utf-8').write(
        "\n".join(forwards_on_ice_output))
