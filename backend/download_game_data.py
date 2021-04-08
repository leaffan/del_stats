#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import yaml
import requests
import argparse

from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_download_targets(args, config):
    '''
    Determines download target season(s) and game type(s) from specified
    command line arguments and previously loaded configuration.
    '''
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
        game_types = {
            k: v for (k, v) in config['game_types'].items() if
            v == tgt_game_type
        }

    return seasons, game_types


def get_game_ids_dates_and_teams(schedule_dir, season='', game_type='', team=''):
    '''
    Retrieves ids for games to be downloaded from specified schedule directory,
    season, game type, and team. If either one of the latter parameters is not
    set game data for all seasons, game types, and/or teams is marked to be
    downloaded. Additionally retrieves ids of teams involved in each game.
    '''
    game_ids_team_ids = defaultdict(set)
    game_dates = dict()

    for dirpath, _, filenames in os.walk(schedule_dir):
        # checking for specified season
        if season and str(season) not in dirpath:
            continue
        # checking for specified game type
        if game_type and not dirpath.endswith(str(game_type)):
            continue

        if filenames:
            for schedule_file in filenames:
                # checking for specified team
                if team and os.path.splitext(schedule_file)[0] != str(team):
                    continue
                src_path = os.path.join(dirpath, schedule_file)
                schedule = json.loads(open(src_path).read())['matches']
                for game in schedule:
                    if game['status'] == 'AFTER_MATCH':
                        game_ids_team_ids[game['id']].add(game['home']['id'])
                        game_ids_team_ids[game['id']].add(game['guest']['id'])
                        game_dates[game['id']] = game['start_date']

    return game_ids_team_ids, game_dates


def download_task(tgt_url, alt_url, tgt_path, last_modified_dict):
    '''
    Represents single task to download data from speficied target url to
    specified target path using information from dictionary of last
    modification timestamps.
    '''
    # setting up customized header if target file already exists and a
    # timestamp of last modification has been saved previously
    req_header = dict()
    if tgt_url in last_modified_dict and os.path.isfile(tgt_path):
        req_header['If-Modified-Since'] = last_modified_dict[tgt_url]

    # retrieving target data using customized header
    try:
        r = requests.get(tgt_url, headers=req_header)
        if r.status_code == 200:
            data = r.json()
            sys.stdout.write('+')
            sys.stdout.flush()
        # data has not been modified since last visit
        elif r.status_code == 304:
            sys.stdout.write('.')
            sys.stdout.flush()
            return tgt_url, None
        # data not available, i.e. playoff stats for
        # non-playoff teams
        elif r.status_code == 404:
            if alt_url:
                time.sleep(0.2)
                rr = requests.get(alt_url, headers=req_header)
                if rr.status_code == 200:
                    data = rr.json()
                    sys.stdout.write('+')
                    sys.stdout.flush()
                # data has not been modified since last visit
                elif rr.status_code == 304:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    return alt_url, None
                elif rr.status_code == 404:
                    sys.stdout.write('O')
                    sys.stdout.flush()
                    return alt_url, None
            else:
                sys.stdout.write('X')
                sys.stdout.flush()
                return tgt_url, None
    except json.decoder.JSONDecodeError:
        print("Unable to retrieve JSON data from %s" % tgt_url)
        return

    open(tgt_path, 'w').write(json.dumps(data, indent=2))

    # retrieving date of last modification
    if r.status_code == 200:
        last_modified = r.headers.get('Last-Modified')
    else:
        last_modified = rr.headers.get('Last-Modified')

    time.sleep(0.2)

    return tgt_url, last_modified


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Download DEL game information.')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, type=int,
        metavar='season to download data for', default=2020,
        choices=[2016, 2017, 2018, 2019, 2020],
        help="The season for which information will be downloaded for")
    parser.add_argument(
        '-g', '--game_type', dest='game_type', required=False,
        metavar='game type to download data for', choices=['RS', 'PO', 'MSC', 'ALL'],
        help="The game type for which information will be downloaded for")
    parser.add_argument(
        'category', metavar='information category',
        help='information category to be downloaded',
        choices=[
            'game_info', 'game_events', 'game_roster', 'game_team_stats',
            'game_goalies', 'shifts', 'game_player_stats', 'shots', 'faceoffs'
        ])

    # loading external configuration
    config = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

    args = parser.parse_args()
    seasons, game_types = get_download_targets(args, config)
    print("+ Downloading %s data" % args.category)

    base_url = config['base_url']
    del_base_url = config['del_base_url']
    tgt_base_dir = config['tgt_base_dir']
    tgt_sub_dir = args.category
    target_url_component = config['url_components'][args.category]

    if args.category == 'shots':
        print("+ Using DEL base url %s" % del_base_url)
    else:
        print("+ Using base url %s" % base_url)

    schedule_src_dir = os.path.join(tgt_base_dir, 'schedules')

    # retrieving or setting up dictionary with dates of last modification
    last_modified_path = os.path.join(tgt_base_dir, 'last_modified.json')
    if os.path.isfile(last_modified_path):
        last_modified_dict = json.loads(open(last_modified_path).read())
    else:
        last_modified_dict = dict()

    for season in seasons:
        for game_type in game_types:

            # setting up target directory and path
            tgt_dir = os.path.join(tgt_base_dir, tgt_sub_dir, str(season), str(game_type))

            print(
                "+ Downloading %s data for %s games in %d-%d" % (
                    args.category, config['game_types'][game_type], season, season + 1))

            download_tasks = list()

            # retrieving games, game dates and teams involved for current season and game type
            games_and_teams, game_dates = get_game_ids_dates_and_teams(schedule_src_dir, season, game_type)

            for game_id in games_and_teams:
                # game player stats are divided in two files for each of the
                # involved teams
                if args.category in ['game_player_stats', 'game_team_stats']:
                    current_team = 'home'
                    for team_id in games_and_teams[game_id]:
                        # setting up target url
                        if args.category == 'game_player_stats':
                            target_url = R"/".join((
                                base_url, 'matches', str(game_id),
                                target_url_component, "%s.json" % team_id))
                            alt_url = ''
                        elif args.category == 'game_team_stats':
                            target_url = R"/".join((
                                base_url, 'match-detail', target_url_component,
                                str(game_id), "%s.json" % team_id))
                            alt_url = R"/".join((
                                del_base_url, 'live-ticker', 'matches',
                                str(game_id), "team-stats-%s.json" % current_team))
                        current_team = 'guest'

                        tgt_path = os.path.join(tgt_dir, "%d_%d.json" % (game_id, team_id))
                        download_tasks.append((target_url, alt_url, tgt_path))
                # regular game stats are stored in a single file for each game
                else:
                    if args.category in ['shifts']:
                        # shift data files after a certain cutoff date need special treatment
                        game_date = datetime.strptime(game_dates[game_id], '%Y-%m-%d %H:%M:%S').date()
                        suffix_valid_from_date = datetime.strptime(config['url_suffix_valid_from'], '%Y-%m-%d').date()
                        if game_date >= suffix_valid_from_date:
                            target_url = R"/".join((
                                base_url, 'matches', str(game_id),
                                "%s%s.json" % (target_url_component, config['url_suffix'])))
                        else:
                            target_url = R"/".join((
                                base_url, 'matches', str(game_id), "%s.json" % target_url_component))
                        alt_url = ''
                    elif args.category in ['shots']:
                        # setting up target url
                        target_url = R"/".join((base_url, 'visualization', 'shots', "%d.json" % game_id))
                        alt_url = R"/".join((del_base_url, target_url_component, "%d.json" % game_id))
                    else:
                        # setting up target url
                        target_url = R"/".join((
                            base_url, 'matches', str(game_id),
                            "%s.json" % target_url_component))
                        if args.category in ['game_goalies', 'faceoffs']:
                            alt_url = ''
                        else:
                            alt_url = R"/".join((
                                del_base_url, 'live-ticker', 'matches', str(game_id), "%s.json" % target_url_component))

                    tgt_path = os.path.join(tgt_dir, "%d.json" % game_id)
                    download_tasks.append((target_url, alt_url, tgt_path))

            # creating target directory (if necessary)
            if download_tasks:
                if not os.path.isdir(tgt_dir):
                    os.makedirs(tgt_dir)

            # downloading data concurrently
            with ThreadPoolExecutor(max_workers=4) as threads:
                tasks = {
                    threads.submit(
                        download_task, tgt_url, alt_url, tgt_path, last_modified_dict
                    ): (
                        tgt_url, alt_url, tgt_path
                    ) for tgt_url, alt_url, tgt_path in download_tasks[:]
                }
                for completed_task in as_completed(tasks):
                    if completed_task.result():
                        tgt_url, last_modified = completed_task.result()
                        if last_modified:
                            last_modified_dict[tgt_url] = last_modified
            print()

    open(last_modified_path, 'w').write(json.dumps(last_modified_dict, indent=2))
