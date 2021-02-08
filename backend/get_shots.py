#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import json
import yaml
import argparse
from collections import defaultdict

from shapely.geometry import Point
from intervaltree import IntervalTree

import rink_dimensions as rd
from utils import get_game_info, get_game_type_from_season_type
from reconstruct_skater_situation import reconstruct_skater_situation

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

GAME_SRC = 'del_games.json'
SHOTS_DATA_TGT = 'del_shots.json'
PP_SITS_DATA_TGT = 'del_pp_sits_goals.json'

ALL_PLAYERS = os.path.join(CONFIG['tgt_processing_dir'], 'del_players.json')

SHOT_RESULTS = {
    1: 'on_goal', 2: 'missed', 3: 'blocked', 4: 'on_goal', 5: 'post',
}


def correct_time_of_shot(shot, goal_times):
    """
    Corrects time of shot (a goal was scored on) by comparing its original time
    with a list of actual times of goals scored in the game and finding the
    goal incident with the minimum time difference. Optionally correcting the
    time of the shot when a non-zero minimum difference was found.
    """
    # initiating minimum difference and minimum difference index
    min_diff = min_diff_time = 10000

    for goal_time in goal_times:
        # calculating time difference between current shot and goal time
        diff = abs(goal_time - shot['time'])
        # updating minimum difference and minimum difference index
        if diff < min_diff:
            min_diff = diff
            min_diff_time = goal_time

    # correcting current shot's time if a difference to the time a goal scored
    # was found
    if min_diff:
        shot['time'] = min_diff_time

    return shot


def set_period(shot, season):
    """
    Sets period of a shot in accordance of its actual time.
    """
    # in season 2016/17 shot times are mainly set to full period times with
    # 0 meaning first period, 1200 second period etc.
    if season == 2016:
        shot['period'] = shot['time'] // 1200 + 1
    else:
        if shot['time'] % 20 != 0:
            shot['period'] = shot['time'] // 1200 + 1
        else:
            shot['period'] = shot['time'] // 1200
    if shot['period'] == 0:
        shot['period'] = 1
    elif shot['period'] > 3:
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


def retrieve_shifts(shifts_src_path):
    """
    Retrieves shifts as interval tree from original data.
    """
    shifts = IntervalTree()
    if not os.path.isfile(shifts_src_path):
        return shifts

    shifts_orig = json.loads(open(shifts_src_path).read())

    for shift in shifts_orig:
        payload = dict()
        payload['player_id'] = shift['player']['id']
        payload['player'] = shift['player']['name']
        payload['team_id'] = shift['team']['id']
        payload['team'] = CONFIG['teams'][payload['team_id']]
        payload['start'] = shift['startTime']['time']
        payload['end'] = shift['endTime']['time']
        if payload['start'] != payload['end']:
            shifts.addi(-payload['end'], -payload['start'], payload)

    return shifts


def retrieve_goals(events_src_path):
    """
    Retrieves goals (along with corresponding players on ice) from original
    events data.
    """
    goals = dict()
    if not os.path.isfile(events_src_path):
        return goals

    events_orig = json.loads(open(events_src_path).read())

    for period in events_orig:
        for event in events_orig[period]:
            if event['type'] == 'goal':
                goals[event['time']] = event['data']

    return goals


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
    parser.add_argument(
        '-s', '--season', dest='season', required=False, default=2020,
        type=int, metavar='season to process games for',
        choices=[2016, 2017, 2018, 2019, 2020],
        help="The season information will be processed for")

    args = parser.parse_args()

    initial = args.initial
    limit = args.limit
    season = args.season

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))

    # setting up source and target paths
    src_path = os.path.join(tgt_dir, GAME_SRC)
    tgt_path = os.path.join(tgt_dir, SHOTS_DATA_TGT)
    pp_tgt_path = os.path.join(tgt_dir, PP_SITS_DATA_TGT)

    # loading games
    games = json.loads(open(src_path).read())
    # loading players
    all_players = json.loads(open(ALL_PLAYERS).read())

    # loading existing shots
    if not initial and os.path.isfile(tgt_path):
        all_shots = json.loads(open(tgt_path).read())
    # or preparing empty container for all shots
    else:
        all_shots = list()

    all_pp_situations_goals = dict()

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

        # retrieving raw shot data
        shots_src_path = os.path.join(
            CONFIG['base_data_dir'], 'shots',
            str(game['season']), str(game_type), "%d.json" % game['game_id'])
        if not os.path.isfile(shots_src_path):
            print("+ Skipping game since shot data is unavailable")
            continue

        shifts_src_path = os.path.join(
            CONFIG['base_data_dir'], 'shifts', str(game['season']),
            str(game_type), "%d.json" % game['game_id'])

        events_src_path = os.path.join(
            CONFIG['base_data_dir'], 'game_events', str(game['season']),
            str(game_type), "%d.json" % game['game_id'])

        shifts = retrieve_shifts(shifts_src_path)
        goals = retrieve_goals(events_src_path)
        match_data = json.loads(open(shots_src_path).read())

        home_score_diff, road_score_diff = 0, 0

        orig_shots = match_data['match']['shots']
        # sorting original shots to get score differences right all the time
        orig_shots = sorted(orig_shots, key=lambda s: s['time'])
        # preparing set of shots to avoid registering duplicate ones later on
        shots_set = set()

        for shot in orig_shots[:]:
            shot['game_id'] = game['game_id']
            # TODO: activate when schedule game id is available again
            # shot['schedule_game_id'] = game['schedule_game_id']
            shot['season_type'] = game['season_type']

            # checking if shot with same characteristics has already been registered
            # cases in 2020/21: game_id 1865, time: 106 & game_id 1870, time_ids: 1175/2153
            shot_pseudo_hash = (
                shot['game_id'], shot['time'], shot['player_id'], shot['coordinate_x'], shot['coordinate_y'])
            if shot_pseudo_hash in shots_set:
                print(
                    "\t+ Shot with same characteristics (%s at %02d:%02d from (%d, %d)) already registered, " % (
                        shot['last_name'], shot['time'] // 60, shot['time'] % 60,
                        shot['coordinate_x'], shot['coordinate_y']
                    ) + "therefore skipping it")
                continue
            shots_set.add(shot_pseudo_hash)

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
                shot['home_road'] = 'road'
                shot['score_diff'] = road_score_diff
                dst = rd.HOME_GOAL.distance(shot_pnt)
            elif shot['team_id'] == game['home_id']:
                shot['team'] = game['home_abbr']
                shot['team_against'] = game['road_abbr']
                shot['home_road'] = 'home'
                shot['score_diff'] = home_score_diff
                dst = rd.ROAD_GOAL.distance(shot_pnt)
            shot['distance'] = round(dst, 2)
            # determining shot zone
            shot['shot_zone'] = None
            # first checking whether shot is actually in one of the defined shot zone polygons
            for poly_name, poly in rd.polygons:
                if poly.contains(shot_pnt):
                    shot['shot_zone'] = poly_name[5:]
                    # checking whether determined shot zone matches polygon in original data
                    if poly_name in rd.polygon_to_original_mapping:
                        if 'polygon' in shot and shot['polygon'] != rd.polygon_to_original_mapping[poly_name]:
                            # print("\tRetrieved shot zone '%s' does not match original polygon '%s'" % (
                            #     poly_name, shot['polygon']))
                            # print(shot)
                            # print(shot_pnt)
                            pass
                    break
            if shot['shot_zone'] is None:
                for poly_name, poly in rd.polygons:
                    if poly.intersects(shot_pnt):
                        shot['shot_zone'] = poly_name[5:]
                        if poly_name in rd.polygon_to_original_mapping:
                            if 'polygon' in shot and shot['polygon'] != rd.polygon_to_original_mapping[poly_name]:
                                # print(
                                #     "\tRetrieved shot zone '%s' by intersect does not match original polygon '%s'" % (
                                #         poly_name, shot['polygon']))
                                # print(shot)
                                # print(shot_pnt)
                                pass
                        break
            # determining target and outcome of shot
            shot['target_type'] = SHOT_RESULTS[shot['match_shot_resutl_id']]
            if shot['target_type'] == 'post':
                shot['target_type'] = 'missed'
                shot['hit_post'] = True
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
            shot = set_period(shot, season)

            # retrieving skater situation at time of shot
            if not shot['time']:
                print("\t+ Shot registered at 00:00, therefore unable to retrieve skater situation for this one")
            else:
                try:
                    skr_situation = times[shot['time']]
                except KeyError:
                    if shot['time'] > max(times.keys()):
                        print(
                            "\t+ Shot at %02d:%02d after the actual " % (shot['time'] // 60, shot['time'] % 60) +
                            "end of game (%02d:%02d) registered" % (max(times.keys()) // 60, max(times.keys()) % 60))
                        shot['time'] = max(times.keys())

                if skr_situation[shot['team']] == skr_situation[shot['team_against']]:
                    shot['situation'] = 'EV'
                elif skr_situation[shot['team']] > skr_situation[shot['team_against']]:
                    shot['situation'] = 'PP'
                elif skr_situation[shot['team']] < skr_situation[shot['team_against']]:
                    shot['situation'] = 'SH'

                shot['plr_situation'] = "%dv%d" % (skr_situation[shot['team']], skr_situation[shot['team_against']])
                shot['plr_situation_against'] = "%dv%d" % (
                    skr_situation[shot['team_against']], skr_situation[shot['team']])

                # setting 6v5 or 5v6 situations back to 'EV'
                if '6' in shot['plr_situation'] and '5' in shot['plr_situation']:
                    shot['situation'] = 'EV'

                # retrieving players on ice via event data in case of a goal
                if shot['scored'] and goals:
                    goal = goals[shot['time']]
                    # re-calculating home and road score differentials
                    home_score, road_score = [int(x) for x in goal['currentScore'].split(":")]
                    home_score_diff = home_score - road_score
                    road_score_diff = road_score - home_score
                    # retrieving players on ice for goal from events data
                    shot['players_on_for'] = sorted([plr['playerId'] for plr in goal['attendants']['positive']])
                    shot['players_on_against'] = sorted([plr['playerId'] for plr in goal['attendants']['negative']])
                # retrieving players on ice from shifts data
                elif shifts:
                    skaters = shifts[-shot['time']]
                    shot['players_on_for'] = sorted([
                        plr[-1]['player_id'] for plr in skaters if plr[-1]['team'] == shot['team']])
                    shot['players_on_against'] = sorted([
                        plr[-1]['player_id'] for plr in skaters if plr[-1]['team'] == shot['team_against']])
                # using empty lists if no shift data is available
                else:
                    shot['players_on_for'] = list()
                    shot['players_on_against'] = list()

                # retrieving goalie facing the shot
                if game['home_abbr'] == shot['team_against']:
                    shot['goalie'] = times[shot['time']]['home_goalie']
                else:
                    shot['goalie'] = times[shot['time']]['road_goalie']

                # retrieving handedness of shooter
                if str(shot['player_id']) in all_players:
                    shot['hand'] = all_players[str(shot['player_id'])]['hand']

                # deleting unnecessary shot properties
                shot = delete_shot_properties(shot)

                all_shots.append(shot)

        if limit and cnt >= limit:
            break

        # retrieving power play opportunities and goals grouped by
        # skater situation
        # not perfect yet, need to do this whilst reconstructing skater
        # situation
        pp_situations = defaultdict(int)
        pp_goals = defaultdict(int)
        prev_situation = (5, 5)

        for time in times:
            curr_situation = (
                times[time]['home'], times[time]['road'])
            if curr_situation != prev_situation:
                pp_situations[curr_situation] += 1
                prev_situation = curr_situation
            if time in goal_times and goal_times[time].startswith("PP"):
                pp_goals[curr_situation] += 1
                # print("Goal at", time, "in", curr_situation)

        pp_situations_goals = dict()
        pp_situations_goals['game_id'] = game['game_id']
        pp_situations_goals['home'] = defaultdict(dict)
        pp_situations_goals['road'] = defaultdict(dict)

        for situation in [(5, 4), (5, 3), (4, 3), (4, 5), (3, 5), (3, 4)]:
            sit_key = "%dv%d" % situation
            pp_situations_goals['home']['pp_sits'][sit_key] = 0
            pp_situations_goals['home']['pp_goals'][sit_key] = 0
            pp_situations_goals['road']['pp_sits'][sit_key] = 0
            pp_situations_goals['road']['pp_goals'][sit_key] = 0

        for situation in pp_situations:
            sit_key = "%dv%d" % situation
            pp_situations_goals['home']['pp_sits'][sit_key] = (
                pp_situations[situation])
            pp_situations_goals['road']['pp_sits'][sit_key[::-1]] = (
                pp_situations[situation])
        for situation in pp_goals:
            sit_key = "%dv%d" % situation
            pp_situations_goals['home']['pp_goals'][sit_key] = (
                pp_goals[situation])
            pp_situations_goals['road']['pp_goals'][sit_key[::-1]] = (
                pp_goals[situation])

        all_pp_situations_goals[game['game_id']] = pp_situations_goals

    open(pp_tgt_path, 'w').write(json.dumps(all_pp_situations_goals, indent=2))

    CSV_OUT_FIELDS = [
        'player_id', 'jersey', 'first_name', 'last_name', 'team_id', 'time',
        'coordinate_x', 'coordinate_y', 'polygon', 'game_id', 'season_type',
        'x', 'y', 'team', 'team_against', 'distance', 'shot_zone',
        'target_type', 'scored', 'period', 'situation', 'plr_situation',
        'plr_situation_against', 'goalie'
    ]

    tgt_csv_path = os.path.join(tgt_dir, SHOTS_DATA_TGT.replace("json", "csv"))

    open(tgt_path, 'w').write(json.dumps(all_shots, indent=2, default=str))

    with open(tgt_csv_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        dict_writer = csv.DictWriter(
            output_file, CSV_OUT_FIELDS, delimiter=';', lineterminator='\n',
            extrasaction='ignore')
        dict_writer.writeheader()
        dict_writer.writerows(all_shots)
