#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import argparse
import intervaltree
from collections import OrderedDict

import requests
from shapely.geometry import Point

import rink_dimensions as rd
from utils import get_game_info
from reconstruct_skater_situation import reconstruct_skater_situation


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
    Builds an interval tree holding information about goalie shifts and
    penalties. Later used to determine which goalie had to save a certain
    shot or what kind of player situation existed at the time of a shot.
    """
    # retrieving raw events data
    events_path = EVENTS_SUFFIX % game['game_id']
    events_url = "%s/%s" % (BASE_URL, events_path)
    r = requests.get(events_url)
    events_data = r.json()

    # using ordered dictionary to maintain insertion order of keys
    goalie_changes = OrderedDict()
    goalie_changes['home'] = list()
    goalie_changes['road'] = list()
    # goalie_in_net = {'home': 0, 'road': 0}
    goalie_for_team = {'home': None, 'road': None}

    # setting up interval tree
    it = intervaltree.IntervalTree()
    # setting up list to contain all end of period times and all times a goal
    # has been scored
    end_period_times = list()
    goal_times = list()

    # TODO: tidy up the following mess
    # sorting periods first to retain compatibility with Python 3.5
    for period in sorted(events_data.keys()):
        for event in events_data[period]:
            # retrieving type of event first
            event_type = event['type']

            # adding time of period end to list of period end times
            if event_type == 'periodEnd':
                end_period_times.append(event['time'])

            # adding time of goal to list of times a goal has been scored
            if event_type == 'goal':
                goal_times.append(event['time'])

            # handling penalties
            if event_type == 'penalty':
                create_penalty_interval(event, game, it)

            # registering goalie changes
            if event_type == 'goalkeeperChange':
                register_goalie_change(
                    event, game, goalie_changes, goalie_for_team)

    create_goalie_intervals(
        goalie_changes, goalie_for_team, end_period_times, game, it)

    return it, goal_times


def register_goalie_change(event, game, goalie_changes, goalie_for_team):
    """
    Registers a goalie change retrieved from game events by extending the
    specified list of previous changes and by updating the specified dictioary
    holding the current goalie for a team involved in the game.
    """
    # retrieving time of goalie change
    event_time = event['data']['time']
    # retrieving team involved in goalie change
    if event['data']['team'] == 'home':
        event_team = game['home_abbr']
        home_road = 'home'
    else:
        event_team = game['road_abbr']
        home_road = 'road'
    # handling outgoing goalie
    if event['data']['outgoingGoalkeeper']:
        change_type = 'goalie_out'
        player_id = event['data']['outgoingGoalkeeper']['playerId']
        # adding outgoing goalie to list of goalie changes
        goalie_changes[home_road].append((
            event_time, event_team, change_type, player_id))
        # updating the affected team's current goalie
        if goalie_for_team[home_road] == player_id:
            goalie_for_team[home_road] = None
    # handling incoming goalie
    if event['data']['player']:
        change_type = 'goalie_in'
        player_id = event['data']['player']['playerId']
        # adding incoming goalie to list of goalie changes
        goalie_changes[home_road].append((
            event_time, event_team, change_type, player_id))
        # updating the affected team's current goalie
        goalie_for_team[home_road] = player_id


def create_goalie_intervals(
        goalie_changes, goalie_for_team, end_period_times,
        game, interval_tree):
    """
    Creates time intervals containing all information about in-game goalie
    changes.
    """
    # first adding outgoing goalies at the end (e.g. maximum time) of
    # the game as these changes are not registered in the official list of
    # game events
    for key in goalie_for_team:
        if goalie_for_team[key] is not None:
            goalie_changes[key].append((
                # using the maximum time from all period end times as time
                # of game end
                max(end_period_times), game["%s_abbr" % key],
                'goalie_out', goalie_for_team[key]))

    # finally converting collected list of goalie changes to actual intervals
    for home_road in goalie_changes:
        for i in range(0, len(goalie_changes[home_road]) - 1, 2):
            goalie_in_time, goalie_in_team, _, goalie_in_id = (
                goalie_changes[home_road][i])
            goalie_out_time, _, _, _ = (goalie_changes[home_road][i + 1])
            # optionally switching goalie in and out times if necessary
            if goalie_out_time < goalie_in_time:
                goalie_in_time, goalie_out_time = (
                    goalie_out_time, goalie_in_time)
            # adding goalie shift to interval tree
            # both times are increased by 1 to work around the interval tree's
            # implementation to include the interval's lower bound (when the
            # new goalie actually hasn't been on the ice yet) in a query result
            # but not the interval's upper bound (which could be a problem if
            # a goalie coming out incidentally falls together with a goal he
            # surrendered)
            interval_tree.addi(
                goalie_in_time + 1, goalie_out_time + 1,
                ("goalie", goalie_in_team, goalie_in_id))


def create_penalty_interval(event, game, interval_tree):
    """
    Creates a time interval including all penalty-related information.
    """
    # retrieving involved teams
    if event['data']['team'] == 'home':
        penalty_team = game['home_abbr']
    else:
        penalty_team = game['road_abbr']
    # retrieving penalized player
    if (
        event['data']['disciplinedPlayer'] and
        'playerId' in event['data']['disciplinedPlayer']
    ):
        penalty_player_id = event['data']['disciplinedPlayer']['playerId']
        penalty_player = event['data']['disciplinedPlayer']['surname']
    else:
        penalty_player_id = None
        penalty_player = None
    # retrieving other penalty information
    penalty_start = event['data']['time']['from']['scoreboardTime']
    penalty_end = event['data']['time']['to']['scoreboardTime']
    duration = event['data']['duration']
    infraction = event['data']['codename']

    # disregarding penalties with zero length, i.e. penalty shots
    if penalty_end != penalty_start:
        penalty_description = "%d %s %s" % (
            duration, infraction, penalty_player)
        # adding penalty to interval tree
        # end time is increased by 1 to make sure goals scored at
        # the premature end of a penalty are actually recognized
        # as power play/shorthanded goals
        interval_tree.addi(
            penalty_start, penalty_end + 1,
            (penalty_description, penalty_team, penalty_player_id))


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

        # skipping already processed games
        if game['game_id'] in registered_games:
            continue
        print("+ Retrieving shots for game %s " % get_game_info(game))

        # collecting skater situation for each second of the game and a list
        # of times when goals has been scored
        times, goal_times = reconstruct_skater_situation(game)

        # retrieving raw shot data
        shots_path = SHOTS_SUFFIX % game['game_id']
        shots_url = "%s/%s" % (BASE_URL, shots_path)
        r = requests.get(shots_url)
        match_data = r.json()

        for shot in match_data['match']['shots'][:]:

            shot['game_id'] = game['game_id']
            shot['schedule_game_id'] = game['schedule_game_id']
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
                except KeyError as e:
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
