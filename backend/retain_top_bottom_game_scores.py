#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import argparse
import statistics

from operator import itemgetter


# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

PLAYER_GAME_STATS_SRC = 'del_player_game_stats.json'
GOALIE_GAME_STATS_SRC = 'del_goalie_game_stats.json'
PERSONAL_DATA_SRC = 'del_player_personal_data.json'
GAME_SCORE_TGT = 'del_game_scores_per_game_%s.json'


def retrieve_top_bottom_game_scores(player_game_stats, personal_data):
    """
    Identifies and returns top and bottom game scores from specified set of player game stats.
    """
    # getting all individual game score values
    game_scores = list(map(itemgetter('game_score'), player_game_stats))

    # calculating mean and standard deviation
    print("+ %d individual game scores collected" % len(game_scores))
    gs_mean = statistics.mean(game_scores)
    gs_stdev = statistics.stdev(game_scores)
    print("+ Average game score value: %g" % gs_mean)
    print("+ Game score standard deviation: %g" % gs_stdev)

    # identifying top and bottom game scores
    print("+ Collecting top game scores, i.e. greater or equal than %g" % (gs_mean + 1.5 * gs_stdev))
    print("+ Collecting bottom game scores, i.e. lesser or equal than %g" % (gs_mean - 1.5 * gs_stdev))

    top_game_scores = list(filter(lambda gs: gs['game_score'] >= (gs_mean + 1.5 * gs_stdev), player_game_stats))
    bottom_game_scores = list(filter(lambda gs: gs['game_score'] <= (gs_mean - 1.5 * gs_stdev), player_game_stats))

    print("+ %d top game scores identified" % len(top_game_scores))
    print("+ %d bottom game scores identified" % len(bottom_game_scores))

    stripped_top_game_scores = strip_game_scores(top_game_scores, personal_data)
    stripped_bottom_game_scores = strip_game_scores(bottom_game_scores, personal_data, 'b_single_game_score')

    return stripped_top_game_scores, stripped_bottom_game_scores


def strip_game_scores(orig_game_scores, personal_data, rename_game_score='single_game_score'):
    """
    Strips specified list of player game stats to retain only the keys
    defined below.
    """

    # data keys to retain from personal player data
    personal_data_keys = [
        'position', 'first_name', 'last_name', 'full_name', 'u23', 'u20', 'rookie', 'iso_country', 'age'
    ]

    # data keys to retaing from player game stats
    keys_to_retain = [
        'game_id', 'season_type', 'game_date', 'round', 'team', 'opp_team', 'score', 'opp_score', 'game_score',
        'home_road', 'game_type', 'time_on_ice',
    ]

    stripped_game_scores = list()
    for gs in orig_game_scores:
        if 'player_id' in gs:
            player_id = gs['player_id']
        else:
            player_id = gs['goalie_id']

        stripped_gs = {key_to_retain: gs[key_to_retain] for key_to_retain in keys_to_retain if key_to_retain in gs}

        for personal_data_key in personal_data_keys:
            stripped_gs[personal_data_key] = personal_data[player_id][personal_data_key]

        stripped_gs['player_id'] = player_id

        if 'toi' in gs:
            stripped_gs['time_on_ice'] = gs['toi']

        stripped_gs[rename_game_score] = stripped_gs['game_score']
        del stripped_gs['game_score']

        if stripped_gs['time_on_ice']:
            stripped_gs["game_score_per_60"] = round(
                stripped_gs[rename_game_score] / (stripped_gs['time_on_ice'] / 60) * 60, 4)
        else:
            stripped_gs["game_score_per_60"] = None

        stripped_game_scores.append(stripped_gs)

    return stripped_game_scores


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Strip game scores to retain only top and bottom values.')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, default=2020,
        type=int, choices=[2016, 2017, 2018, 2019, 2020],
        metavar='season to process games for',
        help="The season information will be processed for")

    args = parser.parse_args()

    season = args.season

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))

    src_player_stats_path = os.path.join(tgt_dir, PLAYER_GAME_STATS_SRC)
    src_goalie_stats_path = os.path.join(tgt_dir, GOALIE_GAME_STATS_SRC)
    src_personal_data_path = os.path.join(tgt_dir, PERSONAL_DATA_SRC)

    tgt_top_gs_path = os.path.join(tgt_dir, GAME_SCORE_TGT % 'top')
    tgt_bottom_gs_path = os.path.join(tgt_dir, GAME_SCORE_TGT % 'bottom')

    # loading player and goalie stats
    player_stats = json.loads(open(src_player_stats_path).read())[-1]
    print("+ %d player stats items loaded" % len(player_stats))
    skater_stats = list(filter(lambda ps: ps['position'] != 'GK', player_stats))
    print("+ Retained %d skater stats items" % len(skater_stats))
    goalie_stats = json.loads(open(src_goalie_stats_path).read())
    print("+ %d goalie stats items loaded" % len(goalie_stats))
    orig_personal_data = json.loads(open(src_personal_data_path).read())[-1]

    personal_data = dict()
    for pd_item in orig_personal_data:
        personal_data[pd_item['player_id']] = pd_item

    all_stats = skater_stats + goalie_stats

    # collecting top and bottom game scores
    top_game_scores, bottom_game_scores = retrieve_top_bottom_game_scores(all_stats, personal_data)

    open(tgt_top_gs_path, 'w').write(json.dumps(top_game_scores, indent=2))
    open(tgt_bottom_gs_path, 'w').write(json.dumps(bottom_game_scores, indent=2))
