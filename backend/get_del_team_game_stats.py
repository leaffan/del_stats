#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import argparse

from datetime import datetime

import requests

BASE_URL = 'https://www.del.org/live-ticker'

MATCHES_INSERT = 'matches'

HOME_STATS_SUFFIX = 'team-stats-home.json'
ROAD_STATS_SUFFIX = 'team-stats-guest.json'

GAME_SRC = 'del_games.json'
TEAM_GAME_STATS_TGT = 'del_team_game_stats.json'

TGT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def get_single_game_team_data(game):
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
        game_stat_line['game_date'] = game['date']
        game_stat_line['round'] = game['round']
        game_stat_line['game_id'] = game_id
        game_stat_line['games_played'] = 1
        game_stat_line['home_away'] = key
        game_stat_line['team_id'] = game["%s_id" % key]
        game_stat_line['team'] = game["%s_abbr" % key]
        game_stat_line['score'] = game["%s_score" % key]
        game_stat_line['goals'] = game["%s_score" % key]
        game_stat_line['opp_team_id'] = game["%s_id" % opp_key]
        game_stat_line['opp_team'] = game["%s_abbr" % opp_key]
        game_stat_line['opp_score'] = game["%s_score" % opp_key]
        game_stat_line['opp_goals'] = game["%s_score" % opp_key]
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
        for period in [1, 2, 3]:
            game_stat_line["goals_%d" % period] = game[
                "%s_goals_%d" % (key, period)]
            game_stat_line["opp_goals_%d" % period] = game[
                "%s_goals_%d" % (opp_key, period)]
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
        game_stat_line['saves'] = raw_stats[key]['saves']
        game_stat_line['save_pctg'] = round(
            100 - game_stat_line['opp_goals'] /
            game_stat_line['opp_shots_on_goal'] * 100., 2)
        game_stat_line['opp_saves'] = raw_stats[opp_key]['saves']
        game_stat_line['opp_save_pctg'] = round(
            100 - game_stat_line['goals'] /
            game_stat_line['shots_on_goal'] * 100., 2)
        game_stat_line['pdo'] = round((
            game_stat_line['shot_pctg'] + game_stat_line['save_pctg']), 1)
        game_stat_line['opp_pdo'] = round((
            game_stat_line['opp_shot_pctg'] +
            game_stat_line['opp_save_pctg']), 1)
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
        game_stat_line['faceoffs_won'] = int(raw_stats[key]['faceOffsWon'])
        game_stat_line['faceoffs_lost'] = int(
            raw_stats[opp_key]['faceOffsWon'])
        game_stat_line['faceoffs'] = (
            game_stat_line['faceoffs_won'] + game_stat_line['faceoffs_lost'])
        game_stat_line['faceoff_pctg'] = round(
            game_stat_line['faceoffs_won'] /
            game_stat_line['faceoffs'] * 100., 1)

        game_stat_lines.append(game_stat_line)

    return game_stat_lines


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
    tgt_path = os.path.join(TGT_DIR, TEAM_GAME_STATS_TGT)

    # loading games
    games = json.loads(open(src_path).read())

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
        print("+ Retrieving team stats for %s (%d) vs. %s (%d) [%d]" % (
            game['home_team'], game['home_score'],
            game['road_team'], game['road_score'], game['game_id']))
        single_team_game_stats = get_single_game_team_data(game)
        team_game_stats.extend(single_team_game_stats)

        if limit and cnt >= limit:
            break

    # retrieving current timestamp to indicate last modification of dataset
    current_datetime = datetime.now().timestamp() * 1000
    output = [current_datetime, team_game_stats]

    open(tgt_path, 'w').write(
        json.dumps(output, indent=2, default=str))
