#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import argparse

from shapely.geometry import Point

import rink_dimensions as rd
from utils import get_game_info, get_game_type_from_season_type
from reconstruct_skater_situation import reconstruct_skater_situation

# loading external configuration
CONFIG = yaml.load(open('config.yml'))

TGT_DIR = os.path.join(
    CONFIG['tgt_processing_dir'], str(CONFIG['default_season']))
GAME_SRC = 'del_games.json'
SHOTS_DATA_TGT = 'del_shots.json'

SHOT_RESULTS = {
    1: 'on_goal', 2: 'missed', 3: 'blocked', 4: 'on_goal'
}


def correct_time_of_shot(shot, goal_times):
    """
    Corrects time of shot (a goal was scored on) by comparing its original time
    with a list of actual times of goals scored in the game and finding the
    goal incident with the minimum time difference. Optionally correcting the
    time of the shot when a non-zero minimum difference was found.
    """
    # initiating minimum difference and minimum difference index
    min_diff = min_diff_idx = 10000

    for goal_time in goal_times:
        # calculating time difference between current shot and goal time
        diff = abs(goal_time - shot['time'])
        # updating minimum difference and minimum difference index
        if diff < min_diff:
            min_diff = diff
            min_diff_idx = goal_times.index(goal_time)

    # correcting current shot's time if a difference to the time a goal scored
    # was found
    if min_diff:
        shot['time'] = goal_times[min_diff_idx]

    return shot


def set_period(shot):
    """
    Sets period of a shot in accordance of its actual time.
    """
    if shot['time'] <= 1200:
        shot['period'] = 1
    elif shot['time'] <= 2400:
        shot['period'] = 2
    elif shot['time'] <= 3600:
        shot['period'] = 3
    else:
        shot['period'] = 'OT'

    return shot


def delete_shot_properties(shot):
    """
    Delete no longer necessary properties from shot item.
    """
    for key in ['match_shot_resutl_id', 'real_date', 'id']:
        if key in shot:
            del(shot[key])

    return shot


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Process DEL shots.')
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

        # skipping already processed games
        if game['game_id'] in registered_games:
            continue
        print("+ Retrieving shots for game %s " % get_game_info(game))

        # collecting skater situation for each second of the game and a list
        # of times when goals has been scored
        times, goal_times = reconstruct_skater_situation(game)
        game_type = get_game_type_from_season_type(game)

        # # retrieving raw shot data
        shots_src_path = os.path.join(
            CONFIG['base_data_dir'], 'shots',
            str(game['season']), str(game_type), "%d.json" % game['game_id'])
        match_data = json.loads(open(shots_src_path).read())

        for shot in match_data['match']['shots'][:]:

            shot['game_id'] = game['game_id']
            # TODO: activate when schedule game id is available again
            # shot['schedule_game_id'] = game['schedule_game_id']
            shot['season_type'] = game['season_type']

            # converting arbitrary coordinates to actual coordinates in meters
            x = rd.X_TO_M * shot['coordinate_x']
            y = rd.Y_TO_M * shot['coordinate_y']
            shot['x'] = round(x, 2)
            shot['y'] = round(y, 2)
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
            shot['distance'] = round(dst, 2)
            # determining shot zone
            for poly_name, poly in rd.polygons:
                if poly.intersects(shot_pnt):
                    shot['shot_zone'] = poly_name[5:]
                    break
            # determining target and outcome of shot
            shot['target_type'] = SHOT_RESULTS[shot['match_shot_resutl_id']]
            if shot['match_shot_resutl_id'] == 4:
                shot['scored'] = True
            else:
                shot['scored'] = False
            # optionally correcting time of shot using list of times a goals
            # was scored
            if shot['scored']:
                shot = correct_time_of_shot(shot, goal_times)

            # setting shot period and retrieving player situations at time of
            # the shot
            shot = set_period(shot)

            # retrieving skater situation at time of shot
            if not shot['time']:
                print(
                    "Shot at zero time encountered in " +
                    "game %s" % get_game_info(game))
            else:
                try:
                    skr_situation = times[shot['time']]
                except KeyError:
                    if shot['time'] > max(times.keys()):
                        print(
                            "+ Shot at %d after the actual " % shot['time'] +
                            "end of game (%d) registered" % max(times.keys()))
                        shot['time'] = max(times.keys())

                shot['plr_situation'] = "%dv%d" % (
                    skr_situation[shot['team']],
                    skr_situation[shot['team_against']])
                shot['plr_situation_against'] = "%dv%d" % (
                    skr_situation[shot['team_against']],
                    skr_situation[shot['team']])

                # retrieving goalie facing the shot
                if game['home_abbr'] == shot['team_against']:
                    shot['goalie'] = times[shot['time']]['home_goalie']
                else:
                    shot['goalie'] = times[shot['time']]['road_goalie']

                # deleting unnecessary shot properties
                shot = delete_shot_properties(shot)

                all_shots.append(shot)

        if limit and cnt >= limit:
            break

    open(tgt_path, 'w').write(json.dumps(all_shots, indent=2, default=str))
