#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
import json

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))
PLAYER_GAME_STATS_SRC = 'del_player_game_stats.json'

season = 2019

if __name__ == '__main__':

    events_src_dir = os.path.join(
        CONFIG['base_data_dir'], 'game_events', str(season))
    game_info_src_dir = os.path.join(
        CONFIG['base_data_dir'], 'game_info', str(season), str(1))
    player_stats_src_path = os.path.join(
        CONFIG['tgt_processing_dir'], str(season), PLAYER_GAME_STATS_SRC)

    player_stats = json.loads(open(player_stats_src_path).read())[-1]

    print(len(player_stats))

    goals = list()

    for src_dir, _, fnames in os.walk(events_src_dir):
        for fname in fnames[26:27]:
            game_id = int(fname.replace(".json", ""))

            game_info_src_path = os.path.join(game_info_src_dir, fname)
            game_info = json.loads(open(game_info_src_path).read())

            print(game_info['teamInfo'])

            src_path = os.path.join(src_dir, fname)
            # print(game_id, src_path)

            periods = json.loads(open(src_path).read())

            for period in sorted(periods):
                for event in periods[period]:
                    if event['type'] == 'goal':
                        goals.append(event)

    # for goal in goals:
    #     print(goal)
