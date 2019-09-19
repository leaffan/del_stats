#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import yaml
import requests
import argparse


def get_download_targets(args, config):
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
    if not tgt_game_type:
        game_types = list(config['game_types'].keys())
    else:
        game_types = {
            k: v for (k, v) in config['game_types'].items() if
            v == tgt_game_type
        }

    return seasons, game_types, teams


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Download DEL team information.')
    parser.add_argument(
        '-t', '--team', dest='team', required=False,
        metavar='team to download data for',
        choices=[
            'ING', 'MAN', 'EBB', 'DEG', 'KEV', 'STR', 'IEC',
            'WOB', 'BHV', 'KEC', 'RBM', 'AEV', 'NIT', 'SWW'],
        help="The team for which information will be downloaded for")
    parser.add_argument(
        '-s', '--season', dest='season', required=False, type=int,
        metavar='season to download data for',
        choices=[2016, 2017, 2018, 2019],
        help="The season for which information will be downloaded for")
    parser.add_argument(
        '-g', '--game_type', dest='game_type', required=False,
        metavar='game type to download data for', choices=['RS', 'PO'],
        help="The game type for which information will be downloaded for")
    parser.add_argument(
        'category', metavar='information category',
        help='information category to be downloaded',
        choices=['schedules', 'team_stats', 'roster_stats'])

    # loading external configuration
    config = yaml.safe_load(open(os.path.join(
        os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

    args = parser.parse_args()
    seasons, game_types, teams = get_download_targets(args, config)
    print("+ Downloading %s data" % args.category)
    print("+ Using base url %s" % config['base_url'])

    # retrieving configuration
    base_url = config['base_url']
    tgt_base_dir = config['tgt_base_dir']
    tgt_sub_dir = args.category
    target_url_component = config['url_components'][args.category]

    # retrieving or setting up dictionary with dates of last modification
    last_modified_path = os.path.join(tgt_base_dir, 'last_modified.json')
    if os.path.isfile(last_modified_path):
        last_modified_dict = json.loads(open(last_modified_path).read())
    else:
        last_modified_dict = dict()

    for season in seasons:
        print(
            "+ Downloading %s for %d-%d" % (args.category, season, season + 1))
        for team_id in teams:
            sys.stdout.write(teams[team_id])
            sys.stdout.flush()
            for game_type in game_types:
                # setting up target url
                target_url = R"/".join((
                    base_url, target_url_component,
                    str(season), str(game_type), "%d.json" % team_id))

                # setting up target directory and path
                tgt_dir = os.path.join(
                    tgt_base_dir, tgt_sub_dir, str(season), str(game_type))
                if not os.path.isdir(tgt_dir):
                    os.makedirs(tgt_dir)
                tgt_path = os.path.join(tgt_dir, "%d.json" % team_id)

                # setting up customized header
                req_header = dict()
                if (
                    os.path.isfile(tgt_path) and
                    target_url in last_modified_dict
                ):
                    req_header['If-Modified-Since'] = last_modified_dict[
                        target_url]

                # retrieving target data using customized header
                try:
                    r = requests.get(target_url, headers=req_header)
                    if r.status_code == 200:
                        data = r.json()
                        sys.stdout.write('+')
                        sys.stdout.flush()
                    # data has not been modified since last visit
                    elif r.status_code == 304:
                        sys.stdout.write('.')
                        sys.stdout.flush()
                        continue
                    # data not available, i.e. playoff stats for non-playoff
                    # teams
                    elif r.status_code == 404:
                        sys.stdout.write('X')
                        sys.stdout.flush()
                        continue
                except json.decoder.JSONDecodeError:
                    print(
                        "Unable to retrieve JSON data from %s" % target_url)
                    continue

                if args.category == 'roster_stats':
                    data = sorted(data, key=lambda k: k['id'])

                open(tgt_path, 'w').write(json.dumps(data, indent=2))

                # retrieving date of last modification
                last_modified = r.headers['Last-Modified']
                last_modified_dict[target_url] = last_modified
            sys.stdout.write(' ')
        print()

    open(last_modified_path, 'w').write(
        json.dumps(last_modified_dict, indent=2))
