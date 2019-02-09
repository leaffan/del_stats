#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

from collections import defaultdict

from utils import get_game_info
from reconstruct_skater_situation import build_interval_tree

GAME_SRC = 'del_games.json'
SHOT_SRC = 'del_shots.json'
PLR_SRC = 'del_players.json'

# GOALIE_TGT = 'del_goalies.json'
GOALIE_GAME_STATS_TGT = 'del_goalie_game_stats.json'
TGT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
PER_GOALIE_TGT_DIR = 'per_goalie'

SKR_SITUATIONS = [
    '5v5', '4v4', '3v3', '5v4', '5v3', '4v3', '4v5', '3v5', '3v4']
SHOT_ZONES = [
    'blue_line', 'left', 'right', 'slot', 'neutral_zone']


def retrieve_goalies_in_game(game):

    interval_tree, _, _ = build_interval_tree(game)

    goalie_seconds = defaultdict(int)

    for interval in interval_tree:
        desc, team, plr_id, _ = interval[-1]
        if desc == 'goalie':
            goalie_seconds[(team, plr_id)] += abs(interval[0] - interval[1])

    return goalie_seconds


def calculate_save_pctg(goalie_dict, type=''):
    if type:
        sa_key = "sa_%s" % type
        ga_key = "ga_%s" % type
        sv_key = ("save_pctg_%s" % type).lower()
    else:
        sa_key = 'shots_against'
        ga_key = 'goals_against'
        sv_key = 'save_pctg'

    if type in ('EV', 'SH', 'PP'):
        shots_against, goals_against = collect_shots_goals_per_situations(
            goalie_dict, type)
    else:
        shots_against = goalie_dict[sa_key]
        goals_against = goalie_dict[ga_key]

    if shots_against:
        goalie_dict[sv_key] = round(
            100 - goals_against / shots_against * 100., 3)
    else:
        goalie_dict[sv_key] = None


def collect_shots_goals_per_situations(goalie_dict, situation='EV'):

    shots_against = 0
    goals_against = 0

    if situation == 'EV':
        skr_situations = ['5v5', '4v4', '3v3']
    elif situation == 'SH':
        skr_situations = ['4v5', '3v5', '3v4']
    elif situation == 'PP':
        skr_situations = ['5v4', '5v3', '4v3']

    for skr_situation in skr_situations:
        shots_against += goalie_dict["sa_%s" % skr_situation]
        goals_against += goalie_dict["ga_%s" % skr_situation]

    return shots_against, goals_against


if __name__ == '__main__':

    if not os.path.isdir(TGT_DIR):
        os.makedirs(TGT_DIR)
    if not os.path.isdir(os.path.join(TGT_DIR, PER_GOALIE_TGT_DIR)):
        os.makedirs(os.path.join(TGT_DIR, PER_GOALIE_TGT_DIR))

    # setting up source and target paths
    src_path = os.path.join(TGT_DIR, GAME_SRC)
    shot_src_path = os.path.join(TGT_DIR, SHOT_SRC)
    plr_src_path = os.path.join(TGT_DIR, PLR_SRC)
    tgt_path = os.path.join(TGT_DIR, GOALIE_GAME_STATS_TGT)
    # plr_tgt_path = os.path.join(TGT_DIR, GOALIE_TGT)

    # loading games and shots
    games = json.loads(open(src_path).read())
    shots = json.loads(open(shot_src_path).read())
    players = json.loads(open(plr_src_path).read())

    goalies_per_game = list()

    for game in games[:]:

        print("+ Retrieving goalie stats for game %s" % get_game_info(game))

        # retrieving goalies dressed from game item
        goalies_dressed = [
            (game['home_abbr'], game['home_g1'][0]),
            (game['home_abbr'], game['home_g2'][0]),
            (game['road_abbr'], game['road_g1'][0]),
            (game['road_abbr'], game['road_g2'][0]),
        ]
        goalies_in_game = retrieve_goalies_in_game(game)

        for goalie_team, goalie_id in goalies_dressed:

            if str(goalie_id) not in players:
                print("=> Goalie with id %d not registered" % goalie_id)
                continue

            goalie_dict = defaultdict(int)

            # retrieving game, team and base goalie information
            goalie_dict['game_id'] = game['game_id']
            goalie_dict['team'] = goalie_team
            goalie_dict['goalie_id'] = goalie_id
            goalie_dict['first_name'] = players[str(goalie_id)]['first_name']
            goalie_dict['last_name'] = players[str(goalie_id)]['last_name']

            print("\t+ Retrieving goalie stats for %s %s (%s)" % (
                goalie_dict['first_name'], goalie_dict['last_name'],
                goalie_team))

            goalie_dict['games_dressed'] += 1
            # checking whether goaltender actually played
            if (goalie_team, goalie_id) in goalies_in_game:
                goalie_dict['games_played'] += 1
            else:
                goalie_dict['games_played'] = 0
            # checking whether goaltender was starting goaltender
            if goalie_id in [game['home_g1'][0], game['road_g1'][0]]:
                goalie_dict['games_started'] += 1
            else:
                goalie_dict['games_started'] = 0
            # # TODO: determine whether to cut processing short right here
            # if not goalie_dict['games_played']:
            #     continue
            goalie_dict['toi'] = goalies_in_game[(goalie_team, goalie_id)]

            # print(goalies_in_game[(goalie_team, goalie_id)])

            for outcome in ['w', 'l', 'otw', 'otl', 'sow', 'sol']:
                goalie_dict[outcome] = 0

            # initializing goalie data dictionary
            goalie_dict['shots_against'] = 0
            goalie_dict['goals_against'] = 0
            for skr_situation in SKR_SITUATIONS:
                goalie_dict["sa_%s" % skr_situation] = 0
            for skr_situation in SKR_SITUATIONS:
                goalie_dict["ga_%s" % skr_situation] = 0
            for shot_zone in SHOT_ZONES:
                goalie_dict["sa_%s" % shot_zone] = 0
            for shot_zone in SHOT_ZONES:
                goalie_dict["ga_%s" % shot_zone] = 0

            for shot in shots:
                # skipping shot if not from current game or not on goal
                if (
                    shot['game_id'] != game['game_id'] or
                    shot['target_type'] != 'on_goal'
                ):
                    continue
                # checking whether shot was on current goalie
                if (
                    shot['team_against'] == goalie_team and
                    shot['goalie'] == goalie_id
                ):
                    # counting shots and goals against
                    goalie_dict['shots_against'] += 1
                    goalie_dict["sa_%s" % shot['plr_situation_against']] += 1
                    goalie_dict["sa_%s" % shot['shot_zone'].lower()] += 1
                    if shot['scored']:
                        goalie_dict['goals_against'] += 1
                        goalie_dict[
                            "ga_%s" % shot['plr_situation_against']] += 1
                        goalie_dict["ga_%s" % shot['shot_zone'].lower()] += 1
            else:
                # calculating save percentages
                for shot_zone in SHOT_ZONES:
                    calculate_save_pctg(goalie_dict, shot_zone)
                for skr_situation in SKR_SITUATIONS:
                    calculate_save_pctg(goalie_dict, skr_situation)
                calculate_save_pctg(goalie_dict, 'EV')
                calculate_save_pctg(goalie_dict, 'SH')
                calculate_save_pctg(goalie_dict, 'PP')
                calculate_save_pctg(goalie_dict)
                # calculating goals against average
                if goalie_dict['goals_against']:
                    goalie_dict['gaa'] = round(
                        goalie_dict['goals_against'] * 3600 /
                        goalie_dict['toi'], 2)

            goalies_per_game.append(goalie_dict)

    # dumping collected and calculated data to target file
    tgt_path = os.path.join(TGT_DIR, GOALIE_GAME_STATS_TGT)
    open(tgt_path, 'w').write(json.dumps(goalies_per_game, indent=2))
