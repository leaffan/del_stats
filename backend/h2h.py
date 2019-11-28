#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import csv
import json
import yaml

from collections import defaultdict

# Make sure team abbreviation MUC/team id 19 is set to RBM/14 for 2010/11
# playoff games in game data source file.

# loading configuration from external file
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

SEASON_FILE_REGEX = re.compile(R"(\d{4})\.json")

TEAM_ABBRS_BY_ID = {
    1: 'KEC', 2: 'WOB', 3: 'HHF', 4: 'EBB', 5: 'KEV', 6: 'IEC', 7: 'DEG',
    8: 'MAN', 9: 'NIT', 10: 'ING', 11: 'STR', 12: 'AEV', 13: 'SWW', 14: 'RBM',
    15: 'HAN', 16: 'SBR', 17: 'KAS', 18: 'FRA', 19: 'MUC', 20: 'CAP',
    21: 'RLO', 22: 'MOS', 24: 'WFR', 25: 'ECH', 26: 'ESV', 27: 'EVL',
    28: 'MAD', 29: 'ECR', 30: 'ESG', 31: 'SCR', 32: 'ERD', 33: 'NEU',
    34: 'DUI', 35: 'BHV',
}
TEAM_IDS_BY_ABBR = {abbr: t_id for t_id, abbr in TEAM_ABBRS_BY_ID.items()}

CURRENT_TEAMS = [
    'AEV', 'EBB', 'BHV', 'DEG', 'ING', 'IEC', 'KEC',
    'KEV', 'MAN', 'RBM', 'NIT', 'SWW', 'STR', 'WOB']

PO_SEASON_TYPES = ['PO-Qualifikation', 'Playoffs', 'Playdowns']

h2h = defaultdict(dict)

if __name__ == '__main__':

    season_files = os.listdir(os.path.join(CONFIG['base_data_dir'], 'archive'))
    season_types = set()

    h2h = dict()

    for season_file in season_files[:]:
        match = re.search(SEASON_FILE_REGEX, season_file)
        if not match:
            continue
        season_path = os.path.join(
            CONFIG['base_data_dir'], 'archive', season_file)
        season_games = json.loads(open(season_path).read())

        print(
            "+ Processing %d games from the %s/%d season" % (
                len(season_games), match.group(1), int(match.group(1)) + 1))

        for game in season_games[:]:
            season_type = game['season_type']
            home = game['home_abbr']
            road = game['road_abbr']

            categories = [
                'games_played', 'wins', 'losses', 'ties',
                'ot_games_played', 'ot_wins', 'ot_losses', 'ot_ties',
                'so_games_played', 'so_wins', 'so_losses',
                'po_games_played', 'po_wins', 'po_losses', 'po_ot_ties',
                'po_ot_games_played', 'po_ot_wins', 'po_ot_losses',
                'po_so_games_played', 'po_so_wins', 'po_so_losses',
                'goals_for', 'goals_against'
            ]

            # setting up head-to-head-configuration (if necessary)
            if home not in h2h:
                h2h[home] = dict()
            if road not in h2h[home]:
                h2h[home][road] = dict()
                h2h[home][road]['home'] = dict()
                h2h[home][road]['road'] = dict()
                for category in categories:
                    h2h[home][road]['home'][category] = 0
                    h2h[home][road]['road'][category] = 0
            if road not in h2h:
                h2h[road] = dict()
            if home not in h2h[road]:
                h2h[road][home] = dict()
                h2h[road][home]['home'] = dict()
                h2h[road][home]['road'] = dict()
                for category in categories:
                    h2h[road][home]['home'][category] = 0
                    h2h[road][home]['road'][category] = 0

            # registering game
            h2h[home][road]['home']['games_played'] += 1
            h2h[road][home]['road']['games_played'] += 1
            if game['overtime']:
                h2h[home][road]['home']['ot_games_played'] += 1
                h2h[road][home]['road']['ot_games_played'] += 1
            if game['shootout']:
                h2h[home][road]['home']['so_games_played'] += 1
                h2h[road][home]['road']['so_games_played'] += 1
            # registering game as playoff game (if applicable)
            if season_type in PO_SEASON_TYPES:
                h2h[home][road]['home']['po_games_played'] += 1
                h2h[road][home]['road']['po_games_played'] += 1
                if game['overtime']:
                    h2h[home][road]['home']['po_ot_games_played'] += 1
                    h2h[road][home]['road']['po_ot_games_played'] += 1
                if game['shootout']:
                    h2h[home][road]['home']['po_so_games_played'] += 1
                    h2h[road][home]['road']['po_so_games_played'] += 1

            # registering scores as goals for/against
            h2h[home][road]['home']['goals_for'] += game['home_score']
            h2h[home][road]['home']['goals_against'] += game['road_score']
            h2h[road][home]['road']['goals_for'] += game['road_score']
            h2h[road][home]['road']['goals_against'] += game['home_score']

            # registering game outcome
            if game['home_score'] == game['road_score']:
                h2h[home][road]['home']['ties'] += 1
                h2h[road][home]['road']['ties'] += 1
                if game['overtime']:
                    h2h[home][road]['home']['ot_ties'] += 1
                    h2h[road][home]['road']['ot_ties'] += 1
            elif game['home_score'] > game['road_score']:
                h2h[home][road]['home']['wins'] += 1
                h2h[road][home]['road']['losses'] += 1
                if game['shootout']:
                    h2h[home][road]['home']['so_wins'] += 1
                    h2h[road][home]['road']['so_losses'] += 1
                    h2h[home][road]['home']['ot_ties'] += 1
                    h2h[road][home]['road']['ot_ties'] += 1
                elif game['overtime']:
                    h2h[home][road]['home']['ot_wins'] += 1
                    h2h[road][home]['road']['ot_losses'] += 1
                if season_type in PO_SEASON_TYPES:
                    h2h[home][road]['home']['po_wins'] += 1
                    h2h[road][home]['road']['po_losses'] += 1
                    if game['shootout']:
                        h2h[home][road]['home']['po_so_wins'] += 1
                        h2h[road][home]['road']['po_so_losses'] += 1
                        h2h[home][road]['home']['po_ot_ties'] += 1
                        h2h[road][home]['road']['po_ot_ties'] += 1
                    elif game['overtime']:
                        h2h[home][road]['home']['po_ot_wins'] += 1
                        h2h[road][home]['road']['po_ot_losses'] += 1
            elif game['home_score'] < game['road_score']:
                h2h[home][road]['home']['losses'] += 1
                h2h[road][home]['road']['wins'] += 1
                if game['shootout']:
                    h2h[home][road]['home']['so_losses'] += 1
                    h2h[road][home]['road']['so_wins'] += 1
                    h2h[home][road]['home']['ot_ties'] += 1
                    h2h[road][home]['road']['ot_ties'] += 1
                elif game['overtime']:
                    h2h[home][road]['home']['ot_losses'] += 1
                    h2h[road][home]['road']['ot_wins'] += 1
                if season_type in PO_SEASON_TYPES:
                    h2h[home][road]['home']['po_losses'] += 1
                    h2h[road][home]['road']['po_wins'] += 1
                    if game['shootout']:
                        h2h[home][road]['home']['po_so_wins'] += 1
                        h2h[road][home]['road']['po_so_losses'] += 1
                        h2h[home][road]['home']['po_ot_ties'] += 1
                        h2h[road][home]['road']['po_ot_ties'] += 1
                    elif game['overtime']:
                        h2h[home][road]['home']['po_ot_losses'] += 1
                        h2h[road][home]['road']['po_ot_wins'] += 1

    # calculating winning percentages
    for key in h2h:
        for opp_key in h2h[key]:
            if h2h[key][opp_key]['home']['games_played']:
                h2h[key][opp_key]['home']['win_pctg'] = round(
                    h2h[key][opp_key]['home']['wins'] /
                    h2h[key][opp_key]['home']['games_played'] * 100, 2)
            else:
                h2h[key][opp_key]['home']['win_pctg'] = 0.
            if h2h[key][opp_key]['road']['games_played']:
                h2h[key][opp_key]['road']['win_pctg'] = round(
                    h2h[key][opp_key]['road']['wins'] /
                    h2h[key][opp_key]['road']['games_played'] * 100, 2)
            else:
                h2h[key][opp_key]['road']['win_pctg'] = 0.
            h2h[key][opp_key]['overall'] = dict()
            for category in categories:
                h2h[key][opp_key]['overall'][category] = (
                    h2h[key][opp_key]['home'][category] +
                    h2h[key][opp_key]['road'][category]
                )
            if h2h[key][opp_key]['overall']['games_played']:
                h2h[key][opp_key]['overall']['win_pctg'] = round(
                    h2h[key][opp_key]['overall']['wins'] /
                    h2h[key][opp_key]['overall']['games_played'] * 100, 2)
            else:
                h2h[key][opp_key]['overall']['win_pctg'] = 0.

    # preparing h2h dataset for current DEL teams suitable for usage on
    # extended stats website
    curr_h2h = dict()

    for key in CURRENT_TEAMS:
        curr_h2h[key] = dict()
        for opp_key in CURRENT_TEAMS:
            # teams don't play against themselves
            if opp_key == key:
                continue
            curr_h2h[key][opp_key] = dict()
            for home_road_overall in h2h[key][opp_key]:
                # setting up prefix for final dictionary keys
                prefix = ''
                if home_road_overall == 'home':
                    prefix = 'home_'
                elif home_road_overall == 'road':
                    prefix = 'road_'
                for category in h2h[key][opp_key][home_road_overall]:
                    curr_h2h[key][opp_key]["%s%s" % (prefix, category)] = (
                        h2h[key][opp_key][home_road_overall][category])

    tgt_path = os.path.join(CONFIG['base_data_dir'], 'archive', 'h2h.json')
    open(tgt_path, 'w').write(json.dumps(h2h, indent=2))
    tgt_path = os.path.join(
        CONFIG['tgt_processing_dir'], '2019', 'pre_season_h2h.json')
    open(tgt_path, 'w').write(json.dumps(curr_h2h, indent=2))

    # preparing CSV dataset with h2h records of current DEL teams
    records = list()
    for key in CURRENT_TEAMS:
        for opp_key in CURRENT_TEAMS:
            if key == opp_key:
                continue
            record = dict()
            record['team'] = key
            record['opp_team'] = opp_key
            record['games_played'] = curr_h2h[key][opp_key]['games_played']
            record['wins'] = curr_h2h[key][opp_key]['wins']
            record['ties'] = curr_h2h[key][opp_key]['ties']
            record['losses'] = curr_h2h[key][opp_key]['losses']
            record['games_played_home'] = curr_h2h[key][opp_key][
                'home_games_played']
            record['wins_home'] = curr_h2h[key][opp_key]['home_wins']
            record['ties_home'] = curr_h2h[key][opp_key]['home_ties']
            record['losses_home'] = curr_h2h[key][opp_key]['home_losses']
            record['games_played_road'] = curr_h2h[key][opp_key][
                'road_games_played']
            record['wins_road'] = curr_h2h[key][opp_key]['road_wins']
            record['ties_road'] = curr_h2h[key][opp_key]['road_ties']
            record['losses_road'] = curr_h2h[key][opp_key]['road_losses']

            records.append(record)

    tgt_csv_path = os.path.join(
        CONFIG['base_data_dir'], 'archive', 'h2h.csv')

    OUT_FIELDS = [
        'team', 'opp_team', 'games_played', 'wins', 'ties', 'losses',
        'games_played_home', 'wins_home', 'ties_home', 'losses_home',
        'games_played_road', 'wins_road', 'ties_road', 'losses_road'
    ]

    with open(tgt_csv_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        dict_writer = csv.DictWriter(
            output_file, OUT_FIELDS, delimiter=';', lineterminator='\n',
            extrasaction='ignore')
        dict_writer.writeheader()
        dict_writer.writerows(records)
