#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import json
import yaml
import argparse
import itertools

from datetime import datetime
from collections import defaultdict

from dateutil.parser import parse

from utils import get_game_info, get_game_type_from_season_type

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

PER_PLAYER_TGT_DIR = 'per_player'
GAME_SRC = 'del_games.json'
SHOT_SRC = 'del_shots.json'
PLAYER_GAME_STATS_TGT = 'del_player_game_stats.json'
# TODO: reduced csv output

PENALTY_CATEGORIES = {
    'lazy': ['TRIP', 'HOLD', 'HOOK', 'HO-ST', 'INTRF', 'SLASH'],
    'roughing': ['CHARG', 'ROUGH', 'BOARD', 'CROSS', 'FIST'],
    'reckless': [
        'HI-ST', 'ELBOW', 'L-HIT', 'CHE-H', 'KNEE', 'CHE-B', 'CLIP',
        'BUT-E', 'SPEAR'],
    'other': [
        'THR-S', 'UN-SP', 'DELAY', 'ABUSE', 'TOO-M', 'L-BCH', 'DIVE',
        'BENCH', 'BR-ST'],
}
REVERSE_PENALTY_CATEGORIES = dict()
for key, values in PENALTY_CATEGORIES.items():
    for value in values:
        REVERSE_PENALTY_CATEGORIES[value] = key

U23_CUTOFF_DATES = {
    2016: parse("1994-01-01"),
    2017: parse("1995-01-01"),
    2018: parse("1996-01-01"),
    2019: parse("1997-01-01")
}

OUT_FIELDS = [
    "game_id", "player_id", "no", "position", "first_name", "last_name",
    "country", "shoots", "weight", "height", "date_of_birth",
    "u23", "home_road", "game_date", "season", "season_type", "round",
    "team", "score", "opp_team", "opp_score", "game_type",
    "games_played", "goals", "assists", "primary_assists",
    "secondary_assists", "points", "primary_points", "pim", "plus",
    "minus", "plus_minus", "pp_goals", "pp_assists",
    "pp_primary_assists", "pp_secondary_assists", "pp_points",
    "sh_goals", "sh_assists", "sh_points", "assists_5v5",
    "primary_assists_5v5", "points_5v5", "primary_points_5v5", "gw_goals",
    "shots", "shots_on_goal", "shots_missed", "shots_blocked",
    "faceoffs", "faceoffs_won", "faceoffs_lost", "blocked_shots",
    "time_on_ice", "time_on_ice_pp", "time_on_ice_sh", "shifts", "penalties",
    "pim_from_events", "penalty_shots", "first_goals", "_2min", "_5min",
    "_10min", "_20min", "lazy", "roughing", "reckless", "other", "shots_5v5",
    "shots_missed_5v5", "shots_on_goal_5v5", "goals_5v5", "line", "weekday",
    "slot_shots", "slot_on_goal", "slot_goals", "left_shots", "left_on_goal",
    "left_goals", "right_shots", "right_on_goal", "right_goals",
    "blue_line_shots", "blue_line_on_goal", "blue_line_goals",
    "neutral_zone_shots", "neutral_zone_on_goal", "neutral_zone_goals",
    "behind_goal_shots", "behind_goal_on_goal", "behind_goal_goals",
    "goals_5v5_from_events", "on_ice_sh_f", "on_ice_unblocked_sh_f",
    "on_ice_sog_f", "on_ice_goals_f", "on_ice_sh_f_5v5",
    "on_ice_unblocked_sh_f_5v5", "on_ice_sog_f_5v5", "on_ice_goals_f_5v5",
    "on_ice_sh_a", "on_ice_unblocked_sh_a", "on_ice_sog_a", "on_ice_goals_a",
    "on_ice_sh_a_5v5", "on_ice_unblocked_sh_a_5v5", "on_ice_sog_a_5v5",
    "on_ice_goals_a_5v5", 'game_score'
]

# default empty line
EMPTY_LINE = [0, 0, 0]
# defining potential lines and positions
LINES = ['1', '2', '3', '4']
POSITIONS = ['d', 'f']
POS_LINES = list(
    map(''.join, itertools.chain(itertools.product(POSITIONS, LINES))))


def retrieve_on_ice_stats(gsl, shots):

    # retrieving on-ice shots for (all situations)
    on_ice_shots_for = list(filter(
        lambda d: gsl['player_id'] in d['players_on_for'], shots))
    gsl['on_ice_sh_f'] = len(on_ice_shots_for)
    on_ice_shots_for_unblocked = list(filter(
        lambda d: d['target_type'] != 'blocked', on_ice_shots_for))
    gsl['on_ice_unblocked_sh_f'] = len(on_ice_shots_for_unblocked)
    on_ice_shots_for_on_goal = list(filter(
        lambda d: d['target_type'] == 'on_goal', on_ice_shots_for))
    gsl['on_ice_sog_f'] = len(on_ice_shots_for_on_goal)
    on_ice_goals_for = list(filter(
        lambda d: d['scored'] is True, on_ice_shots_for))
    gsl['on_ice_goals_f'] = len(on_ice_goals_for)

    # retrieving on-ice shots against (all situations)
    on_ice_shots_against = list(filter(
        lambda d: gsl['player_id'] in d['players_on_against'], shots))
    gsl['on_ice_sh_a'] = len(on_ice_shots_against)
    on_ice_shots_against_unblocked = list(filter(
        lambda d: d['target_type'] != 'blocked', on_ice_shots_against))
    gsl['on_ice_unblocked_sh_a'] = len(on_ice_shots_against_unblocked)
    on_ice_shots_against_on_goal = list(filter(
        lambda d: d['target_type'] == 'on_goal', on_ice_shots_against))
    gsl['on_ice_sog_a'] = len(on_ice_shots_against_on_goal)
    on_ice_goals_against = list(filter(
        lambda d: d['scored'] is True, on_ice_shots_against))
    gsl['on_ice_goals_a'] = len(on_ice_goals_against)

    # calculating percentages (all situations)
    on_ice_shots = gsl['on_ice_sh_f'] + gsl['on_ice_sh_a']
    if on_ice_shots:
        gsl['on_ice_sh_pctg'] = round(
            gsl['on_ice_sh_f'] / on_ice_shots * 100, 2)
    else:
        gsl['on_ice_sh_pctg'] = 0.
    on_ice_unblocked_shots = (
        gsl['on_ice_unblocked_sh_f'] + gsl['on_ice_unblocked_sh_a'])
    if on_ice_unblocked_shots:
        gsl['on_ice_unblocked_sh_pctg'] = round(
            gsl['on_ice_unblocked_sh_f'] / on_ice_unblocked_shots * 100, 2)
    else:
        gsl['on_ice_unblocked_sh_pctg'] = 0.
    on_ice_shots_on_goal = gsl['on_ice_sog_f'] + gsl['on_ice_sog_a']
    if on_ice_shots_on_goal:
        gsl['on_ice_sog_pctg'] = round(
            gsl['on_ice_sog_f'] / on_ice_shots_on_goal * 100, 2)
    else:
        gsl['on_ice_sog_pctg'] = 0.
    on_ice_goals = gsl['on_ice_goals_f'] + gsl['on_ice_goals_a']
    if on_ice_goals:
        gsl['on_ice_goals_pctg'] = round(
            gsl['on_ice_goals_f'] / on_ice_goals * 100, 2)
    else:
        gsl['on_ice_goals_pctg'] = 0.
    if gsl['on_ice_sog_f']:
        gsl['on_ice_shooting_pctg'] = round(
            gsl['on_ice_goals_f'] / gsl['on_ice_sog_f'] * 100, 2)
    else:
        gsl['on_ice_shooting_pctg'] = 0.
    if gsl['on_ice_sog_a']:
        gsl['on_ice_save_pctg'] = round(100 -
            gsl['on_ice_goals_a'] / gsl['on_ice_sog_a'] * 100, 2)
    else:
        gsl['on_ice_save_pctg'] = 0.
    gsl['on_ice_pdo'] = gsl['on_ice_shooting_pctg'] + gsl['on_ice_save_pctg']

    # retrieving on-ice shots for (5v5)
    on_ice_shots_for_5v5 = list(filter(
        lambda d: d['plr_situation'] == '5v5', on_ice_shots_for))
    gsl['on_ice_sh_f_5v5'] = len(on_ice_shots_for_5v5)
    on_ice_shots_for_unblocked_5v5 = list(filter(
        lambda d: d['plr_situation'] == '5v5', on_ice_shots_for_unblocked))
    gsl['on_ice_unblocked_sh_f_5v5'] = len(on_ice_shots_for_unblocked_5v5)
    on_ice_shots_for_on_goal_5v5 = list(filter(
        lambda d: d['plr_situation'] == '5v5', on_ice_shots_for_on_goal))
    gsl['on_ice_sog_f_5v5'] = len(on_ice_shots_for_on_goal_5v5)
    on_ice_goals_for_5v5 = list(filter(
        lambda d: d['scored'] is True, on_ice_shots_for_5v5))
    gsl['on_ice_goals_f_5v5'] = len(on_ice_goals_for_5v5)

    # retrieving on-ice shots against (5v5)
    on_ice_shots_against_5v5 = list(filter(
        lambda d: d['plr_situation'] == '5v5', on_ice_shots_against))
    gsl['on_ice_sh_a_5v5'] = len(on_ice_shots_against_5v5)
    on_ice_shots_against_unblocked_5v5 = list(filter(
        lambda d: d['plr_situation'] == '5v5', on_ice_shots_against_unblocked))
    gsl['on_ice_unblocked_sh_a_5v5'] = len(
        on_ice_shots_against_unblocked_5v5)
    on_ice_shots_against_on_goal_5v5 = list(filter(
        lambda d: d['plr_situation'] == '5v5', on_ice_shots_against_on_goal))
    gsl['on_ice_sog_a_5v5'] = len(on_ice_shots_against_on_goal_5v5)
    on_ice_goals_against_5v5 = list(filter(
        lambda d: d['scored'] is True, on_ice_shots_against_5v5))
    gsl['on_ice_goals_a_5v5'] = len(on_ice_goals_against_5v5)

    # calculating percentages (5v5)
    on_ice_shots_5v5 = gsl['on_ice_sh_f_5v5'] + gsl['on_ice_sh_a_5v5']
    if on_ice_shots_5v5:
        gsl['on_ice_sh_pctg_5v5'] = round(
            gsl['on_ice_sh_f_5v5'] / on_ice_shots_5v5 * 100, 2)
    else:
        gsl['on_ice_sh_pctg_5v5'] = 0.
    on_ice_unblocked_shots_5v5 = (
        gsl['on_ice_unblocked_sh_f_5v5'] + gsl['on_ice_unblocked_sh_a_5v5'])
    if on_ice_unblocked_shots_5v5:
        gsl['on_ice_unblocked_sh_pctg_5v5'] = round(
            gsl['on_ice_unblocked_sh_f_5v5'] /
            on_ice_unblocked_shots_5v5 * 100, 2)
    else:
        gsl['on_ice_unblocked_sh_pctg_5v5'] = 0.
    on_ice_shots_on_goal_5v5 = (
        gsl['on_ice_sog_f_5v5'] + gsl['on_ice_sog_a_5v5'])
    if on_ice_shots_on_goal_5v5:
        gsl['on_ice_sog_pctg_5v5'] = round(
            gsl['on_ice_sog_f_5v5'] / on_ice_shots_on_goal_5v5 * 100, 2)
    else:
        gsl['on_ice_sog_pctg_5v5'] = 0.
    on_ice_goals_5v5 = gsl['on_ice_goals_f_5v5'] + gsl['on_ice_goals_a_5v5']
    if on_ice_goals_5v5:
        gsl['on_ice_goals_pctg_5v5'] = round(
            gsl['on_ice_goals_f_5v5'] / on_ice_goals_5v5 * 100, 2)
    else:
        gsl['on_ice_goals_pctg_5v5'] = 0.
    if gsl['on_ice_sog_f_5v5']:
        gsl['on_ice_shooting_pctg_5v5'] = round(
            gsl['on_ice_goals_f_5v5'] / gsl['on_ice_sog_f_5v5'] * 100, 2)
    else:
        gsl['on_ice_shooting_pctg_5v5'] = 0.
    if gsl['on_ice_sog_a_5v5']:
        gsl['on_ice_save_pctg_5v5'] = round(100 - 
            gsl['on_ice_goals_a_5v5'] / gsl['on_ice_sog_a_5v5'] * 100, 2)
    else:
        gsl['on_ice_save_pctg_5v5'] = 0.
    gsl['on_ice_pdo_5v5'] = (
        gsl['on_ice_shooting_pctg_5v5'] + gsl['on_ice_save_pctg_5v5'])

    return gsl


def get_single_game_player_data(game, shots):
    """
    Retrieves statistics for all players participating in specified game.
    """
    game_stat_lines = list()
    game_id = game['game_id']
    home_id = game['home_id']
    road_id = game['road_id']
    game_type = get_game_type_from_season_type(game)

    home_stats_src_path = os.path.join(
        CONFIG['base_data_dir'], 'game_player_stats',
        str(game['season']), str(game_type), "%d_%d.json" % (game_id, home_id))
    road_stats_src_path = os.path.join(
        CONFIG['base_data_dir'], 'game_player_stats',
        str(game['season']), str(game_type), "%d_%d.json" % (game_id, road_id))
    game_events_src_path = os.path.join(
        CONFIG['base_data_dir'], 'game_events',
        str(game['season']), str(game_type), "%d.json" % game['game_id'])

    home_stats = json.loads(open(home_stats_src_path).read())
    road_stats = json.loads(open(road_stats_src_path).read())
    period_events = json.loads(open(game_events_src_path).read())

    for home_stat_line in home_stats:
        player_game = retrieve_single_player_game_stats(
            home_stat_line, game, 'home')
        if player_game['games_played']:
            game_stat_lines.append(player_game)

    for road_stat_line in road_stats:
        player_game = retrieve_single_player_game_stats(
            road_stat_line, game, 'away')
        if player_game['games_played']:
            game_stat_lines.append(player_game)

    assistants, scorers_5v5 = retrieve_assistants_from_event_data(
        period_events)
    penalties = retrieve_penalties_from_event_data(period_events)

    for gsl in game_stat_lines:
        # retrieving on-ice statistics
        gsl = retrieve_on_ice_stats(gsl, shots)
        # retrieving actual shots
        per_player_game_shots = list(filter(
            lambda d: d['player_id'] == gsl['player_id'], shots))
        shots_5v5 = list(filter(
            lambda d: d['plr_situation'] == '5v5', per_player_game_shots))
        gsl['shots_5v5'] = len(shots_5v5)
        shots_missed_5v5 = list(filter(
            lambda d: d['target_type'] == 'missed', shots_5v5))
        gsl['shots_missed_5v5'] = len(shots_missed_5v5)
        shots_on_goal_5v5 = list(filter(
            lambda d: d['target_type'] == 'on_goal', shots_5v5))
        gsl['shots_on_goal_5v5'] = len(shots_on_goal_5v5)
        goals_5v5 = list(filter(
            lambda d: d['scored'] is True, shots_on_goal_5v5))
        gsl['goals_5v5'] = len(goals_5v5)
        gsl['goals_5v5_from_events'] = 0
        if gsl['player_id'] in scorers_5v5:
            gsl['goals_5v5_from_events'] = scorers_5v5[gsl['player_id']]
        if gsl['player_id'] in assistants:
            single_assist_dict = assistants[gsl['player_id']]
            gsl['primary_assists'] = single_assist_dict.get('A1', 0)
            gsl['secondary_assists'] = single_assist_dict.get('A2', 0)
            gsl['pp_assists'] = single_assist_dict.get('PPA', 0)
            gsl['pp_primary_assists'] = single_assist_dict.get('PPA1', 0)
            gsl['pp_secondary_assists'] = single_assist_dict.get('PPA2', 0)
            gsl['pp_points'] += gsl['pp_assists']
            gsl['sh_assists'] = single_assist_dict.get('SHA', 0)
            gsl['sh_points'] += gsl['sh_assists']
            gsl['assists_5v5'] = single_assist_dict.get('5v5A', 0)
            gsl['primary_assists_5v5'] = single_assist_dict.get('5v5A1', 0)
            gsl['secondary_assists_5v5'] = single_assist_dict.get('5v5A2', 0)
        # calculating primary points
        gsl['primary_points'] = gsl['goals'] + gsl['primary_assists']
        gsl['points_5v5'] = gsl['goals_5v5_from_events'] + gsl['assists_5v5']
        gsl['primary_points_5v5'] = (
            gsl['goals_5v5_from_events'] + gsl['primary_assists_5v5'])
        # adding penalty information to player's game stat line
        if gsl['player_id'] in penalties:
            single_penalty_dict = penalties[gsl['player_id']]
            gsl['penalties'] = single_penalty_dict.get('penalties', 0)
            gsl['pim_from_events'] = single_penalty_dict.get('pim', 0)
            for l in [2, 5, 10, 20]:
                gsl["_%dmin" % l] = single_penalty_dict['durations'].get(l, 0)
            gsl['penalty_shots'] = single_penalty_dict.get('penalty_shots')
            for category in PENALTY_CATEGORIES:
                gsl[category] = single_penalty_dict['categories'].get(
                    category, 0)
        # adding linemate information to player's game stat line
        defense_linemates, forward_linemates, line = get_linemates(gsl, game)
        gsl['line'] = line
        gsl['defense'] = defense_linemates
        gsl['forwards'] = forward_linemates
        for shot_zone in [
            'slot', 'left', 'right', 'blue_line',
            'neutral_zone', 'behind_goal'
        ]:
            shots_from_zone = list(filter(
                lambda d: d['shot_zone'] == shot_zone.upper(),
                per_player_game_shots))
            gsl["%s_shots" % shot_zone] = len(shots_from_zone)
            missed_from_zone = list(filter(
                lambda d: d['target_type'] == 'missed',
                shots_from_zone))
            gsl["%s_missed" % shot_zone] = len(missed_from_zone)
            blocked_from_zone = list(filter(
                lambda d: d['target_type'] == 'blocked',
                shots_from_zone))
            gsl["%s_blocked" % shot_zone] = len(blocked_from_zone)
            shots_on_goal_from_zone = list(filter(
                lambda d: d['target_type'] == 'on_goal',
                shots_from_zone))
            gsl["%s_on_goal" % shot_zone] = len(shots_on_goal_from_zone)
            goals_from_zone = list(filter(
                lambda d: d['scored'], shots_on_goal_from_zone))
            gsl["%s_goals" % shot_zone] = len(goals_from_zone)

        gsl['game_score'] = round(
            0.75 * gsl['goals'] + 0.7 * gsl['primary_assists'] +
            0.55 * gsl['secondary_assists'] + 0.075 * gsl['shots_on_goal'] +
            0.05 * gsl['blocked_shots'] - 0.15 * gsl['penalties'] +
            0.01 * gsl['faceoffs_won'] - 0.01 * gsl['faceoffs_lost'] +
            0.05 * gsl['on_ice_sh_f'] - 0.05 * gsl['on_ice_sh_a'] +
            0.15 * gsl['on_ice_goals_f'] - 0.15 * gsl['on_ice_goals_a'], 2
        )

    return game_stat_lines


def retrieve_single_player_game_stats(data_dict, game, key):
    """
    Retrieves single player's statistics in specified game.
    """
    game_id = game['game_id']
    # retrieving individual base data
    single_player_game = dict()
    single_player_game['game_id'] = game_id
    # TODO: reactivate when schedule game id is available again
    # single_player_game['schedule_game_id'] = game['schedule_game_id']
    single_player_game['player_id'] = data_dict['id']
    single_player_game['no'] = data_dict['jersey']
    single_player_game['position'] = data_dict['position']
    single_player_game['first_name'] = data_dict['firstname']
    single_player_game['last_name'] = data_dict['surname']
    single_player_game['full_name'] = data_dict['name']
    single_player_game['country'] = data_dict['nationalityShort']
    single_player_game['shoots'] = data_dict['stick']
    single_player_game['weight'] = data_dict['weight']
    single_player_game['height'] = data_dict['height']
    single_player_game['date_of_birth'] = data_dict['dateOfBirth']
    # setting u23 status
    if (
        single_player_game['country'] == 'GER' and
        parse(single_player_game['date_of_birth']) >= U23_CUTOFF_DATES[
            game['season']]
    ):
        single_player_game['u23'] = True
    else:
        single_player_game['u23'] = False
    # setting up actual stats dictionary
    stat_dict = data_dict['statistics']
    # retrieving game stats for current player
    if key == 'home':
        single_player_game['home_road'] = key
    else:
        single_player_game['home_road'] = "road"
    single_player_game['game_date'] = game['date']
    single_player_game['weekday'] = game['weekday']
    single_player_game['season'] = game['season']
    single_player_game['season_type'] = game['season_type']
    single_player_game['round'] = game['round']
    single_player_game['team'] = stat_dict['teamShortcut']
    if key == 'home':
        single_player_game['score'] = game['home_score']
        single_player_game['opp_team'] = game['road_abbr']
        single_player_game['opp_score'] = game['road_score']
    else:
        single_player_game['score'] = game['road_score']
        single_player_game['opp_team'] = game['home_abbr']
        single_player_game['opp_score'] = game['home_score']
    if game['shootout_game']:
        single_player_game['game_type'] = 'SO'
    elif game['overtime_game']:
        single_player_game['game_type'] = 'OT'
    else:
        single_player_game['game_type'] = ''
    single_player_game['games_played'] = stat_dict['games']
    single_player_game['goals'] = stat_dict['goals'][key]
    single_player_game['assists'] = stat_dict['assists'][key]
    single_player_game['assists_5v5'] = 0
    single_player_game['primary_assists'] = 0
    single_player_game['secondary_assists'] = 0
    single_player_game['points'] = stat_dict['points'][key]
    single_player_game['primary_points'] = 0
    single_player_game['points_5v5'] = 0
    single_player_game['pim'] = stat_dict['penaltyMinutes']
    single_player_game['plus'] = stat_dict['positive']
    single_player_game['minus'] = stat_dict['negative']
    single_player_game['plus_minus'] = (
        stat_dict['positive'] - stat_dict['negative'])
    single_player_game['pp_goals'] = stat_dict['ppGoals']
    single_player_game['pp_assists'] = 0
    single_player_game['pp_primary_assists'] = 0
    single_player_game['pp_secondary_assists'] = 0
    single_player_game['primary_assists_5v5'] = 0
    single_player_game['secondary_assists_5v5'] = 0
    single_player_game['pp_points'] = single_player_game['pp_goals']
    single_player_game['sh_goals'] = stat_dict['shGoals']
    single_player_game['sh_assists'] = 0
    single_player_game['sh_points'] = single_player_game['sh_goals']
    single_player_game['gw_goals'] = stat_dict['gwGoals']
    single_player_game['shots'] = stat_dict['shotsAttempts']
    single_player_game['shots_on_goal'] = stat_dict['shotsOnGoal'][key]
    single_player_game['shots_missed'] = stat_dict['shotsMissed']
    single_player_game['shots_blocked'] = stat_dict['shotsBlocked']
    single_player_game['shot_pctg'] = stat_dict['shotEfficiency']
    single_player_game['faceoffs'] = stat_dict['faceoffsCount']
    single_player_game['faceoffs_won'] = stat_dict['faceoffsWin']
    single_player_game['faceoffs_lost'] = stat_dict['faceoffsLosses']
    if single_player_game['faceoffs']:
        single_player_game['faceoff_pctg'] = round(
            single_player_game['faceoffs_won'] /
            single_player_game['faceoffs'] * 100., 3)
    else:
        single_player_game['faceoff_pctg'] = 0
    single_player_game['blocked_shots'] = stat_dict['blockedShotsByPlayer']
    single_player_game['time_on_ice'] = stat_dict['timeOnIce']
    single_player_game['time_on_ice_pp'] = stat_dict['timeOnIcePP']
    single_player_game['time_on_ice_sh'] = stat_dict['timeOnIceSH']
    single_player_game['shifts'] = stat_dict['shifts']
    if single_player_game['shifts']:
        single_player_game['toi_per_shift'] = round(
            single_player_game['time_on_ice'] / single_player_game['shifts'], 2
        )
    else:
        single_player_game['toi_per_shift'] = 0.
    single_player_game['penalties'] = 0
    single_player_game['pim_from_events'] = 0
    single_player_game['penalty_shots'] = 0
    if game['first_goal_player_id'] == single_player_game['player_id']:
        single_player_game['first_goals'] = 1
    else:
        single_player_game['first_goals'] = 0
    for l in [2, 5, 10, 20]:
        single_player_game["_%dmin" % l] = 0
    for category in PENALTY_CATEGORIES:
        single_player_game[category] = 0

    return single_player_game


def retrieve_assistants_from_event_data(period_events):
    """
    Retrieves primary and secondary assists from game event data.
    """
    goals_5v5_dict = dict()
    assists_dict = dict()

    for period in period_events:
        events = period_events[period]
        for event in events:
            if event['type'] != 'goal':
                continue
            assist_cnt = 0
            # retrieving goals in 5v5
            scorer_plr_id = event['data']['scorer']['playerId']
            if event['data']['balance'] == 'EQ':
                if (
                    not event['data']['ea'] and
                    len(event['data']['attendants']['positive']) == 6 and
                    len(event['data']['attendants']['negative']) == 6
                ):
                    if scorer_plr_id not in goals_5v5_dict:
                        goals_5v5_dict[scorer_plr_id] = 0
                    goals_5v5_dict[scorer_plr_id] += 1
            # retrieving assists
            for assistant in event['data']['assistants']:
                assist_cnt += 1
                assist_plr_id = assistant['playerId']
                if assist_plr_id not in assists_dict:
                    assists_dict[assist_plr_id] = defaultdict(int)
                assists_dict[assist_plr_id]["A%d" % assist_cnt] += 1
                if 'PP' in event['data']['balance']:
                    assists_dict[assist_plr_id]["PPA"] += 1
                    assists_dict[assist_plr_id]["PPA%d" % assist_cnt] += 1
                if 'SH' in event['data']['balance']:
                    assists_dict[assist_plr_id]["SHA"] += 1
                    # assists_dict[assist_plr_id]["SHA%d" % assist_cnt] += 1
                if event['data']['balance'] == 'EQ':
                    if (
                        len(event['data']['attendants']['positive']) == 6 and
                        len(event['data']['attendants']['negative']) == 6
                    ):
                        assists_dict[assist_plr_id]["5v5A"] += 1
                        assists_dict[assist_plr_id]["5v5A%d" % assist_cnt] += 1

    return assists_dict, goals_5v5_dict


def retrieve_penalties_from_event_data(period_events):
    """
    Retrieves penalty information from game event data.
    """
    penalties_dict = dict()

    for period in period_events:
        events = period_events[period]
        for event in events:
            if event['type'] != 'penalty':
                continue

            player = event['data']['disciplinedPlayer']
            # skipping penalties w/o a disciplined player
            if player is None:
                continue
            plr_id = player['playerId']

            if plr_id not in penalties_dict:
                penalties_dict[plr_id] = dict()
                penalties_dict[plr_id]['penalties'] = 0
                penalties_dict[plr_id]['infractions'] = defaultdict(int)
                penalties_dict[plr_id]['penalty_shots'] = 0
                penalties_dict[plr_id]['pim'] = 0
                penalties_dict[plr_id]['durations'] = defaultdict(int)
                penalties_dict[plr_id]['categories'] = defaultdict(int)

            duration = event['data']['duration']
            infraction = event['data']['codename']
            pim = int(duration / 60)

            penalties_dict[plr_id]['penalties'] += 1
            penalties_dict[plr_id]['infractions'][infraction] += 1
            penalties_dict[plr_id]['pim'] += pim
            penalties_dict[plr_id]['durations'][pim] += 1

            if infraction not in REVERSE_PENALTY_CATEGORIES:
                print(
                    "Previously unknown infraction '%s' " % infraction +
                    "discovered. Added to 'other' category.")
                penalties_dict[plr_id]['categories']['other'] += 1
            else:
                penalties_dict[plr_id]['categories'][
                    REVERSE_PENALTY_CATEGORIES[infraction]] += 1

            if event['data']['shooting']:
                penalties_dict[plr_id]['penalty_shots'] += 1

    return penalties_dict


def get_linemates(game_stat_line, game):
    """
    Retrieving line mates in specified game for player with with given stat
    line.
    """
    # per default, linemates are non-existing
    defense = EMPTY_LINE[:2]
    forwards = EMPTY_LINE
    line = 0

    if game_stat_line['position'] != 'GK':
        player_id = game_stat_line['player_id']
        # iterating over all possible four lines/two positions
        for pos_line in POS_LINES:
            full_key = "%s_%s" % (game_stat_line['home_road'], pos_line)
            if full_key in game and player_id in game[full_key]:
                break

        # retrieving line number for current player
        if full_key:
            line = int(list(full_key)[-1])

        # complementing line information with players at different positions
        if "_f" in full_key:
            forwards = game[full_key]
            try:
                defense = game[full_key.replace("_f", "_d")]
            except KeyError:
                pass
        elif '_d' in full_key:
            defense = game[full_key]
            try:
                forwards = game[full_key.replace("_d", "_f")]
            except KeyError:
                pass

    return defense, forwards, line


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Download DEL player game statistics.')
    parser.add_argument(
        '--initial', dest='initial', required=False,
        action='store_true', help='Re-create list of player games')
    parser.add_argument(
        '--limit', dest='limit', required=False, type=int, default=0,
        help='Number of maximum games to be processed')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, default=2019,
        type=int, choices=[2016, 2017, 2018, 2019],
        metavar='season to process games for',
        help="The season information will be processed for")

    args = parser.parse_args()

    initial = args.initial
    limit = args.limit
    season = args.season

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))

    if not os.path.isdir(tgt_dir):
        os.makedirs(tgt_dir)
    if not os.path.isdir(os.path.join(tgt_dir, PER_PLAYER_TGT_DIR)):
        os.makedirs(os.path.join(tgt_dir, PER_PLAYER_TGT_DIR))

    # setting up source and target paths
    src_path = os.path.join(tgt_dir, GAME_SRC)
    src_shots_path = os.path.join(tgt_dir, SHOT_SRC)
    tgt_path = os.path.join(tgt_dir, PLAYER_GAME_STATS_TGT)

    # loading games
    games = json.loads(open(src_path).read())
    shots = json.loads(open(src_shots_path).read())

    # loading existing player game stats
    if not initial and os.path.isfile(tgt_path):
        player_game_stats = json.loads(open(tgt_path).read())[-1]
    else:
        player_game_stats = list()

    # setting up container for player game statistics
    per_player_game_stats = defaultdict(list)
    # retrieving set of games we already have retrieved player stats for
    registered_games = set([pg['game_id'] for pg in player_game_stats])

    cnt = 0

    for game in games[:]:
        cnt += 1
        # skipping already processed games
        if game['game_id'] in registered_games:
            continue

        # retrieving shots for current game
        game_shots = list(
            filter(lambda d: d['game_id'] == game['game_id'], shots))

        print("+ Retrieving player stats for game %s" % get_game_info(game))
        single_player_game_stats = get_single_game_player_data(
            game, game_shots)
        player_game_stats.extend(single_player_game_stats)

        # collecting stat lines on a per-player basis
        for stat_line in single_player_game_stats:
            per_player_game_stats[
                (stat_line['player_id'], stat_line['team'])].append(stat_line)

        if limit and cnt >= limit:
            break

    # retrieving current timestamp to indicate last modification of dataset
    current_datetime = datetime.now().timestamp() * 1000
    output = [current_datetime, player_game_stats]

    # dumping combined game stats for all players
    open(tgt_path, 'w').write(json.dumps(output, indent=2))

    tgt_csv_path = tgt_path.replace(".json", ".csv")
    with open(tgt_csv_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        dict_writer = csv.DictWriter(
            output_file, OUT_FIELDS, delimiter=';', lineterminator='\n',
            extrasaction='ignore')
        dict_writer.writeheader()
        dict_writer.writerows(player_game_stats)

    # dumping individual player game stats
    for player_id, team in per_player_game_stats:
        tgt_path = os.path.join(
            tgt_dir, PER_PLAYER_TGT_DIR, "%s_%d.json" % (team, player_id))

        output = per_player_game_stats[(player_id, team)]
        # optionally adding output to already existing data
        if not initial and os.path.isfile(tgt_path):
            existing_data = json.loads(open(tgt_path).read())
            existing_data.extend(output)
            output = existing_data

        open(tgt_path, 'w').write(json.dumps(output, indent=2))
