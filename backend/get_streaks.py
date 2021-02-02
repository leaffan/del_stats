#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import argparse
import operator

from collections import namedtuple, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

TeamGame = namedtuple('TeamGame', [
    'team', 'game_id', 'game_date', 'game_type', 'home_road', 'roster'])
Streak = namedtuple('Streak', [
    'player_id', 'team', 'type', 'length', 'from_date', 'to_date', 'goals', 'assists', 'points'])
Slump = namedtuple('Slump', [
    'player_id', 'team', 'type', 'length', 'from_date', 'to_date'])

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

GAME_SRC = 'del_games.json'
PLAYER_STATS_SRC = 'del_player_game_stats.json'
PLAYER_SRC = 'del_players.json'

STREAK_DATA_STRICT_TGT = 'del_streaks_strict.json'
STREAK_DATA_LOOSE_TGT = 'del_streaks_loose.json'
SLUMP_DATA_STRICT_TGT = 'del_slumps_strict.json'
SLUMP_DATA_LOOSE_TGT = 'del_slumps_loose.json'


def collect_team_games(games, teams):
    """
    Collects sorted lists of games played for each of the specified teams.
    """
    team_games = dict()

    for team in teams:
        single_team_games = list()
        for game in games:
            if team in [game['home_abbr'], game['road_abbr']]:
                # determining home/road status
                if team == game['home_abbr']:
                    home_road_key = 'home'
                else:
                    home_road_key = 'road'
                # retrieving game roster (only forwards/defensemen)
                roster = list()
                for l in ['d1', 'd2', 'd3', 'd4', 'f1', 'f2', 'f3', 'f4']:
                    if "%s_%s" % (home_road_key, l) in game:
                        roster.extend(game["%s_%s" % (home_road_key, l)])
                else:
                    # removing zeros from roster
                    while 0 in roster:
                        roster.remove(0)
                # creating actual team game
                team_game = TeamGame(
                    team, game['game_id'], game['date'], game['season_type'], home_road_key, sorted(roster))
                single_team_games.append(team_game)
        else:
            # sorting all team games by date
            single_team_games.sort(key=operator.attrgetter('game_date'))

        # adding team games to dictionary of all team games
        team_games[team] = single_team_games

    return team_games


def save_and_reset_streak(raw_streak, component, plr_id, team):
    """
    Saves and resets streak for specified player, team and scoring component.
    """
    # creating an actual streak item from raw streak data
    if raw_streak[component]['length'] > 2:
        streak = Streak(
            plr_id, team, component, raw_streak[component]['length'],
            min(raw_streak[component]['range']), max(raw_streak[component]['range']),
            raw_streak[component]['goals'], raw_streak[component]['assists'], raw_streak[component]['points']
        )
    else:
        streak = None
    # re-setting raw streak data
    for key in raw_streak[component]:
        raw_streak[component][key] = 0
    else:
        raw_streak[component]['range'] = list()

    return streak


def save_and_reset_slump(raw_slump, component, plr_id, team):
    """
    Saves and resets slump for specified player, team and scoring component.
    """
    # creating an actual slump item from raw slump data
    if raw_slump[component]['length'] > 4:
        slump = Slump(
            plr_id, team, component, raw_slump[component]['length'],
            min(raw_slump[component]['range']), max(raw_slump[component]['range'])
        )
    else:
        slump = None
    # re-setting raw streak data
    for key in raw_slump[component]:
        raw_slump[component][key] = 0
    else:
        raw_slump[component]['range'] = list()

    return slump


def post_process_streak_slump(streaks_slumps, raw_streak_slump, component, plr_id, team, max_lengths, type='streak'):
    """
    Handles post-processing of streak/slump data after registering it. Includes
    creation of an actual streak/slump item.
    """
    if type == 'streak':
        streak_slump = save_and_reset_streak(raw_streak_slump, component, plr_id, team)
    elif type == 'slump':
        # bailing out since we're not registering assist slumps
        if component == 'assists':
            return
        streak_slump = save_and_reset_slump(raw_streak_slump, component, plr_id, team)
    if streak_slump:
        streaks_slumps[component].append(streak_slump)
        if streak_slump.length > max_lengths[component]:
            max_lengths[component] = streak_slump.length


def get_streaks_slumps_for_player(plr_id, plr_team, player_stats, players):
    """
    Retrieves scorings streaks for specified player only regardles of the team
    and whether he was dressed for all the team's games during the streak.
    """
    plr_name = " ".join((players[plr_id]['first_name'], players[plr_id]['last_name']))
    print("+ Collecting loosely defined scoring streaks/slumps for %s" % plr_name)
    # setting containers for all of a player's streaks and slumps
    single_player_streaks = defaultdict(list)
    single_player_slumps = defaultdict(list)
    # setting containers to hold maximum length of player's streaks and slumps
    max_streak_lengths = defaultdict(int)
    max_slump_lengths = defaultdict(int)
    # temporary containers to hold raw streak or slump data
    raw_streaks = dict()
    raw_slumps = dict()
    # initializing temporary containers
    for component in ['goals', 'assists', 'points']:
        raw_streaks[component] = {'length': 0, 'goals': 0, 'assists': 0, 'points': 0, 'range': list()}
        raw_slumps[component] = {'length': 0, 'goals': 0, 'assists': 0, 'points': 0, 'range': list()}

    single_player_stats = list(filter(lambda d: d['player_id'] == plr_id and d['team'] == plr_team, player_stats))
    single_player_stats = sorted(single_player_stats, key=lambda d: d['game_date'])

    for plr_game in single_player_stats:
        for component in ['goals', 'assists', 'points']:
            if plr_game[component]:
                raw_streaks[component]['length'] += 1
                raw_streaks[component]['goals'] += plr_game['goals']
                raw_streaks[component]['assists'] += plr_game['assists']
                raw_streaks[component]['points'] += plr_game['points']
                raw_streaks[component]['range'].append(plr_game['game_date'])
            else:
                post_process_streak_slump(
                    single_player_streaks, raw_streaks, component, plr_id, plr_team, max_streak_lengths)
            if not plr_game[component]:
                raw_slumps[component]['length'] += 1
                raw_slumps[component]['range'].append(plr_game['game_date'])
            else:
                post_process_streak_slump(
                    single_player_slumps, raw_slumps, component, plr_id, plr_team, max_slump_lengths, type='slump')
    else:
        for component in ['goals', 'assists', 'points']:
            post_process_streak_slump(
                single_player_streaks, raw_streaks, component, plr_id, plr_team, max_streak_lengths)
            post_process_streak_slump(
                single_player_slumps, raw_slumps, component, plr_id, plr_team, max_slump_lengths, type='slump')

    last_plr_game_date = single_player_stats[-1]['game_date']

    all_single_player_streaks = combine_streaks_slumps(single_player_streaks, max_streak_lengths, last_plr_game_date)
    all_single_player_slumps = combine_streaks_slumps(single_player_slumps, max_slump_lengths, last_plr_game_date)

    return all_single_player_streaks, all_single_player_slumps


def get_streaks_slumps_for_team_and_player(plr_id, plr_team, team_games, player_stats, players):
    """
    Retrieves scorings streaks for specified player and team using provided
    team games and player statistics.
    """
    plr_name = " ".join((players[plr_id]['first_name'], players[plr_id]['last_name']))
    print("+ Collecting strictly defined scoring streaks/slumps for %s" % plr_name)
    # setting containers for all of a player's streaks and slumps
    single_player_streaks = defaultdict(list)
    single_player_slumps = defaultdict(list)
    # setting containers to hold maximum length of player's streaks and slumps
    max_streak_lengths = defaultdict(int)
    max_slump_lengths = defaultdict(int)
    # temporary containers to hold raw streak or slump data
    raw_streaks = dict()
    raw_slumps = dict()
    # initializing temporary containers
    for component in ['goals', 'assists', 'points']:
        raw_streaks[component] = {'length': 0, 'goals': 0, 'assists': 0, 'points': 0, 'range': list()}
        raw_slumps[component] = {'length': 0, 'goals': 0, 'assists': 0, 'points': 0, 'range': list()}

    for team_game in team_games[plr_team]:
        # re-setting all (possibly on-going) streaks if player didn't play in
        # current game
        team = team_game.team
        if plr_id not in team_game.roster:
            for component in ['goals', 'assists', 'points']:
                post_process_streak_slump(
                    single_player_streaks, raw_streaks, component, plr_id, team, max_streak_lengths)
                post_process_streak_slump(
                    single_player_slumps, raw_slumps, component, plr_id, team, max_slump_lengths, type='slump')

        for plr_game in player_stats:
            if (
                plr_game['game_id'] == team_game.game_id and
                plr_game['player_id'] == plr_id and
                plr_game['team'] == team
            ):
                for component in ['goals', 'assists', 'points']:
                    if plr_game[component]:
                        raw_streaks[component]['length'] += 1
                        raw_streaks[component]['goals'] += plr_game['goals']
                        raw_streaks[component]['assists'] += plr_game['assists']
                        raw_streaks[component]['points'] += plr_game['points']
                        raw_streaks[component]['range'].append(team_game.game_date)
                    else:
                        post_process_streak_slump(
                            single_player_streaks, raw_streaks, component, plr_id, team, max_streak_lengths)
                    if not plr_game[component]:
                        raw_slumps[component]['length'] += 1
                        raw_slumps[component]['range'].append(plr_game['game_date'])
                    else:
                        post_process_streak_slump(
                            single_player_slumps, raw_slumps, component, plr_id, team, max_slump_lengths, type='slump')
                break
    # finally ending all on-going streaks
    else:
        for component in ['goals', 'assists', 'points']:
            post_process_streak_slump(
                single_player_streaks, raw_streaks, component, plr_id, team, max_streak_lengths)
            post_process_streak_slump(
                single_player_slumps, raw_slumps, component, plr_id, team, max_slump_lengths, type='slump')
    # retrieving last game date for current team
    last_team_game_date = team_games[plr_team][-1].game_date

    all_single_player_streaks = combine_streaks_slumps(single_player_streaks, max_streak_lengths, last_team_game_date)
    all_single_player_slumps = combine_streaks_slumps(single_player_slumps, max_slump_lengths, last_team_game_date)

    return all_single_player_streaks, all_single_player_slumps


def combine_streaks_slumps(single_plr_streak_slumps, max_lengths, last_game_date):
    """
    Combines all collected player scoring streaks/slumps determining the longest and
    (possibly) current ones as well.
    """
    all_single_plr_streaks_slumps = list()

    for component in single_plr_streak_slumps:
        for streak_slump in single_plr_streak_slumps[component]:
            streak_slump_d = streak_slump._asdict()
            streak_slump_d['last_name'] = players[streak_slump.player_id]['last_name']
            streak_slump_d['full_name'] = " ".join((
                players[streak_slump.player_id]['first_name'], players[streak_slump.player_id]['last_name']
            ))
            streak_slump_d['position'] = players[streak_slump.player_id]['position']
            streak_slump_d['iso_country'] = players[streak_slump.player_id]['iso_country']
            streak_slump_d['age'] = players[streak_slump.player_id]['age']
            # setting default indicators for longest and current streaks/slumps
            streak_slump_d['longest'] = False
            streak_slump_d['current'] = False
            if streak_slump.length == max_lengths[component]:
                streak_slump_d['longest'] = True
            if streak_slump.to_date == last_game_date:
                streak_slump_d['current'] = True
            all_single_plr_streaks_slumps.append(streak_slump_d)

    return all_single_plr_streaks_slumps


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Retrieve DEL scoring streaks.')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, default=2020,
        type=int, choices=[2016, 2017, 2018, 2019, 2020],
        metavar='season to process games for',
        help="The season information will be processed for")

    args = parser.parse_args()
    season = args.season

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))
    src_path = os.path.join(tgt_dir, GAME_SRC)
    player_src_path = os.path.join(CONFIG['tgt_processing_dir'], PLAYER_SRC)
    player_stats_src_path = os.path.join(tgt_dir, PLAYER_STATS_SRC)

    # loading games
    games = json.loads(open(src_path).read())
    player_stats = json.loads(open(player_stats_src_path).read())[-1]
    players = json.loads(open(player_src_path).read())
    players = {int(k): v for (k, v) in players.items()}

    # filtering games and player stats to only contain data from regular season or playoff games
    games = list(filter(lambda g: g['season_type'] in ['RS', 'PO'], games))
    player_stats = list(filter(lambda g: g['season_type'] in ['RS', 'PO'], player_stats))

    teams = set()
    player_teams = set()
    # collecting teams
    [teams.add(game['home_abbr']) for game in games]
    [teams.add(game['road_abbr']) for game in games]
    # collecting games played by each team and player
    [player_teams.add((
        player_stat['player_id'], player_stat['team'])) for player_stat in player_stats]
    # collecting indivudual team games
    team_games = collect_team_games(games, teams)

    all_streaks_strict = list()
    all_streaks_loose = list()
    all_slumps_strict = list()
    all_slumps_loose = list()

    # retrieving scoring streaks in parallel threads
    with ThreadPoolExecutor(max_workers=8) as threads:
        tasks = {threads.submit(
            get_streaks_slumps_for_team_and_player, plr_id, plr_team, team_games, player_stats, players
        ): (
            plr_id, plr_team) for plr_id, plr_team in player_teams}
        for completed_task in as_completed(tasks):
            streaks, slumps = completed_task.result()
            all_streaks_strict.extend(streaks)
            all_slumps_strict.extend(slumps)

    with ThreadPoolExecutor(max_workers=8) as threads:
        tasks = {threads.submit(
            get_streaks_slumps_for_player, plr_id, plr_team, player_stats, players
        ): (
            plr_id, plr_team) for plr_id, plr_team in player_teams}
        for completed_task in as_completed(tasks):
            streaks, slumps = completed_task.result()
            all_streaks_loose.extend(streaks)
            all_slumps_loose.extend(slumps)

    # removing goaltenders from slump data
    all_slumps_loose = list(filter(lambda d: d['position'] != 'GK', all_slumps_loose))
    all_slumps_strict = list(filter(lambda d: d['position'] != 'GK', all_slumps_strict))

    # dumping results to JSON
    tgt_streak_path = os.path.join(tgt_dir, STREAK_DATA_STRICT_TGT)
    open(tgt_streak_path, 'w').write(json.dumps(all_streaks_strict, indent=2))
    tgt_streak_path = os.path.join(tgt_dir, STREAK_DATA_LOOSE_TGT)
    open(tgt_streak_path, 'w').write(json.dumps(all_streaks_loose, indent=2))

    tgt_slump_path = os.path.join(tgt_dir, SLUMP_DATA_STRICT_TGT)
    open(tgt_slump_path, 'w').write(json.dumps(all_slumps_strict, indent=2))
    tgt_slump_path = os.path.join(tgt_dir, SLUMP_DATA_LOOSE_TGT)
    open(tgt_slump_path, 'w').write(json.dumps(all_slumps_loose, indent=2))
