#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import json
import yaml

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))


SRC_DATA_DIR = "data"
SRC_GAME_STATS_FILE = "del_games.json"
SRC_SKATER_STATS_FILE = "del_player_game_stats.json"
SRC_GOALIE_STATS_FILE = "del_goalie_game_stats.json"


def load_data(season):

    src_dir = os.path.join(SRC_DATA_DIR, str(season))
    skater_src_file = os.path.join(src_dir, SRC_SKATER_STATS_FILE)
    goalie_src_file = os.path.join(src_dir, SRC_GOALIE_STATS_FILE)
    games_src_file = os.path.join(src_dir, SRC_GAME_STATS_FILE)

    skater_stats = json.loads(open(skater_src_file).read())[-1]
    skater_stats = list(filter(lambda d: d['position'] != 'GK', skater_stats))
    goalie_stats = json.loads(open(goalie_src_file).read())

    games = json.loads(open(games_src_file).read())

    return skater_stats, goalie_stats, games


if __name__ == '__main__':

    all_stats = list()
    all_games_list = list()

    for season in [2018, 2019]:
        skater_stats, goalie_stats, games = load_data(season)
        all_stats += skater_stats
        all_stats += goalie_stats
        all_games_list += games

    all_games = dict()
    for game in all_games_list:
        all_games[game['game_id']] = game

    sorted_all_stats = sorted(
        all_stats, key=lambda d: d['game_score'], reverse=True)

    output = list()

    for stat in sorted_all_stats[:]:
        out_dict = dict()
        out_dict['game_date'] = stat['game_date']
        out_dict['full_name'] = " ".join(
            [stat['first_name'], stat['last_name']])
        out_dict['team'] = stat['team']
        out_dict['opp_team'] = stat['opp_team']
        out_dict['score'] = stat['score']
        out_dict['opp_score'] = stat['opp_score']
        out_dict['result'] = (
            "-".join([str(x) for x in [stat['score'], stat['opp_score']]]))
        if all_games[stat['game_id']]['shootout_game']:
            out_dict['result'] += ' (SO)'
        elif all_games[stat['game_id']]['overtime_game']:
            out_dict['result'] += ' (OT)'
        out_dict['result'] = "xxx" + out_dict['result']
        if 'position' in stat:
            out_dict['position'] = stat['position']
            out_dict['goals'] = stat['goals']
            out_dict['primary_assists'] = stat['primary_assists']
            out_dict['secondary_assists'] = stat['secondary_assists']
            out_dict['shots_on_goal'] = stat['shots_on_goal']
            out_dict['blocked_shots'] = stat['blocked_shots']
            out_dict['toi'] = stat['time_on_ice']
            out_dict['on_ice_shots_diff'] = (
                stat['on_ice_sh_f'] - stat['on_ice_sh_a'])
            out_dict['on_ice_goals_diff'] = (
                stat['on_ice_goals_f'] - stat['on_ice_goals_a'])
            out_dict['faceoffs_diff'] = (
                stat['faceoffs_won'] - stat['faceoffs_lost'])
        else:
            out_dict['position'] = 'GK'
            out_dict['goals'] = stat['goals_against']
            out_dict['primary_assists'] = None
            out_dict['secondary_assists'] = None
            out_dict['shots_on_goal'] = stat['shots_against']
            out_dict['blocked_shots'] = None
            out_dict['toi'] = stat['toi']
            out_dict['on_ice_shots_diff'] = None
            out_dict['on_ice_goals_diff'] = None
            out_dict['faceoffs_diff'] = None

        out_dict['game_score'] = "xxx" + str(stat['game_score'])

        output.append(out_dict)

    out_fields = list(out_dict.keys())

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'])
    tgt_csv_path = os.path.join(tgt_dir, "sorted_game_scores.csv")
    with open(tgt_csv_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        dict_writer = csv.DictWriter(
            output_file, out_fields, delimiter=';', lineterminator='\n',
            extrasaction='ignore')
        dict_writer.writeheader()
        dict_writer.writerows(output)
