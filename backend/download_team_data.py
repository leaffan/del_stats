#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import yaml
import requests
import argparse

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

def get_download_targets(args, config):
    """
    Retrieves seasons, game types and teams to download data for.
    """
    # setting target team(s)
    tgt_team = args.team
    if not tgt_team:
        teams = config['teams']
    else:
        teams = {k: v for (k, v) in config['teams'].items() if v == tgt_team}
    # setting target season(s)
    tgt_season = args.season
    if not tgt_season:
        seasons = config['seasons']
    else:
        seasons = [tgt_season]
    # setting target game type(s)
    tgt_game_type = args.game_type
    if not tgt_game_type or tgt_game_type == 'ALL':
        game_types = list(config['game_types'].keys())
    else:
        game_types = {k: v for (k, v) in config['game_types'].items() if v == tgt_game_type}

    return seasons, game_types, teams


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(description='Download DEL team information.')
    parser.add_argument(
        '-t', '--team', dest='team', required=False, metavar='team to download data for',
        choices=list(CONFIG['teams'].values()),
        help="The team for which information will be downloaded for")
    parser.add_argument(
        '-s', '--season', dest='season', required=False, type=int, metavar='season to download data for',
        default=CONFIG['default_season'], choices=CONFIG['seasons'],
        help="The season for which information will be downloaded for")
    parser.add_argument(
        '-g', '--game_type', dest='game_type', required=False, metavar='game type to download data for',
        choices=list(CONFIG['game_types'].values()) + ['ALL'],
        help="The game type for which information will be downloaded for")
    parser.add_argument(
        'category', metavar='information category',
        choices=['schedules', 'team_stats', 'roster_stats'],
        help='information category to be downloaded')

    args = parser.parse_args()
    seasons, game_types, teams = get_download_targets(args, CONFIG)
    print("+ Downloading %s data" % args.category)
    print("+ Using base url %s" % CONFIG['base_url'])

    # retrieving configuration
    base_url = CONFIG['base_url']
    tgt_base_dir = CONFIG['tgt_base_dir']
    tgt_sub_dir = args.category
    tgt_url_component = CONFIG['url_components'][args.category]

    # retrieving or setting up dictionary with dates of last modification
    last_modified_path = os.path.join(tgt_base_dir, 'last_modified.json')
    if os.path.isfile(last_modified_path):
        last_modified_dict = json.loads(open(last_modified_path).read())
    else:
        last_modified_dict = dict()

    for season in seasons:
        print("+ Downloading %s for %d-%d" % (args.category, season, season + 1))
        for team_id in teams:
            sys.stdout.write("%s:" % teams[team_id])
            sys.stdout.flush()
            for game_type in game_types:
                # setting up target url
                tgt_url = R"/".join((base_url, tgt_url_component, str(season), str(game_type), "%d.json" % team_id))

                # setting up target directory and path
                tgt_dir = os.path.join(tgt_base_dir, tgt_sub_dir, str(season), str(game_type))
                if not os.path.isdir(tgt_dir):
                    os.makedirs(tgt_dir)
                tgt_path = os.path.join(tgt_dir, "%d.json" % team_id)

                # setting up customized header
                req_header = dict()
                if os.path.isfile(tgt_path) and tgt_url in last_modified_dict:
                    req_header['If-Modified-Since'] = last_modified_dict[tgt_url]

                # retrieving target data using customized header
                try:
                    r = requests.get(tgt_url, headers=req_header)
                    # downloading new or modified data
                    if r.status_code == 200:
                        data = r.json()
                        sys.stdout.write('+')
                        sys.stdout.flush()
                    # data has not been modified since last visit
                    elif r.status_code == 304:
                        sys.stdout.write('.')
                        sys.stdout.flush()
                        continue
                    # data not available, i.e. playoff stats for non-playoff teams
                    elif r.status_code == 404:
                        sys.stdout.write('X')
                        sys.stdout.flush()
                        continue
                except json.decoder.JSONDecodeError:
                    print("Unable to retrieve JSON data from %s" % tgt_url)
                    continue

                # sorting roster stats by player id in order to allow for data versioning
                if args.category == 'roster_stats':
                    data = sorted(data, key=lambda k: k['id'])

                # writing downloaded data
                open(tgt_path, 'w').write(json.dumps(data, indent=2))

                # retrieving date of last modification
                last_modified = r.headers['Last-Modified']
                last_modified_dict[tgt_url] = last_modified
                time.sleep(0.1)
            sys.stdout.write(' ')
        print()

    # re-writing dictionary with timestamp of last modification of source files
    open(last_modified_path, 'w').write(json.dumps(last_modified_dict, indent=2))
