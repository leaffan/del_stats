#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import json
import yaml

from utils import read_del_team_names, get_season

from dateutil.parser import parse

# loading configuration from external file
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

TEAM_LOOKUP = read_del_team_names()

SRC_DIR = os.path.join(CONFIG['base_data_dir'], 'archive')

STREAK_CUTOFF = 5


def load_games():
    """
    Loads all registered games from source directory.
    """
    all_games = list()

    files = os.listdir(SRC_DIR)
    for f in files[:]:
        if not f.startswith('games_'):
            continue
        src_path = os.path.join(SRC_DIR, f)
        games = json.loads(open(src_path).read())
        print("+ Loaded %d games from %s" % (len(games), src_path))
        all_games.extend(games)

    return all_games


def get_team_games(team_id, all_games):
    """
    Retrieves games (incl. home and road ones) played by the team identified by
    the specified team id.
    """
    team_games = list(filter(
        lambda d:
            d['home_id'] == team_id or d['road_id'] == team_id, all_games))
    team_home_games = list(filter(
        lambda d:
            d['home_id'] == team_id, all_games))
    team_road_games = list(filter(
        lambda d:
            d['road_id'] == team_id, all_games))

    return team_games, team_home_games, team_road_games


def set_streak(team_id, team_abbr, type, count, streak_games, start, end):
    """
    Register game streak for team of specified team id.
    """
    start_as_date = parse(start)
    season = get_season(start_as_date)
    team_name = TEAM_LOOKUP[(team_id, season)][-1]

    streak = dict()
    streak['team_abbr'] = team_abbr
    streak['team'] = team_name
    streak['team_id'] = team_id
    streak['type'] = type
    streak['length'] = count
    streak['start'] = start
    streak['end'] = end
    streak['games'] = list()
    streak['scores_for'] = 0
    streak['scores_against'] = 0
    for sg in streak_games:
        single_game = dict()
        single_game['game_date'] = sg['game_date']
        single_game['opp'] = sg['opp_abbr']
        single_game['score'] = sg['score']
        streak['games'].append(single_game)
        streak['scores_for'] += sg['own_score']
        streak['scores_against'] += sg['opp_score']

    return streak


def enrich_team_games(team_id, team_games):

    for tg in team_games:
        # checking whether current team was the home team
        if tg['home_id'] == team_id:
            abbr = tg['home_abbr']
            opp_abbr = tg['road_abbr']
            opp_team = tg['road_team']
            score = "%d-%d" % (tg['home_score'], tg['road_score'])
            own_score = tg['home_score']
            opp_score = tg['road_score']
            if tg['home_score'] > tg['road_score']:
                outcome = 'W'
            elif tg['home_score'] < tg['road_score']:
                outcome = 'L'
            else:
                outcome = 'T'
        # otherwise treating current team as the road team
        else:
            abbr = tg['road_abbr']
            opp_abbr = tg['home_abbr']
            opp_team = tg['home_team']
            score = "%d-%d" % (tg['road_score'], tg['home_score'])
            own_score = tg['road_score']
            opp_score = tg['home_score']
            if tg['home_score'] > tg['road_score']:
                outcome = 'L'
            elif tg['home_score'] < tg['road_score']:
                outcome = 'W'
            else:
                outcome = 'T'

        # enriching current team game with retrieved variables
        tg['score'] = score
        tg['outcome'] = outcome
        tg['abbr'] = abbr
        tg['opp_team'] = opp_team
        tg['opp_abbr'] = opp_abbr
        tg['own_score'] = own_score
        tg['opp_score'] = opp_score


def find_streaks(team_games):
    # setting up container for results
    streaks = list()
    # setting up helper variables
    wins = 0
    losses = 0
    ties = 0

    start_streak = ''
    end_streak = ''
    streak_games = list()

    for tg in team_games:
        # finishing respective streak if outcome of current game is not equal
        # to the last one
        if wins and tg['outcome'] != 'W':
            end_streak = tg['game_date']
            if wins > STREAK_CUTOFF:
                print("%d consecutive wins from %s to %s" % (
                    wins, start_streak, end_streak))
                streaks.append(set_streak(
                    team_id, tg['abbr'], 'W', wins,
                    streak_games, start_streak, end_streak))
            wins = 0
            streak_games = list()
        if losses and tg['outcome'] != 'L':
            end_streak = tg['game_date']
            if losses > STREAK_CUTOFF:
                print("%d consecutive losses from %s to %s" % (
                    losses, start_streak, end_streak))
                streaks.append(set_streak(
                    team_id, tg['abbr'], 'L', losses,
                    streak_games, start_streak, end_streak))
            losses = 0
            streak_games = list()
        if ties and tg['outcome'] != 'T':
            end_streak = tg['game_date']
            if ties > STREAK_CUTOFF:
                print("%d consecutive ties from %s to %s" % (
                    ties, start_streak, end_streak))
                streaks.append(set_streak(
                    team_id, tg['abbr'], 'T', ties,
                    streak_games, start_streak, end_streak))
            ties = 0
            streak_games = list()
        # continuing an on-going/starting a new streak
        if tg['outcome'] == 'W':
            if not wins:
                start_streak = tg['game_date']
            wins += 1
            streak_games.append(tg)
        elif tg['outcome'] == 'L':
            if not losses:
                start_streak = tg['game_date']
            losses += 1
            streak_games.append(tg)
        elif tg['outcome'] == 'T':
            if not ties:
                start_streak = tg['game_date']
            ties += 1
            streak_games.append(tg)
    # handling streaks that are currently on-going
    else:
        if wins:
            end_streak = tg['game_date']
            if wins > STREAK_CUTOFF:
                print("%d consecutive wins from %s to %s" % (
                    wins, start_streak, end_streak))
                streaks.append(set_streak(
                    team_id, tg['abbr'], 'W', wins,
                    streak_games, start_streak, end_streak))
            wins = 0
        if losses:
            end_streak = tg['game_date']
            if losses > STREAK_CUTOFF:
                print("%d consecutive losses from %s to %s" % (
                    losses, start_streak, end_streak))
                streaks.append(set_streak(
                    team_id, tg['abbr'], 'L', losses,
                    streak_games, start_streak, end_streak))
            losses = 0
        if ties:
            end_streak = tg['game_date']
            if ties > STREAK_CUTOFF:
                print("%d consecutive ties from %s to %s" % (
                    ties, start_streak, end_streak))
                streaks.append(set_streak(
                    team_id, tg['abbr'], 'T', ties,
                    streak_games, start_streak, end_streak))
            ties = 0

    return streaks


if __name__ == '__main__':

    # loading games
    all_games = load_games()
    # sorting games by game date
    all_games = sorted(
        all_games, key=lambda d: d['game_date'], reverse=False)
    # retrieving all available teams
    all_home_teams = [g['home_id'] for g in all_games]
    all_road_teams = [g['road_id'] for g in all_games]
    all_teams = set(all_home_teams + all_road_teams)

    print(all_teams)

    losing_streaks = list()
    winning_streaks = list()

    for team_id in list(all_teams)[:]:
        # retrieving games for current team
        team_games, home_games, road_games = get_team_games(team_id, all_games)
        # enriching games for current team
        enrich_team_games(team_id, team_games)

        print("+ Finding streaks for %s" % team_games[0]['abbr'])

        streaks = find_streaks(team_games)

        losing_streaks.extend(list(filter(
            lambda d: d['type'] == 'L', streaks)))
        winning_streaks.extend(list(filter(
            lambda d: d['type'] == 'W', streaks)))

        tgt_file = "streaks_%d.json" % team_id
        tgt_path = os.path.join(CONFIG['base_data_dir'], 'archive', tgt_file)
        open(tgt_path, 'w').write(json.dumps(streaks, indent=2))

    losing_streaks = sorted(
        losing_streaks, key=lambda d: d['length'], reverse=True)
    winning_streaks = sorted(
        winning_streaks, key=lambda d: d['length'], reverse=True)

    keys = list(losing_streaks[0].keys())
    keys.remove('games')

    losing_csv_tgt_file = "losing_streaks.csv"
    losing_csv_tgt_path = os.path.join(
        CONFIG['base_data_dir'], 'archive', losing_csv_tgt_file)
    winning_csv_tgt_file = "winning_streaks.csv"
    winning_csv_tgt_path = os.path.join(
        CONFIG['base_data_dir'], 'archive', winning_csv_tgt_file)

    with open(winning_csv_tgt_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        dict_writer = csv.DictWriter(
            output_file, keys, delimiter=';', extrasaction='ignore',
            lineterminator='\n')
        dict_writer.writeheader()
        dict_writer.writerows(winning_streaks)
