#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import json
import yaml

from operator import itemgetter

# loading configuration from external file
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

SRC_DIR = os.path.join(CONFIG['base_data_dir'], 'archive', 'player_games')

TGT_DIR = SRC_DIR

if __name__ == '__main__':

    src_files = os.listdir(SRC_DIR)

    pp_goals_per_player = list()

    for f in src_files[:]:

        if not f.endswith(".json"):
            continue

        src_path = os.path.join(SRC_DIR, f)
        plr_games = json.loads(open(src_path).read())

        if not plr_games:
            continue

        plr_name = plr_games[0]['player_name']
        # print("+ Summing up power play goals for %s" % plr_name)

        pp_goals = sum(
            plr_game['ppg'] for
            plr_game in plr_games if plr_game['season'] != 2019)
        games = sum(1 for plr_game in plr_games if plr_game['season'] != 2019)

        if plr_name == 'Patrick Reimer':
            seasons = sorted(set([(
                plr_game['season'],
                plr_game['season_type']) for plr_game in plr_games]))
            print(seasons)
            for season, season_type in seasons:
                if season == 2019:
                    continue
                games_per_season = list(
                    filter(
                        lambda d: d['season'] == season and
                        d['season_type'] == season_type, plr_games))
                pp_goals_per_season = sum(
                    plr_game['ppg'] for plr_game in games_per_season)
                print(
                    season, season_type,
                    len(games_per_season), pp_goals_per_season)
        pp_goals_per_player.append((plr_name, games, pp_goals))

    # print(pp_goals_per_player)

    pp_goals_per_player = sorted(
        pp_goals_per_player, key=itemgetter(1), reverse=False)
    pp_goals_per_player.sort(key=itemgetter(2), reverse=True)

    # print(pp_goals_per_player)

    tgt_csv_path = os.path.join(TGT_DIR, '_pp_goal_scorers.csv')

    with open(tgt_csv_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        csv_out = csv.writer(output_file, delimiter=';', lineterminator='\n')
        csv_out.writerow(['name', 'games', 'pp_goals'])
        for row in pp_goals_per_player:
            csv_out.writerow(row)
