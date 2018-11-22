#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import json
from datetime import timedelta, date

from collections import defaultdict

from dateutil.parser import parse

PLAYER_GAME_STATS_SRC = 'del_player_game_stats.json'
AGGREGATED_PLAYER_STATS_TGT = 'del_player_game_stats_aggregated.json'
U23_CUTOFF_DATE = parse("1996-01-01")


# attributes to simply collect from single-game player statistics
TO_COLLECT = [
    'no', 'position', 'first_name', 'last_name', 'full_name', 'country',
    'shoots', 'date_of_birth', 'weight', 'height',
]
# attributes from single-game player statistics to aggregate as integers
TO_AGGREGATE_INTS = [
    'games_played', 'goals', 'assists', 'primary_assists', 'secondary_assists',
    'points', 'pim', 'plus', 'minus', 'plus_minus', 'pp_goals', 'pp_assists',
    'pp_primary_assists', 'pp_secondary_assists', 'pp_points', 'sh_goals',
    'gw_goals', 'shots', 'shots_on_goal', 'shots_missed', 'shots_blocked',
    'faceoffs', 'faceoffs_won', 'faceoffs_lost', 'blocked_shots', 'shifts',
    'penalties', 'pim_from_events', 'penalty_shots', '_2min', '_5min',
    '_10min', '_20min', 'lazy', 'roughing', 'reckless', 'other',
]
# attributes from single-game player statistics to aggregate as timedeltas
TO_AGGREGATE_TIMES = [
    'time_on_ice', 'time_on_ice_pp', 'time_on_ice_sh',
]
# attributes to calculate per-game relative values for
PER_GAME_ATTRS = [
    'goals', 'assists', 'primary_assists', 'secondary_assists', 'points',
    'pim', 'shots', 'shots_on_goal', 'shots_missed', 'shots_blocked',
    'blocked_shots', 'shifts', 'time_on_ice', 'time_on_ice_pp',
    'time_on_ice_sh',
]
# attributes to calculate per-60-minute relative values for
PER_60_ATTRS = [
    'goals', 'assists', 'primary_assists', 'secondary_assists', 'points',
    'shots', 'shots_on_goal', 'shots_missed', 'shots_blocked', 'blocked_shots',
    'pp_goals', 'pp_assists', 'pp_primary_assists', 'pp_secondary_assists',
    'pp_points', 'sh_goals',
]

ISO_COUNTRY_CODES = {
    'GER': 'de',
    'CAN': 'ca',
    'SWE': 'se',
    'USA': 'us',
    'FIN': 'fi',
    'ITA': 'it',
    'NOR': 'no',
    'FRA': 'fr',
    'LVA': 'lv',
    'SVK': 'sk',
    'DNK': 'dk',
    'RUS': 'ru',
    'SVN': 'si',
    'HUN': 'hu',
    'SLO': 'si',
}

OUT_FIELDS = [
    'player_id', 'team', 'no', 'position', 'first_name', 'last_name',
    'full_name', 'country', 'shoots', 'date_of_birth', 'age', 'height',
    'weight', 'games_played', 'goals', 'assists', 'primary_assists',
    'secondary_assists', 'points', 'plus', 'minus', 'plus_minus',
    'pp_goals', 'pp_assists', 'pp_primary_assists', 'pp_secondary_assists',
    'pp_points', 'sh_goals', 'gw_goals', 'shots', 'shots_on_goal',
    'shots_missed', 'shots_blocked', 'shot_pctg', 'faceoffs', 'faceoffs_won',
    'faceoffs_lost', 'faceoff_pctg', 'blocked_shots', 'shifts', 'penalties',
    'pim', '_2min', '_5min', '_10min', '_20min', 'lazy', 'roughing',
    'reckless', 'other', 'time_on_ice', 'time_on_ice_pp', 'time_on_ice_sh',
    'time_on_ice_seconds', 'time_on_ice_pp_seconds', 'time_on_ice_sh_seconds',
    'goals_per_game', 'assists_per_game', 'primary_assists_per_game',
    'secondary_assists_per_game', 'points_per_game', 'pim_per_game',
    'shots_per_game', 'shots_on_goal_per_game', 'shots_missed_per_game',
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


def calculate_player_age(player_dob):
    """
    Calculates current age of player with specified date of birth.
    """
    # parsing player's date of birth
    player_dob = parse(player_dob).date()
    # retrieving today's date
    today = date.today()
    # projecting player's date of birth to this year
    # TODO: check for Feb 29 in a leap year
    this_year_dob = date(today.year, player_dob.month, player_dob.day)

    # if this year's birthday has already passed...
    if (today - this_year_dob).days >= 0:
        # calculating age as years since year of birth and days since this
        # year's birthday
        years = today.year - player_dob.year
        days = (today - this_year_dob).days
    # otherwise...
    else:
        # projecting player's data of birth to last year
        # TODO: check for Feb 29 in a leap year
        last_year_dob = date(today.year - 1, player_dob.month, player_dob.day)
        # calculating age as years between last year and year of birth and days
        # since last year's birthday
        years = last_year_dob.year - player_dob.year
        days = (today - last_year_dob).days

    # converting result to pseudo-float
    return float("%d.%03d" % (years, days))


def convert_to_minutes(td):
    return "%02d:%02d" % (
        td.total_seconds() // 60, round(td.total_seconds() % 60, 0))


if __name__ == '__main__':

    src_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'data', PLAYER_GAME_STATS_SRC)
    tgt_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'data', AGGREGATED_PLAYER_STATS_TGT)
    tgt_csv_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'data',
        AGGREGATED_PLAYER_STATS_TGT.replace('json', 'csv'))

    # loading collected single-game player data
    last_modified, player_game_stats = json.loads(open(src_path).read())

    print("+ %d player-in-game items collected" % len(player_game_stats))

    # setting up data containers
    player_data = dict()
    aggregated_stats = dict()
    aggregate_time_stats = dict()

    for game_stat_line in player_game_stats:
        # constructing reference key
        player_team_key = (game_stat_line['player_id'], game_stat_line['team'])
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
            aggregated_stats[player_team_key][attr] += game_stat_line[attr]
        # aggregating timedelta attributes
        for attr in TO_AGGREGATE_TIMES:
            aggregate_time_stats[player_team_key][attr] += timedelta(
                seconds=game_stat_line[attr])

    # post-processing aggregated attributes
    aggregated_stats_as_list = list()

    for player_id, team in aggregated_stats:
        # constructing reference key
        key = (player_id, team)

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

        # setting up data dictionary for personal player attributes
        basic_values = dict()
        basic_values['player_id'] = player_id
        basic_values['team'] = team
        # retaining single valiue for personal player attribute
        for attr in TO_COLLECT:
            basic_values[attr] = list(player_data[key][attr])[-1]
        # calculating player age
        basic_values['age'] = calculate_player_age(
            basic_values['date_of_birth'])

        if (
            basic_values['country'] == 'GER' and
            parse(basic_values['date_of_birth']) >= U23_CUTOFF_DATE
        ):
            basic_values['u23'] = True
        else:
            basic_values['u23'] = False

        if basic_values['country'] in ISO_COUNTRY_CODES:
            basic_values[
                'iso_country'] = ISO_COUNTRY_CODES[basic_values['country']]
        else:
            basic_values['iso_country'] = None

        # combining data dictionaries
        all_values = {
            **basic_values,
            **aggregated_stats[key], **aggregate_time_stats[key]
        }
        aggregated_stats_as_list.append(all_values)

    # deriving further attributes
    for item in aggregated_stats_as_list:

        item['time_on_ice_seconds'] = item['time_on_ice'].total_seconds()
        item['time_on_ice_pp_seconds'] = item['time_on_ice_pp'].total_seconds()
        item['time_on_ice_sh_seconds'] = item['time_on_ice_sh'].total_seconds()

        # calculating shooting percentage
        if item['shots_on_goal']:
            item['shot_pctg'] = (
                item['goals'] / float(item['shots_on_goal']) * 100.)
        else:
            item['shot_pctg'] = 0.
        # calculating faceoff percentage
        if item['faceoffs']:
            item['faceoff_pctg'] = round(
                item['faceoffs_won'] / float(item['faceoffs']) * 100., 4)
        else:
            item['faceoff_pctg'] = 0.
        # calculating per-game relative values
        for attr in PER_GAME_ATTRS:
            per_game_attr = item[attr] / float(item['games_played'])
            try:
                item["%s_per_game" % attr] = round(per_game_attr, 4)
            except TypeError as e:
                item["%s_per_game" % attr] = per_game_attr

        item['time_on_ice_per_game_seconds'] = item[
            'time_on_ice_per_game'].total_seconds()
        item['time_on_ice_pp_per_game_seconds'] = item[
            'time_on_ice_pp_per_game'].total_seconds()
        item['time_on_ice_sh_per_game_seconds'] = item[
            'time_on_ice_sh_per_game'].total_seconds()

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

    open(tgt_path, 'w').write(
        json.dumps(output, indent=2, default=convert_to_minutes))

    keys = aggregated_stats_as_list[0].keys()

    with open(tgt_csv_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        dict_writer = csv.DictWriter(
            output_file, OUT_FIELDS, delimiter=';', lineterminator='\n',
            extrasaction='ignore')
        dict_writer.writeheader()
        dict_writer.writerows(aggregated_stats_as_list)
