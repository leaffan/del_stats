#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Retrieves player games with more than three goals
# scored from downloaded player game data in archive.

import os
import csv
import json
import yaml


# loading configuration from external file
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

SRC_DIR = os.path.join(CONFIG['base_data_dir'], 'archive', 'player_games')

TGT_DIR = SRC_DIR

if __name__ == '__main__':

    src_files = os.listdir(SRC_DIR)

    multi_goal_games = list()

    for f in src_files[:]:

        if not f.endswith(".json"):
            continue

        src_path = os.path.join(SRC_DIR, f)
        plr_games = json.loads(open(src_path).read())

        for plr_game in plr_games:
            if plr_game['goals'] >= 4:
                multi_goal_games.append(plr_game)

    tgt_csv_path = os.path.join(TGT_DIR, '_four_plus_goal_games.csv')

    out_fields = list(multi_goal_games[0].keys())

    with open(tgt_csv_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        dict_writer = csv.DictWriter(
            output_file, out_fields, delimiter=';', lineterminator='\n',
            extrasaction='ignore')
        dict_writer.writeheader()
        dict_writer.writerows(multi_goal_games)
