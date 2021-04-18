#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import json
import yaml
import argparse
from datetime import timedelta

from collections import defaultdict

from dateutil.parser import parse

from utils import calculate_age, iso_country_codes, get_season

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

PLAYER_GAME_STATS_SRC = 'del_player_game_stats.json'
GOALIE_GAME_STATS_SRC = 'del_goalie_game_stats.json'
SHOTS_DATA_SRC = 'del_shots.json'
AGGREGATED_PLAYER_STATS_TGT = 'del_player_game_stats_aggregated.json'
AGGREGATED_GOALIE_STATS_TGT = 'del_goalie_game_stats_aggregated.json'
PLAYER_PERSONAL_DATA_TGT = 'del_player_personal_data.json'


# attributes to simply collect from single-game player statistics
TO_COLLECT = [
    'no', 'position', 'first_name', 'last_name', 'full_name', 'country',
    'shoots', 'date_of_birth', 'weight', 'height', 'season_type', 'status'
]
# attributes from single-game player statistics to aggregate as integers
TO_AGGREGATE_INTS = [
    'games_played', 'goals', 'assists', 'primary_assists', 'secondary_assists',
    'points', 'primary_points', 'pim', 'plus', 'minus', 'plus_minus',
    'pp_goals', 'pp_assists', 'pp_primary_assists', 'pp_secondary_assists',
    'pp_points', 'sh_goals', 'sh_assists', 'sh_points', 'gw_goals', 'shots',
    'shots_on_goal', 'shots_missed', 'shots_blocked', 'faceoffs',
    'faceoffs_won', 'faceoffs_lost', 'blocked_shots', 'shifts', 'penalties',
    'pim_from_events', 'penalty_shots', '_2min', '_5min', '_10min', '_20min',
    'lazy', 'roughing', 'reckless', 'other',
]
TO_AGGREGATE_INTS_GOALIES = [
    'games_played', 'games_started', 'toi', 'w', 'rw', 'ow', 'sw', 'l', 'rl',
    'ol', 'sl', 'shots_against', 'goals_against', 'sa_5v5', 'sa_4v4', 'sa_3v3',
    'sa_5v4', 'sa_5v3', 'sa_4v3', 'sa_4v5', 'sa_3v5', 'sa_3v4', 'ga_5v5',
    'ga_4v4', 'ga_3v3', 'ga_5v4', 'ga_5v3', 'ga_4v3', 'ga_4v5', 'ga_3v5',
    'ga_3v4', 'sa_slot', 'sa_blue_line', 'sa_left', 'sa_right',
    'sa_neutral_zone', 'ga_slot', 'ga_blue_line', 'ga_left', 'ga_right',
    'ga_neutral_zone', 'sa_ev', 'sa_sh', 'sa_pp', 'ga_ev', 'ga_sh', 'ga_pp',
    'so',
]
TO_CALCULATE_PCTG_GOALIES = [
    '5v5', '4v4', '3v3', '5v4', '5v3', '4v3', '4v5', '3v5', '3v4', 'slot',
    'blue_line', 'left', 'right', 'neutral_zone', 'ev', 'sh', 'pp'
]
# attributes from single-game player statistics to aggregate as timedeltas
TO_AGGREGATE_TIMES = [
    'time_on_ice', 'time_on_ice_pp', 'time_on_ice_sh',
]
# attributes to calculate per-game relative values for
PER_GAME_ATTRS = [
    'goals', 'assists', 'primary_assists', 'secondary_assists', 'points',
    'primary_points', 'pim', 'shots', 'shots_on_goal', 'shots_missed',
    'shots_blocked', 'blocked_shots', 'shifts', 'time_on_ice',
    'time_on_ice_pp', 'time_on_ice_sh',
]
# attributes to calculate per-60-minute relative values for
PER_60_ATTRS = [
    'goals', 'assists', 'primary_assists', 'secondary_assists', 'points',
    'primary_points', 'shots', 'shots_on_goal', 'shots_missed',
    'shots_blocked', 'blocked_shots', 'pp_goals', 'pp_assists',
    'pp_primary_assists', 'pp_secondary_assists', 'pp_points', 'sh_goals',
    'sh_assists', 'sh_points'
]

SHOT_STATS_ATTRS = [
    'slot_shots', 'slot_on_goal', 'slot_missed', 'slot_blocked', 'slot_goals',
    'slot_distance', 'slot_pctg', 'slot_on_goal_pctg',
    'left_shots', 'left_on_goal', 'left_missed', 'left_blocked', 'left_goals',
    'left_distance', 'left_pctg', 'left_on_goal_pctg',
    'right_shots', 'right_on_goal', 'right_missed', 'right_blocked',
    'right_goals', 'right_distance', 'right_pctg', 'right_on_goal_pctg',
    'blue_line_shots', 'blue_line_on_goal', 'blue_line_missed',
    'blue_line_blocked', 'blue_line_goals', 'blue_line_distance',
    'blue_line_pctg', 'blue_line_on_goal_pctg',
    'neutral_zone_shots', 'neutral_zone_on_goal', 'neutral_zone_missed',
    'neutral_zone_blocked', 'neutral_zone_goals', 'neutral_zone_distance',
    'neutral_zone_pctg', 'neutral_zone_on_goal_pctg',
    'behind_goal_shots', 'behind_goal_on_goal', 'behind_goal_missed',
    'behind_goal_blocked', 'behind_goal_goals', 'behind_goal_distance',
    'behind_goal_pctg', 'behind_goal_on_goal_pctg'
]

OUT_FIELDS = [
    'player_id', 'season_type', 'team', 'no', 'position',
    'first_name', 'last_name',
    'full_name', 'country', 'shoots', 'date_of_birth', 'age', 'height',
    'weight', 'games_played', 'goals', 'assists', 'primary_assists',
    'secondary_assists', 'points', 'primary_points', 'plus', 'minus',
    'plus_minus', 'pp_goals', 'pp_assists', 'pp_primary_assists',
    'pp_secondary_assists', 'pp_points', 'sh_goals', 'gw_goals', 'shots',
    'shots_on_goal', 'shots_missed', 'shots_blocked', 'shot_pctg', 'faceoffs',
    'faceoffs_won', 'faceoffs_lost', 'faceoff_pctg', 'blocked_shots', 'shifts',
    'penalties', 'pim', '_2min', '_5min', '_10min', '_20min', 'lazy',
    'roughing', 'reckless', 'other', 'time_on_ice', 'time_on_ice_pp',
    'time_on_ice_sh', 'time_on_ice_seconds', 'time_on_ice_pp_seconds',
    'time_on_ice_sh_seconds', 'goals_per_game', 'assists_per_game',
    'primary_assists_per_game', 'secondary_assists_per_game',
    'points_per_game', 'pim_per_game', 'shots_per_game',
    'shots_on_goal_per_game', 'shots_missed_per_game',
    'shots_blocked_per_game', 'blocked_shots_per_game', 'shifts_per_game',
    'time_on_ice_per_game', 'time_on_ice_pp_per_game',
    'time_on_ice_sh_per_game', 'time_on_ice_per_game_seconds',
    'time_on_ice_pp_per_game_seconds', 'time_on_ice_sh_per_game_seconds',
    'goals_per_60', 'assists_per_60', 'primary_assists_per_60',
    'secondary_assists_per_60', 'points_per_60', 'shots_per_60',
    'shots_on_goal_per_60', 'shots_missed_per_60', 'shots_blocked_per_60',
    'blocked_shots_per_60', 'pp_goals_per_60', 'pp_assists_per_60',
    'pp_primary_assists_per_60', 'pp_secondary_assists_per_60',
    'pp_points_per_60', 'sh_goals_per_60',
]


def convert_to_minutes(td):
    return "%02d:%02d" % (
        td.total_seconds() // 60, round(td.total_seconds() % 60, 0))


def get_shot_stats(player_id, team, season_type, shot_data):
    """
    Compiles and aggregates shot statistics for specified player and team.
    """
    shot_stats = dict()
    for attr in SHOT_STATS_ATTRS:
        shot_stats[attr] = 0

    # counters for all shots and all shots on goal respectively
    all_shots = 0
    on_goal = 0

    for shot in shot_data:
        if shot['player_id'] != player_id:
            continue
        if shot['team'] != team:
            continue
        if shot['season_type'] != season_type:
            continue
        all_shots += 1
        if "goal" in shot['target_type']:
            on_goal += 1
        shot_stats["%s_shots" % shot['shot_zone'].lower()] += 1
        # adding up shot distances
        shot_stats[
            "%s_distance" % shot['shot_zone'].lower()] += shot['distance']
        shot_zone_result = "%s_%s" % (
            shot['shot_zone'].lower(), shot['target_type'])
        shot_stats[shot_zone_result] += 1
        if shot['scored']:
            shot_stats["%s_goals" % shot['shot_zone'].lower()] += 1

    for zone in [
        'slot', 'left', 'right', 'blue_line', 'neutral_zone', 'behind_goal'
    ]:
        # calculating average distance to goal from all previously aggregated
        # distances and number of shots for the current shot zone
        if shot_stats["%s_distance" % zone]:
            shot_stats["%s_distance" % zone] = round(
                shot_stats["%s_distance" % zone] /
                float(shot_stats["%s_shots" % zone]), 2)
        # calculating shots on goal percentage for current shot zone in
        # relation to all shots on goal
        if shot_stats["%s_on_goal" % zone]:
            shot_stats["%s_on_goal_pctg" % zone] = round(
                shot_stats["%s_on_goal" % zone] / float(on_goal) * 100, 2)
        # calculating shots percentage for current shot zone in relation
        # to all shots
        if shot_stats["%s_shots" % zone]:
            shot_stats["%s_pctg" % zone] = round(
                shot_stats["%s_shots" % zone] / float(all_shots) * 100, 2)

    return shot_stats


def calculate_goalie_stats(player_id, team, aggregated_stats):
    """
    Calculates goaltender stats, i.e. save percentages and goals against
    average from previously aggregated stats.
    """
    goalie_stats = dict()
    # retrieving aggregated stats for current player and team
    aggregated_stats = aggregated_stats[(player_id, team, season_type)]
    # calculating overall save percentage and goals against average
    if aggregated_stats['shots_against']:
        goalie_stats['save_pctg'] = round(
            100 - aggregated_stats['goals_against'] /
            aggregated_stats['shots_against'] * 100., 3)
        goalie_stats['gaa'] = round(
            aggregated_stats['goals_against'] * 3600 /
            aggregated_stats['toi'], 2)
    else:
        goalie_stats['save_pctg'] = None
        goalie_stats['gaa'] = None

    # calculating save percentages for multiple skater situations and shot
    # zones
    for key in TO_CALCULATE_PCTG_GOALIES:
        if aggregated_stats["sa_%s" % key]:
            goalie_stats["save_pctg_%s" % key] = round(
                100 - aggregated_stats["ga_%s" % key] /
                aggregated_stats["sa_%s" % key] * 100., 3)
        else:
            goalie_stats["save_pctg_%s" % key] = None

    return goalie_stats


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Aggregate DEL player stats.')
    parser.add_argument(
        '-f', '--from', dest='from_date', required=False,
        metavar='first date to aggregate stats for', default=None,
        help="The first date statistics will be aggregated")
    parser.add_argument(
        '-t', '--to', dest='to_date', required=False,
        metavar='last date to aggregate stats for', default=None,
        help="The last date statistics will be aggregated")
    parser.add_argument(
        '-s', '--season', dest='season', required=False, type=int,
        metavar='season to download data for', default=2020,
        choices=[2016, 2017, 2018, 2019, 2020],
        help="The season for which data  will be aggregated")

    args = parser.parse_args()
    season = args.season
    from_date = args.from_date
    to_date = args.to_date

    if from_date is not None:
        from_date = parse(from_date)
    if to_date is not None:
        to_date = parse(to_date)

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))

    src_path = os.path.join(tgt_dir, PLAYER_GAME_STATS_SRC)
    shot_src_path = os.path.join(tgt_dir, SHOTS_DATA_SRC)
    goalie_src_path = os.path.join(tgt_dir, GOALIE_GAME_STATS_SRC)
    tgt_path = os.path.join(tgt_dir, AGGREGATED_PLAYER_STATS_TGT)
    tgt_goalies_path = os.path.join(tgt_dir, AGGREGATED_GOALIE_STATS_TGT)
    tgt_csv_path = os.path.join(
        tgt_dir, AGGREGATED_PLAYER_STATS_TGT.replace('json', 'csv'))
    tgt_personal_data_path = os.path.join(tgt_dir, PLAYER_PERSONAL_DATA_TGT)

    # loading collected single-game player data
    last_modified, player_game_stats = json.loads(open(src_path).read())
    goalie_game_stats = json.loads(open(goalie_src_path).read())
    # loading shot data
    shot_data = json.loads(open(shot_src_path).read())

    print("+ %d player-in-game items collected overall" % len(
        player_game_stats))

    # setting up data containers
    player_data = dict()
    aggregated_stats = dict()
    aggregate_time_stats = dict()
    filtered_cnt = 0

    for game_stat_line in player_game_stats:
        # applying optional time filters
        if from_date and parse(game_stat_line['game_date']) < from_date:
            continue
        if to_date and parse(game_stat_line['game_date']) > to_date:
            continue
        filtered_cnt += 1
        # constructing reference key
        player_team_key = (
            game_stat_line['player_id'],
            game_stat_line['team'],
            game_stat_line['season_type'])
        # creating empty data dictionaries
        if player_team_key not in aggregated_stats:
            aggregated_stats[player_team_key] = defaultdict(int)
            aggregate_time_stats[player_team_key] = defaultdict(timedelta)
            player_data[player_team_key] = defaultdict(set)

        # collecting personal player attributes
        for attr in TO_COLLECT:
            player_data[player_team_key][attr].add(game_stat_line[attr])
        # aggregating integer attributes
        for attr in TO_AGGREGATE_INTS:
            try:
                aggregated_stats[player_team_key][attr] += game_stat_line[attr]
            except TypeError:
                print("\t+ Unable to aggregate '%s' using current game's stat line" % attr)
        # aggregating timedelta attributes
        for attr in TO_AGGREGATE_TIMES:
            try:
                aggregate_time_stats[player_team_key][attr] += timedelta(
                    seconds=game_stat_line[attr])
            except TypeError:
                print("\t+ Unable to aggregate time parameter '%s' using current game's stat line" % attr)
    else:
        print("+ %d player-in-game items after filtering" % filtered_cnt)
        # re-setting games played counter for goaltenders
        for player_id, team, season_type in aggregated_stats:
            if (
                list(player_data[
                    (player_id, team, season_type)]['position'])[0] == 'GK'
            ):
                aggregated_stats[
                    (player_id, team, season_type)]['games_played'] = 0

    print("+ %d goalie-in-game items collected overall" % len(
        goalie_game_stats))

    filtered_cnt = 0

    for game_stat_line in goalie_game_stats:
        # applying optional time filters
        if from_date and parse(game_stat_line['game_date']) < from_date:
            continue
        if to_date and parse(game_stat_line['game_date']) > to_date:
            continue
        filtered_cnt += 1
        # constructing reference key
        goalie_team_key = (
            game_stat_line['goalie_id'],
            game_stat_line['team'],
            game_stat_line['season_type'])
        # creating empty data dictionaries
        if goalie_team_key not in aggregated_stats:
            aggregated_stats[goalie_team_key] = defaultdict(int)
            aggregate_time_stats[goalie_team_key] = defaultdict(timedelta)
            player_data[goalie_team_key] = defaultdict(set)
        # aggregating integer attributes for goaltenders
        for attr in TO_AGGREGATE_INTS_GOALIES:
            aggregated_stats[goalie_team_key][attr] += game_stat_line[attr]
    else:
        print("+ %d goalie-in-game items after filtering" % filtered_cnt)

    # post-processing aggregated attributes
    aggregated_stats_as_list = list()
    # preparing container for non-fluctuating data
    personal_player_data = dict()

    for player_id, team, season_type in aggregated_stats:
        # constructing reference key
        key = (player_id, team, season_type)

        for pd_item in player_data[key]:
            # reviewing multiple values for personal player attributes
            if len(player_data[key][pd_item]) > 1:
                print(
                    "+ %s (%s) registered with " % (
                        list(player_data[key]['full_name'])[-1], team) +
                    "multiple values for '%s': %s" % (
                        pd_item,
                        ", ".join([str(s) for s in player_data[key][pd_item]]))
                )

        if not player_data[key]:
            continue

        # setting up data dictionary for personal player attributes
        basic_values = dict()
        basic_values['player_id'] = player_id
        basic_values['team'] = team
        # retaining single (and most recent) value for personal player attribute
        for attr in TO_COLLECT:
            basic_values[attr] = list(player_data[key][attr])[-1]
        # calculating player age
        current_season = get_season()
        if current_season == season:
            basic_values['age'] = calculate_age(basic_values['date_of_birth'])
        else:
            # if we're not aggregating data for the current season, calculate age for
            # mid-point (i.e. turn of the year) in season of interest
            basic_values['age'] = calculate_age(basic_values['date_of_birth'], "%d-12-31" % season)

        # turning status code into different player type statuses
        if basic_values['status'][0] == 't':
            basic_values['u23'] = True
        else:
            basic_values['u23'] = False
        if basic_values['status'][1] == 't':
            basic_values['u20'] = True
        else:
            basic_values['u20'] = False
        if basic_values['status'][2] == 't':
            basic_values['rookie'] = True
        else:
            basic_values['rookie'] = False

        if basic_values['country'] in iso_country_codes:
            basic_values['iso_country'] = iso_country_codes[basic_values['country']]
        else:
            print(
                "+ Country code '%s' not found " % basic_values['country'] +
                "in list of available ones")
            basic_values['iso_country'] = None

        # calculating shot statistics
        # TODO: determine whether to deactivate for goalies
        shot_stats = get_shot_stats(player_id, team, season_type, shot_data)
        # calculating goaltender statistics
        if basic_values['position'] == 'GK':
            goalie_stats = calculate_goalie_stats(
                player_id, team, aggregated_stats)
        else:
            goalie_stats = dict()

        # combining data dictionaries
        all_values = {
            **basic_values,
            **aggregated_stats[key], **aggregate_time_stats[key],
            **shot_stats, **goalie_stats
        }
        aggregated_stats_as_list.append(all_values)
        personal_player_data[basic_values['player_id']] = basic_values

    # deriving further attributes
    for item in aggregated_stats_as_list:

        item['time_on_ice_seconds'] = item['time_on_ice'].total_seconds()
        item['time_on_ice_pp_seconds'] = item['time_on_ice_pp'].total_seconds()
        item['time_on_ice_sh_seconds'] = item['time_on_ice_sh'].total_seconds()

        # calculating shooting percentage
        if item['shots_on_goal']:
            item['shot_pctg'] = round(
                item['goals'] / float(item['shots_on_goal']) * 100., 2)
        else:
            item['shot_pctg'] = 0.
        # calculating faceoff percentage
        if item['faceoffs']:
            item['faceoff_pctg'] = round(
                item['faceoffs_won'] / float(item['faceoffs']) * 100., 4)
        else:
            item['faceoff_pctg'] = 0.
        # calculating power play point share among all points
        if item['points']:
            item['pp_pts_pctg'] = round(
                item['pp_points'] / item['points'] * 100, 4)
        else:
            item['pp_pts_pctg'] = 0.
        # calculating per-game relative values
        for attr in PER_GAME_ATTRS:
            if item['games_played']:
                per_game_attr = item[attr] / float(item['games_played'])
            else:
                if "time_on_ice" in attr:
                    per_game_attr = timedelta()
                else:
                    per_game_attr = 0
            try:
                item["%s_per_game" % attr] = round(per_game_attr, 4)
            except TypeError:
                item["%s_per_game" % attr] = per_game_attr

        item['time_on_ice_per_game_seconds'] = item[
            'time_on_ice_per_game'].total_seconds()
        item['time_on_ice_pp_per_game_seconds'] = item[
            'time_on_ice_pp_per_game'].total_seconds()
        item['time_on_ice_sh_per_game_seconds'] = item[
            'time_on_ice_sh_per_game'].total_seconds()
        if item['shifts']:
            item['time_on_ice_per_shift'] = round(
                item['time_on_ice_seconds'] / item['shifts'], 2)
        else:
            item['time_on_ice_per_shift'] = 0.

        # calculating per-60-minute relative values
        for attr in PER_60_ATTRS:
            # determining reference time interval
            if attr.startswith('pp_'):
                time_attr = 'time_on_ice_pp'
            elif attr.startswith('sh_'):
                time_attr = 'time_on_ice_sh'
            else:
                time_attr = 'time_on_ice'
            # calculating per-60-minute relative values
            if item[time_attr]:
                item["%s_per_60" % attr] = round(
                    item[attr] /
                    (item[time_attr].total_seconds() / 60) * 60, 4)

    output = [last_modified, aggregated_stats_as_list]
    output_personal_data = [last_modified, list(personal_player_data.values())]

    aggregated_goalie_stats = list()
    for item in aggregated_stats_as_list:
        if item['position'] == 'GK':
            aggregated_goalie_stats.append(item)

    if from_date is not None or to_date is not None:
        adjusted_player_stats_tgt = AGGREGATED_PLAYER_STATS_TGT
        if to_date is not None:
            to_prefix = "to%s" % to_date.strftime('%Y-%m-%d')
            adjusted_player_stats_tgt = "%s_%s" % (to_prefix, adjusted_player_stats_tgt)
        if from_date is not None:
            from_prefix = "from%s" % from_date.strftime('%Y-%m-%d')
            adjusted_player_stats_tgt = "%s_%s" % (from_prefix, adjusted_player_stats_tgt)

        tgt_path = os.path.join(tgt_dir, adjusted_player_stats_tgt)
        tgt_csv_path = os.path.join(tgt_dir, adjusted_player_stats_tgt.replace('json', 'csv'))

    open(tgt_path, 'w').write(json.dumps(output, indent=2, default=convert_to_minutes))
    open(tgt_goalies_path, 'w').write(json.dumps(aggregated_goalie_stats, indent=2, default=convert_to_minutes))
    open(tgt_personal_data_path, 'w').write(json.dumps(output_personal_data, indent=2))

    keys = aggregated_stats_as_list[0].keys()

    with open(tgt_csv_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        dict_writer = csv.DictWriter(output_file, OUT_FIELDS, delimiter=';', lineterminator='\n', extrasaction='ignore')
        dict_writer.writeheader()
        dict_writer.writerows(aggregated_stats_as_list)
