#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import argparse
import intervaltree
from collections import defaultdict

import requests
from shapely.geometry import Point

import rink_dimensions as rd
from utils import get_game_info


BASE_URL = 'https://www.del.org/live-ticker'
SHOTS_SUFFIX = "visualization/shots/%d.json"
EVENTS_SUFFIX = "matches/%d/period-events.json"
GAME_SRC = 'del_games.json'
SHOTS_DATA_TGT = 'del_shots.json'
TGT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

SHOT_RESULTS = {
    1: 'on_goal', 2: 'missed', 3: 'blocked', 4: 'on_goal'
}


def build_interval_tree(game):
    """
    Builds an interval tree holding information about goaltender shifts and
    penalties. Later used to determine which goaltender had to save a certain
    shot or what kind of player situation existed at the time of a shot.
    """
    # retrieving raw events data
    events_path = EVENTS_SUFFIX % game['game_id']
    events_url = "%s/%s" % (BASE_URL, events_path)
    r = requests.get(events_url)
    events_data = r.json()

    goalie_changes = defaultdict(list)
    goalie_in_net = {'home': 0, 'road': 0}
    goalie_for_team = {'home': None, 'road': None}

    max_game_time = 0

    # TODO: tidy up the following mess
    for period in events_data:
        for event in events_data[period]:
            event_type = event['type']
            if event_type == 'periodEnd':
                max_game_time = event['time']
            if event_type == 'goalkeeperChange':
                event_data = event['data']
                if event_data['team'] == 'home':
                    event_team = game['home_abbr']
                    home_road = 'home'
                else:
                    event_team = game['road_abbr']
                    home_road = 'road'
                event_time = event_data['time']
                if event_data['outgoingGoalkeeper']:
                    change_type = 'goalie_out'
                    event_player_id = event_data[
                        'outgoingGoalkeeper']['playerId']
                    goalie_changes[home_road].append((
                        event_time, event_team, change_type, event_player_id))
                    goalie_in_net[home_road] -= 1
                    if goalie_for_team[home_road] == event_player_id:
                        goalie_for_team[home_road] = None
                if event_data['player']:
                    change_type = 'goalie_in'
                    event_player_id = event_data['player']['playerId']
                    goalie_changes[home_road].append((
                        event_time, event_team, change_type, event_player_id))
                    goalie_in_net[home_road] += 1
                    goalie_for_team[home_road] = event_player_id

    # finally adding outgoing goalkeepers at the end (e.g. maximum time) of
    # the game
    for key in goalie_in_net:
        if goalie_in_net[key] != 0:
            goalie_changes[key].append((
                max_game_time, game["%s_abbr" % key],
                'goalie_out', goalie_for_team[key]))

    # setting up interval tree
    it = intervaltree.IntervalTree()

    for home_road in goalie_changes:
        for i in range(0, len(goalie_changes[home_road]) - 1, 2):
            goalie_in_time, goalie_in_team, _, goalie_in_id = (
                goalie_changes[home_road][i])
            goalie_out_time, _, _, _ = (
                goalie_changes[home_road][i + 1])
            it.addi(
                goalie_in_time, goalie_out_time,
                ('goalie', goalie_in_team, goalie_in_id))

    return it


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Download DEL shots.')
    parser.add_argument(
        '--initial', dest='initial', required=False,
        action='store_true', help='Re-create list of shots')
    parser.add_argument(
        '--limit', dest='limit', required=False, type=int, default=0,
        help='Number of maximum games to be processed')

    args = parser.parse_args()

    initial = args.initial
    limit = int(args.limit)

    # setting up source and target paths
    src_path = os.path.join(TGT_DIR, GAME_SRC)
    tgt_path = os.path.join(TGT_DIR, SHOTS_DATA_TGT)

    # loading games
    games = json.loads(open(src_path).read())

    # loading existing shots
    if not initial and os.path.isfile(tgt_path):
        all_shots = json.loads(open(tgt_path).read())
    # or preparing empty container for all shots
    else:
        all_shots = list()

    # retrieving set of games we already have retrieved player stats for
    registered_games = set([shot['game_id'] for shot in all_shots])

    cnt = 0
    for game in games[:]:
        cnt += 1

        # building interval tree to query goaltenders and player situations
        it = build_interval_tree(game)

        # skipping already processed games
        if game['game_id'] in registered_games:
            continue
        print("+ Retrieving shots for game %s " % get_game_info(game))

        # retrieving raw shot data
        shots_path = SHOTS_SUFFIX % game['game_id']
        shots_url = "%s/%s" % (BASE_URL, shots_path)
        r = requests.get(shots_url)
        match_data = r.json()

        for shot in match_data['match']['shots'][:]:
            # converting arbitrary coordinates to actual coordinates in meters
            x = rd.X_TO_M * shot['coordinate_x']
            y = rd.Y_TO_M * shot['coordinate_y']

            # constructing shot location
            shot_pnt = Point(x, y)
            # calculating shot distance
            if shot['team_id'] == game['road_id']:
                shot['team'] = game['road_abbr']
                shot['team_against'] = game['home_abbr']
                dst = rd.HOME_GOAL.distance(shot_pnt)
            elif shot['team_id'] == game['home_id']:
                shot['team'] = game['home_abbr']
                shot['team_against'] = game['road_abbr']
                dst = rd.ROAD_GOAL.distance(shot_pnt)
            # determining target and outcome of shot
            shot['target_type'] = SHOT_RESULTS[shot['match_shot_resutl_id']]
            if shot['match_shot_resutl_id'] == 4:
                shot['scored'] = True
            else:
                shot['scored'] = False
            del(shot['match_shot_resutl_id'])
            if 'real_date' in shot:
                del(shot['real_date'])

            # determining shot zone
            for poly_name, poly in rd.polygons:
                if poly.intersects(shot_pnt):
                    shot['shot_zone'] = poly_name[5:]
                    break

            # adding new values to shot item
            shot['distance'] = round(dst, 2)
            shot['x'] = round(x, 2)
            shot['y'] = round(y, 2)
            shot['game_id'] = game['game_id']
            shot['schedule_game_id'] = game['schedule_game_id']

            # retrieving goalie involved in the current shot
            shot['goalie_id'] = None
            available_intervals = it[shot['time']]
            for int_start, int_end, int_data in available_intervals:
                int_type, int_team, int_plr_id = int_data
                if int_type == 'goalie' and int_team != shot['team']:
                    shot['goalie_id'] = int_plr_id

            all_shots.append(shot)

        if limit and cnt >= limit:
            break

    open(tgt_path, 'w').write(json.dumps(all_shots, indent=2, default=str))
