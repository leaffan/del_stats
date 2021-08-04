#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import argparse

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

ROUND_MAPPING = {
    '1. Playoff-Runde': 'first_round',
    'Viertelfinale': 'quarter_finals',
    'Halbfinale': 'semi_finals',
    'Finale': 'finals',
    # MSC rounds:
    'Halbfinale 1': 'semi_finals',
    'Halbfinale 2': 'semi_finals',
}


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(description='Order DEL team schedules.')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, type=int, metavar='season to order schedules for',
        default=CONFIG['default_season'], choices=CONFIG['seasons'],
        help="The season for which team schedules will be ordered")

    args = parser.parse_args()
    seasons = [args.season]

    teams = CONFIG['teams']
    game_types = CONFIG['game_types']

    games = list()
    game_ids = set()

    for season in seasons:
        for game_type in game_types:
            # skipping MagentaSport Cup 2020
            # if season == 2020 and game_type == 4:
            #     continue
            print("+ Aggregating schedules for %s season %d-%d" % (game_types[game_type], season, season + 1))
            for team_id in teams:
                team_schedule_src_path = os.path.join(
                    CONFIG['base_data_dir'], 'schedules', str(season), str(game_type), "%d.json" % team_id)
                if not os.path.isfile(team_schedule_src_path):
                    continue
                team_schedule = json.loads(open(team_schedule_src_path).read())
                for game in team_schedule['matches']:
                    if not game['id'] in game_ids:
                        game_ids.add(game['id'])
                        game['game_id'] = game['id']
                        # setting round for non-regular season games
                        if game['round'] and not game['round'].isdigit():
                            try:
                                rnd_type, rnd = game['round'].rsplit(maxsplit=1)
                                rnd_type = ROUND_MAPPING[rnd_type]
                                game['round'] = "_".join((rnd_type, rnd))
                            except ValueError:
                                rnd_type = ROUND_MAPPING[game['round']]
                                game['round'] = "rnd_type_%d" % 1
                        del(game['id'])
                        games.append(game)

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))
    if not os.path.isdir(tgt_dir):
        os.makedirs(tgt_dir)
    tgt_path = os.path.join(tgt_dir, 'full_schedule.json')

    open(tgt_path, 'w').write(json.dumps(games, indent=2))
