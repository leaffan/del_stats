#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Retrieves head-to-head records for games and playoff series from previously
downloaded and processed team games per season.
"""

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
    os.path.dirname(os.path.realpath(__file__)), '..', 'config.yml')))

SEASON_FILE_REGEX = re.compile(R"games_(\d{4})\.json")
# SEASON_FILE_REGEX = re.compile(R"games_(2010)\.json")

# setting lookup table for abbreviations by team id
TEAM_ABBRS_BY_ID = {
    1: 'KEC', 2: 'WOB', 3: 'HHF', 4: 'EBB', 5: 'KEV', 6: 'IEC', 7: 'DEG',
    8: 'MAN', 9: 'NIT', 10: 'ING', 11: 'STR', 12: 'AEV', 13: 'SWW', 14: 'RBM',
    15: 'HAN', 16: 'SBR', 17: 'KAS', 18: 'FRA', 19: 'MUC', 20: 'CAP',
    21: 'RLO', 22: 'MOS', 24: 'WFR', 25: 'ECH', 26: 'ESV', 27: 'EVL',
    28: 'MAD', 29: 'ECR', 30: 'ESG', 31: 'SCR', 32: 'ERD', 33: 'NEU',
    34: 'DUI', 35: 'BHV',
}
# reversing lookup for team ids by abbreviation
TEAM_IDS_BY_ABBR = {abbr: t_id for t_id, abbr in TEAM_ABBRS_BY_ID.items()}

CURRENT_TEAMS = [
    'AEV', 'EBB', 'BHV', 'DEG', 'ING', 'IEC', 'KEC',
    'KEV', 'MAN', 'RBM', 'NIT', 'SWW', 'STR', 'WOB']

# defining play-off-like season types
PO_SEASON_TYPES = ['PO-Qualifikation', 'Playoffs', 'Playdowns']

# setting current season to toggle it as an upper limit for the head-to-head
# records
CURRENT_SEASON = 2019

# setting up categories for head-to-head records
CATEGORIES = [
    'games_played', 'wins', 'losses', 'ties',
    'ot_games_played', 'ot_wins', 'ot_losses', 'ot_ties',
    'so_games_played', 'so_wins', 'so_losses',
    'po_games_played', 'po_wins', 'po_losses', 'po_ot_ties',
    'po_ot_games_played', 'po_ot_wins', 'po_ot_losses',
    'po_so_games_played', 'po_so_wins', 'po_so_losses',
    'goals_for', 'goals_against',
    'goals_for_po', 'goals_against_po',
]


def create_update_playoff_series(h2h_series, series_key, game):
    """
    Creates and/or updates playoff series for given series key using specified
    game data.
    """
    # creating new empty series for specified key (consisting of season,
    # alphabetically sorted abbreviations of both participating teams, and
    # round name, e.g. *2018_MAN_RBM_Finale*)
    if series_key not in h2h_series:
        print(series_key)
        h2h_series[series_key] = dict()
        h2h_series[series_key]['season'] = game['season']
        h2h_series[series_key]['round'] = game['round']
        h2h_series[series_key]['round_type'] = game['round_type']
        h2h_series[series_key]['s_home'] = game['home_abbr']
        h2h_series[series_key]['s_road'] = game['road_abbr']
        h2h_series[series_key]['s_games_played'] = 0
        h2h_series[series_key]['s_home_games_won'] = 0
        h2h_series[series_key]['s_road_games_won'] = 0
        h2h_series[series_key]['s_score'] = "%d-%d" % (
            h2h_series[series_key]['s_home_games_won'],
            h2h_series[series_key]['s_road_games_won'])
        h2h_series[series_key]['s_home_goals'] = 0
        h2h_series[series_key]['s_road_goals'] = 0

    # increasing number of games played in series
    h2h_series[series_key]['s_games_played'] += 1

    # checking whether series home team matches the home team of the game...
    if h2h_series[series_key]['s_home'] == game['home_abbr']:
        # ...and registering stats accordingly
        h2h_series[series_key]['s_home_goals'] += game['home_score']
        h2h_series[series_key]['s_road_goals'] += game['road_score']
        if game['home_score'] > game['road_score']:
            h2h_series[series_key]['s_home_games_won'] += 1
        else:
            h2h_series[series_key]['s_road_games_won'] += 1
    # doing the same if series home team matches the road team of the game
    elif h2h_series[series_key]['s_home'] == game['road_abbr']:
        h2h_series[series_key]['s_home_goals'] += game['road_score']
        h2h_series[series_key]['s_road_goals'] += game['home_score']
        if game['road_score'] > game['home_score']:
            h2h_series[series_key]['s_home_games_won'] += 1
        else:
            h2h_series[series_key]['s_road_games_won'] += 1

    # setting series score from series home team perspective
    h2h_series[series_key]['s_score'] = "%d-%d" % (
        h2h_series[series_key]['s_home_games_won'],
        h2h_series[series_key]['s_road_games_won'])


def create_h2h_record(h2h, team_a, team_b):
    """
    Creates new and empty head-to-head record in specified container using the
    given abbreviations for teams a and b.
    """
    if team_a not in h2h:
        h2h[team_a] = dict()
    if team_b not in h2h[team_a]:
        h2h[team_a][team_b] = dict()
        h2h[team_a][team_b]['home'] = dict()
        h2h[team_a][team_b]['road'] = dict()
        for category in CATEGORIES:
            h2h[team_a][team_b]['home'][category] = 0
            h2h[team_a][team_b]['road'][category] = 0
    if team_b not in h2h:
        h2h[team_b] = dict()
    if team_a not in h2h[team_b]:
        h2h[team_b][team_a] = dict()
        h2h[team_b][team_a]['home'] = dict()
        h2h[team_b][team_a]['road'] = dict()
        for category in CATEGORIES:
            h2h[team_b][team_a]['home'][category] = 0
            h2h[team_b][team_a]['road'][category] = 0

    return h2h


def register_game(h2h, game):
    """
    Registers information from specified game in dictionary of head-to-head
    game records.
    """
    # retrieving home and road teams from current game
    home = game['home_abbr']
    road = game['road_abbr']

    # setting up empty head-to-head-record for current teams (if
    # necessary)
    h2h = create_h2h_record(h2h, home, road)

    # registering regular season game game
    h2h[home][road]['home']['games_played'] += 1
    h2h[road][home]['road']['games_played'] += 1
    if game['overtime']:
        h2h[home][road]['home']['ot_games_played'] += 1
        h2h[road][home]['road']['ot_games_played'] += 1
    if game['shootout']:
        h2h[home][road]['home']['so_games_played'] += 1
        h2h[road][home]['road']['so_games_played'] += 1

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

    return h2h


def register_playoff_game(h2h, h2h_series, game):
    """
    Registers information from specified game in dictionary of head-to-head
    game and playoff series records.
    """
    # retrieving home and road teams from current game
    home = game['home_abbr']
    road = game['road_abbr']
    sorted_teams = sorted([home, road])
    # setting up series key (consisting of season, alphabetically
    # sorted abbreviations of both participating teams, and round
    # name, e.g. *2018_MAN_RBM_Finale*)
    series_key = "_".join((str(game['season']), *sorted_teams, game['round']))
    create_update_playoff_series(h2h_series, series_key, game)

    # registering game as playoff game
    h2h[home][road]['home']['po_games_played'] += 1
    h2h[road][home]['road']['po_games_played'] += 1
    if game['overtime']:
        h2h[home][road]['home']['po_ot_games_played'] += 1
        h2h[road][home]['road']['po_ot_games_played'] += 1
    if game['shootout']:
        h2h[home][road]['home']['po_so_games_played'] += 1
        h2h[road][home]['road']['po_so_games_played'] += 1

    # registering goals scored
    h2h[home][road]['home']['goals_for_po'] += game['home_score']
    h2h[home][road]['home'][
        'goals_against_po'] += game['road_score']
    h2h[road][home]['road']['goals_for_po'] += game['road_score']
    h2h[road][home]['road'][
        'goals_against_po'] += game['home_score']

    # registering game outcome
    if game['home_score'] > game['road_score']:
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

    return h2h, h2h_series


def calculate_winning_percentages(h2h):
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
            for category in CATEGORIES:
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

    return h2h


def prepare_h2h_records_of_current_teams(h2h):
    """
    Prepares head-to-head records of current DEL teams suitable for usage on
    extended stats website.
    """
    curr_h2h = dict()

    for key in CURRENT_TEAMS:
        curr_h2h[key] = dict()
        for opp_key in CURRENT_TEAMS:
            # teams don't play against themselves
            if opp_key == key:
                continue
            curr_h2h[key][opp_key] = dict()
            if key not in h2h:
                continue
            if opp_key not in h2h[key]:
                continue
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

    return curr_h2h


def prepare_h2h_series_of_current_teams(h2h_series):
    """
    Prepares head-to-head series records of current DEL teams suitable for
    usage on extended stats website.
    """
    curr_team_series = defaultdict(list)

    for series_key in h2h_series:
        series = h2h_series[series_key]
        home, road = series['s_home'], series['s_road']
        if home in CURRENT_TEAMS:
            home_series = dict()
            home_series['season'] = series['season']
            home_series['round'] = series['round']
            home_series['round_type'] = series['round_type']
            home_series['team'] = home
            home_series['opp_team'] = road
            home_series['score'] = series['s_score']
            home_series['games_played'] = series['s_games_played']
            home_series['wins'] = series['s_home_games_won']
            home_series['losses'] = series['s_road_games_won']
            home_series['goals_for'] = series['s_home_goals']
            home_series['goals_against'] = series['s_road_goals']
            home_series['home_advantage'] = True
            if home_series['wins'] > home_series['losses']:
                home_series['series_win'] = 1
                home_series['series_loss'] = 0
            else:
                home_series['series_win'] = 0
                home_series['series_loss'] = 1
            curr_team_series[home].append(home_series)

        if road in CURRENT_TEAMS:
            road_series = dict()
            road_series['season'] = series['season']
            road_series['round'] = series['round']
            road_series['round_type'] = series['round_type']
            road_series['team'] = road
            road_series['opp_team'] = home
            road_series['score'] = "-".join(series['s_score'].split("-")[::-1])
            road_series['games_played'] = series['s_games_played']
            road_series['wins'] = series['s_road_games_won']
            road_series['losses'] = series['s_home_games_won']
            road_series['goals_for'] = series['s_road_goals']
            road_series['goals_against'] = series['s_home_goals']
            road_series['home_advantage'] = False
            if road_series['wins'] > road_series['losses']:
                road_series['series_win'] = 1
                road_series['series_loss'] = 0
            else:
                road_series['series_win'] = 0
                road_series['series_loss'] = 1
            curr_team_series[road].append(road_series)

    return curr_team_series


def save_h2h_records_to_csv(curr_h2h):
    """
    Prepares and saves head-to-head game records of current DEL teams to a
    CSV file.
    """
    # preparing CSV dataset with h2h records of current DEL teams
    records = list()
    for key in CURRENT_TEAMS:
        for opp_key in CURRENT_TEAMS:
            if key == opp_key:
                continue
            if not curr_h2h[key][opp_key]:
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


if __name__ == '__main__':

    season_files = os.listdir(os.path.join(CONFIG['base_data_dir'], 'archive'))
    season_types = set()

    # setting up containers for head-to-head game and series records
    h2h = dict()
    h2h_series = dict()

    for season_file in season_files[:]:
        match = re.search(SEASON_FILE_REGEX, season_file)
        if not match:
            continue
        # loading all games for current season
        season_path = os.path.join(
            CONFIG['base_data_dir'], 'archive', season_file)
        season_games = json.loads(open(season_path).read())

        # skipping current season since we're retrieving pre-season data
        if int(match.group(1)) == CURRENT_SEASON:
            continue

        print(
            "+ Processing %d games from the %s/%d season" % (
                len(season_games), match.group(1), int(match.group(1)) + 1))

        for game in season_games[:]:
            # registering any kind of game
            h2h = register_game(h2h, game)
            # registering game as playoff game (if applicable)
            if game['season_type'] in PO_SEASON_TYPES:
                h2h, h2h_series = register_playoff_game(h2h, h2h_series, game)

    # finalizing and saving head-to-head game records
    # calculating winning percentages
    h2h = calculate_winning_percentages(h2h)

    # preparing head-to-head records of current DEL teams
    curr_h2h = prepare_h2h_records_of_current_teams(h2h)

    # saving all head-to-head records to disk
    tgt_path = os.path.join(CONFIG['base_data_dir'], 'archive', 'h2h.json')
    open(tgt_path, 'w').write(json.dumps(h2h, indent=2))
    # saving head-to-head records of current teams to disk
    tgt_path = os.path.join(
        CONFIG['tgt_processing_dir'],
        str(CURRENT_SEASON),
        'pre_season_h2h.json')
    open(tgt_path, 'w').write(json.dumps(curr_h2h, indent=2))

    # preparing CSV dataset with h2h records of current DEL teams
    save_h2h_records_to_csv(curr_h2h)

    # finalizing and saving head-to-head playoff series records
    # preparing head-to-head playoff series records of current DEL teams
    curr_h2h_series = prepare_h2h_series_of_current_teams(h2h_series)
