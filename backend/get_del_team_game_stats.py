#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import argparse

from datetime import datetime

import requests

from utils import name_corrections, get_game_info

BASE_URL = 'https://www.del.org/live-ticker'

MATCHES_INSERT = 'matches'

HOME_STATS_SUFFIX = 'team-stats-home.json'
ROAD_STATS_SUFFIX = 'team-stats-guest.json'

GAME_SRC = 'del_games.json'
SHOT_SRC = 'del_shots.json'
TEAM_GAME_STATS_TGT = 'del_team_game_stats.json'

TGT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

SHOT_ZONE_CATEGORIES = [
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
    'behind_goal_pctg', 'behind_goal_on_goal_pctg',
]


def group_shot_data_by_game_team(shots):
    """
    Groups shot data by game and team using the globally defined shot zones
    and target types.
    """
    grouped_shot_data = dict()

    zones = [
        'slot', 'left', 'right', 'blue_line', 'neutral_zone', 'behind_goal']

    for shot in shots[:]:
        game_team_key = (shot['game_id'], shot['team'])
        if game_team_key not in grouped_shot_data:
            grouped_shot_data[game_team_key] = dict()
            for shot_zone_cat in SHOT_ZONE_CATEGORIES:
                grouped_shot_data[game_team_key][shot_zone_cat] = 0
                if 'distance' in shot_zone_cat:
                    grouped_shot_data[game_team_key][shot_zone_cat] = list()
        zone = shot['shot_zone'].lower()
        zone_tgt_type = "%s_%s" % (zone, shot['target_type'])
        zone_distance = "%s_distance" % zone
        grouped_shot_data[game_team_key]["%s_shots" % zone] += 1
        grouped_shot_data[game_team_key][zone_tgt_type] += 1
        grouped_shot_data[game_team_key][zone_distance].append(
            shot['distance'])
        if shot['scored']:
            grouped_shot_data[game_team_key]["%s_goals" % zone] += 1
    else:
        for key in grouped_shot_data:
            all_shots = 0
            all_on_goal = 0
            for zone in zones:
                all_shots += grouped_shot_data[key]["%s_shots" % zone]
                all_on_goal += grouped_shot_data[key]["%s_on_goal" % zone]
                if grouped_shot_data[key]["%s_shots" % zone]:
                    grouped_shot_data[key]["%s_distance" % zone] = round(
                        sum(grouped_shot_data[key]["%s_distance" % zone]) /
                        grouped_shot_data[key]["%s_shots" % zone], 2
                    )
                else:
                    grouped_shot_data[key]["%s_distance" % zone] = 0
            for zone in zones:
                if not all_shots:
                    print(key)

                grouped_shot_data[key]["%s_pctg" % zone] = round((
                    grouped_shot_data[key]["%s_shots" % zone] / all_shots
                ) * 100., 2)
                grouped_shot_data[key]["%s_on_goal_pctg" % zone] = round((
                    grouped_shot_data[key]["%s_on_goal" % zone] / all_on_goal
                ) * 100., 2)

    return grouped_shot_data


def get_single_game_team_data(game, grouped_shot_data):
    """
    Retrieves statistics for both teams participating in specified game.
    """
    game_stat_lines = list()

    game_id = game['game_id']

    home_stats_url = "%s/%s/%d/%s" % (
        BASE_URL, MATCHES_INSERT, game_id, HOME_STATS_SUFFIX)
    road_stats_url = "%s/%s/%d/%s" % (
        BASE_URL, MATCHES_INSERT, game_id, ROAD_STATS_SUFFIX)

    raw_stats = dict()
    r = requests.get(home_stats_url)
    raw_stats['home'] = r.json()
    r = requests.get(road_stats_url)
    raw_stats['road'] = r.json()

    for key in ['home', 'road']:
        opp_key = 'road' if key == 'home' else 'home'
        game_stat_line = dict()
        # basic game information
        game_stat_line['game_date'] = game['date']
        game_stat_line['round'] = game['round']
        game_stat_line['game_id'] = game_id
        game_stat_line['schedule_game_id'] = game['schedule_game_id']
        game_stat_line['arena'] = correct_name(game['arena'])
        game_stat_line['attendance'] = game['attendance']
        # coaches and referees
        if "%s_coach" % key in game:
            game_stat_line['coach'] = correct_name(game["%s_coach" % key])
        else:
            game_stat_line['coach'] = None
        if "%s_coach" % opp_key in game:
            game_stat_line['opp_coach'] = correct_name(
                game["%s_coach" % opp_key])
        else:
            game_stat_line['opp_coach'] = None
        game_stat_line['ref_1'] = correct_name(game['referee_1'])
        game_stat_line['ref_2'] = correct_name(game['referee_2'])
        game_stat_line['lma_1'] = correct_name(game['linesman_1'])
        game_stat_line['lma_2'] = correct_name(game['linesman_2'])
        # outcomes
        game_stat_line['games_played'] = 1
        game_stat_line['home_road'] = key
        game_stat_line['team_id'] = game["%s_id" % key]
        game_stat_line['team'] = game["%s_abbr" % key]
        game_stat_line['score'] = game["%s_score" % key]
        game_stat_line['goals'] = game["%s_score" % key]
        game_stat_line['opp_team_id'] = game["%s_id" % opp_key]
        game_stat_line['opp_team'] = game["%s_abbr" % opp_key]
        game_stat_line['opp_score'] = game["%s_score" % opp_key]
        game_stat_line['opp_goals'] = game["%s_score" % opp_key]
        if game['shootout_game']:
            game_stat_line['game_type'] = 'SO'
        elif game['overtime_game']:
            game_stat_line['game_type'] = 'OT'
        else:
            game_stat_line['game_type'] = ''
        for gsl_key in ['w', 'rw', 'ow', 'sw', 'l', 'rl', 'ol', 'sl']:
            game_stat_line[gsl_key] = 0
        if game_stat_line['score'] > game_stat_line['opp_score']:
            game_stat_line['w'] += 1
            if game['shootout_game']:
                game_stat_line['sw'] += 1
                game_stat_line['goals'] -= 1
            elif game['overtime_game']:
                game_stat_line['ow'] += 1
            else:
                game_stat_line['rw'] += 1
        else:
            game_stat_line['l'] += 1
            if game['shootout_game']:
                game_stat_line['sl'] += 1
                game_stat_line['opp_goals'] -= 1
            elif game['overtime_game']:
                game_stat_line['ol'] += 1
            else:
                game_stat_line['rl'] += 1
        game_stat_line['points'] = (
            game_stat_line['rw'] * 3 + game_stat_line['ow'] * 2 +
            game_stat_line['sw'] * 2 + game_stat_line['sl'] * 1 +
            game_stat_line['ol'] * 1)
        # per-period goals
        for period in [1, 2, 3]:
            game_stat_line["goals_%d" % period] = game[
                "%s_goals_%d" % (key, period)]
            game_stat_line["opp_goals_%d" % period] = game[
                "%s_goals_%d" % (opp_key, period)]
        # situation after 20 and 40 minutes respectively
        for situation in [
            'tied20', 'lead20', 'trail20', 'tied40', 'lead40', 'trail40'
        ]:
            game_stat_line[situation] = False
        if game_stat_line['goals_1'] == game_stat_line['opp_goals_1']:
            game_stat_line['tied20'] = True
        elif game_stat_line['goals_1'] > game_stat_line['opp_goals_1']:
            game_stat_line['lead20'] = True
        else:
            game_stat_line['trail20'] = True
        goals40 = game_stat_line['goals_1'] + game_stat_line['goals_2']
        opp_goals40 = (
            game_stat_line['opp_goals_1'] + game_stat_line['opp_goals_2'])
        if goals40 == opp_goals40:
            game_stat_line['tied40'] = True
        elif goals40 > opp_goals40:
            game_stat_line['lead40'] = True
        else:
            game_stat_line['trail40'] = True
        # scored first?
        if game['first_goal'] == game_stat_line['home_road']:
            game_stat_line['scored_first'] = True
            game_stat_line['trailed_first'] = False
        else:
            game_stat_line['scored_first'] = False
            game_stat_line['trailed_first'] = True
        # shots
        game_stat_line['shots'] = raw_stats[key]['shotsAttempts']
        game_stat_line['shots_on_goal'] = raw_stats[key]['shotsOnGoal']
        game_stat_line['shots_missed'] = raw_stats[key]['shotsMissed']
        game_stat_line['shots_blocked'] = raw_stats[key]['shotsBlocked']
        game_stat_line['opp_shots'] = raw_stats[opp_key]['shotsAttempts']
        game_stat_line['opp_shots_on_goal'] = raw_stats[opp_key]['shotsOnGoal']
        game_stat_line['opp_shots_missed'] = raw_stats[opp_key]['shotsMissed']
        game_stat_line['opp_shots_blocked'] = raw_stats[
            opp_key]['shotsBlocked']
        game_stat_line['shot_pctg'] = round(
            game_stat_line['goals'] /
            game_stat_line['shots_on_goal'] * 100., 2)
        game_stat_line['opp_shot_pctg'] = round(
            game_stat_line['opp_goals'] /
            game_stat_line['opp_shots_on_goal'] * 100., 2)
        # saves
        game_stat_line['saves'] = raw_stats[key]['saves']
        game_stat_line['save_pctg'] = round(
            100 - game_stat_line['opp_goals'] /
            game_stat_line['opp_shots_on_goal'] * 100., 2)
        game_stat_line['opp_saves'] = raw_stats[opp_key]['saves']
        game_stat_line['opp_save_pctg'] = round(
            100 - game_stat_line['goals'] /
            game_stat_line['shots_on_goal'] * 100., 2)
        # pdo
        game_stat_line['pdo'] = round((
            game_stat_line['shot_pctg'] + game_stat_line['save_pctg']), 1)
        game_stat_line['opp_pdo'] = round((
            game_stat_line['opp_shot_pctg'] +
            game_stat_line['opp_save_pctg']), 1)
        # penalty minutes, power play and penalty killing
        game_stat_line['pim'] = raw_stats[key]['penaltyMinutes']
        game_stat_line['pp_time'] = raw_stats[key]['powerPlaySeconds']
        game_stat_line['pp_opps'] = raw_stats[key]['ppCount']
        game_stat_line['pp_goals'] = raw_stats[key]['ppGoals']
        if game_stat_line['pp_opps']:
            game_stat_line['pp_pctg'] = round((
                game_stat_line['pp_goals'] /
                game_stat_line['pp_opps']) * 100., 1)
        else:
            game_stat_line['pp_pctg'] = 0
        game_stat_line['opp_pim'] = raw_stats[opp_key]['penaltyMinutes']
        game_stat_line['opp_pp_time'] = raw_stats[opp_key]['powerPlaySeconds']
        game_stat_line['opp_pp_opps'] = raw_stats[opp_key]['ppCount']
        game_stat_line['opp_pp_goals'] = raw_stats[opp_key]['ppGoals']
        if game_stat_line['opp_pp_opps']:
            game_stat_line['opp_pp_pctg'] = round((
                game_stat_line['opp_pp_goals'] /
                game_stat_line['opp_pp_opps']) * 100., 1)
        else:
            game_stat_line['opp_pp_pctg'] = 0
        game_stat_line['sh_opps'] = raw_stats[key]['shCount']
        game_stat_line['sh_goals'] = raw_stats[key]['shGoals']
        if game_stat_line['sh_opps']:
            game_stat_line['pk_pctg'] = round(
                100 - game_stat_line['opp_pp_goals'] /
                game_stat_line['sh_opps'] * 100., 1)
        else:
            game_stat_line['pk_pctg'] = 0
        game_stat_line['opp_sh_opps'] = raw_stats[opp_key]['shCount']
        game_stat_line['opp_sh_goals'] = raw_stats[opp_key]['shGoals']
        if game_stat_line['opp_sh_opps']:
            game_stat_line['opp_pk_pctg'] = round(
                100 - game_stat_line['pp_goals'] /
                game_stat_line['opp_sh_opps'] * 100., 1)
        else:
            game_stat_line['opp_pk_pctg'] = 0
        # faceoffs
        game_stat_line['faceoffs_won'] = int(raw_stats[key]['faceOffsWon'])
        game_stat_line['faceoffs_lost'] = int(
            raw_stats[opp_key]['faceOffsWon'])
        game_stat_line['faceoffs'] = (
            game_stat_line['faceoffs_won'] + game_stat_line['faceoffs_lost'])
        game_stat_line['faceoff_pctg'] = round(
            game_stat_line['faceoffs_won'] /
            game_stat_line['faceoffs'] * 100., 1)
        # best players
        game_stat_line['best_plr_id'] = game["%s_best_player_id" % key]
        game_stat_line['best_plr'] = game["%s_best_player" % key]
        game_stat_line['opp_best_plr_id'] = game["%s_best_player_id" % opp_key]
        game_stat_line['opp_best_plr'] = game["%s_best_player" % opp_key]

        shot_data = grouped_shot_data[(game_id, game_stat_line['team'])]

        for item in shot_data:
            game_stat_line[item] = shot_data[item]

        game_stat_lines.append(game_stat_line)

    return game_stat_lines


def correct_name(name, corrections=name_corrections):
    if "," in name:
        name = " ".join([token.strip() for token in name.split(",")][::-1])
    if name.upper() == name:
        name = name.title()
    if name in name_corrections:
        name = name_corrections[name]
    return name


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Download DEL team game statistics.')
    parser.add_argument(
        '--initial', dest='initial', required=False,
        action='store_true', help='Re-create list of team games')
    parser.add_argument(
        '--limit', dest='limit', required=False, type=int, default=0,
        help='Number of maximum games to be processed')

    args = parser.parse_args()

    initial = args.initial
    limit = int(args.limit)

    if not os.path.isdir(TGT_DIR):
        os.makedirs(TGT_DIR)

    # setting up source and target paths
    src_path = os.path.join(TGT_DIR, GAME_SRC)
    shots_src_path = os.path.join(TGT_DIR, SHOT_SRC)
    tgt_path = os.path.join(TGT_DIR, TEAM_GAME_STATS_TGT)

    # loading games and shots
    games = json.loads(open(src_path).read())
    shots = json.loads(open(shots_src_path).read())
    # grouping shot data by game and team
    grouped_shot_data = group_shot_data_by_game_team(shots)

    # loading existing player game stats
    if not initial and os.path.isfile(tgt_path):
        team_game_stats = json.loads(open(tgt_path).read())[-1]
    else:
        team_game_stats = list()

    # retrieving set of games we already have retrieved player stats for
    registered_games = set([pg['game_id'] for pg in team_game_stats])

    cnt = 0
    for game in games[:]:
        cnt += 1
        # skipping already processed games
        if game['game_id'] in registered_games:
            continue
        print("+ Retrieving team stats for game %s" % get_game_info(game))
        single_team_game_stats = get_single_game_team_data(
            game, grouped_shot_data)
        team_game_stats.extend(single_team_game_stats)

        if limit and cnt >= limit:
            break

    # retrieving current timestamp to indicate last modification of dataset
    current_datetime = datetime.now().timestamp() * 1000
    output = [current_datetime, team_game_stats]

    open(tgt_path, 'w').write(
        json.dumps(output, indent=2, default=str))
