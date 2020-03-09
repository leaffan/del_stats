#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import argparse

CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

ROUND_MAPPING = {
    '1. Playoff-Runde': 'first_round',
    'Viertelfinale': 'quarter_finals',
    'Halbfinale': 'semi_finals',
    'Finale': 'finals'
}


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Order DEL team schedules.')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, type=int,
        metavar='season to order schedules for', default=2019,
        choices=[2016, 2017, 2018, 2019],
        help="The season for which team schedules will be ordered")

    args = parser.parse_args()
    seasons = [args.season]

    teams = CONFIG['teams']
    game_types = CONFIG['game_types']

    games = list()
    game_ids = set()

    for season in seasons:
        for game_type in game_types:
            print("+ Aggregating schedules for %s season %d-%d" % (
                game_types[game_type], season, season + 1))
            for team_id in teams:
                team_schedule_src_path = os.path.join(
                    CONFIG['base_data_dir'], 'schedules', str(season),
                    str(game_type), "%d.json" % team_id)
                if not os.path.isfile(team_schedule_src_path):
                    continue
                team_schedule = json.loads(open(team_schedule_src_path).read())
                for game in team_schedule['matches']:
                    if not game['id'] in game_ids:
                        game_ids.add(game['id'])
                        game['game_id'] = game['id']
                        if not game['round'].isdigit():
                            rnd_type, rnd = game['round'].rsplit(maxsplit=1)
                            rnd_type = ROUND_MAPPING[rnd_type]
                            game['round'] = "_".join((rnd_type, rnd))
                        del(game['id'])
                        games.append(game)

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))
    if not os.path.isdir(tgt_dir):
        os.makedirs(tgt_dir)
    tgt_path = os.path.join(tgt_dir, 'full_schedule.json')

    open(tgt_path, 'w').write(json.dumps(games, indent=2))
