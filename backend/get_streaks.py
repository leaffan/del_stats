#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import operator

from collections import namedtuple, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

TeamGame = namedtuple('TeamGame', [
    'team', 'game_id', 'game_date', 'game_type', 'home_road', 'roster'])
Streak = namedtuple('Streak', [
    'player_id', 'team', 'type', 'length', 'from_date', 'to_date',
    'goals', 'assists', 'points'])

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

TGT_DIR = os.path.join(
    CONFIG['tgt_processing_dir'], str(CONFIG['default_season']))

GAME_SRC = 'del_games.json'
PLAYER_STATS_SRC = 'del_player_game_stats.json'
PLAYER_SRC = 'del_players.json'

STREAK_DATA_TGT = 'del_streaks.json'


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
                    team, game['game_id'], game['date'],
                    game['season_type'], home_road_key, sorted(roster))
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
            plr_id, team, component,
            raw_streak[component]['length'],
            min(raw_streak[component]['range']),
            max(raw_streak[component]['range']),
            raw_streak[component]['goals'],
            raw_streak[component]['assists'],
            raw_streak[component]['points']
        )
    else:
        streak = None
    # re-setting raw streak data
    for key in raw_streak[component]:
        raw_streak[component][key] = 0
    else:
        raw_streak[component]['range'] = list()

    return streak


def post_process_streak(
    all_streaks, raw_streak, component, plr_id, team, max_streak_lengths
):
    """
    Handles post-processing of streak data after registering it. Includes
    creation of an actual streak item.
    """
    streak = save_and_reset_streak(raw_streak, component, plr_id, team)
    if streak:
        all_streaks[component].append(streak)
        if streak.length > max_streak_lengths[component]:
            max_streak_lengths[component] = streak.length


def single_task(plr_id, plr_team, team_games, player_stats, players):
    """
    Retrieves scorings streaks for specified player and team using provided
    team games and player statistics.
    """
    plr_name = " ".join((
        players[plr_id]['first_name'], players[plr_id]['last_name']))
    print("Collecting scoring streaks by %s" % plr_name)
    # setting container for all of a player's streaks
    single_player_streaks = defaultdict(list)
    # setting container to hold maximum length of player's streaks
    max_streak_lengths = defaultdict(int)
    # temporary container to hold raw streak data
    raw_streaks = dict()
    # initializing temporary container
    for component in ['goals', 'assists', 'points']:
        raw_streaks[component] = {
            'length': 0, 'goals': 0, 'assists': 0, 'points': 0,
            'range': list()
        }
    for team_game in team_games[plr_team]:
        # re-setting all (possibly on-going) streaks if player didn't play in
        # current game
        if plr_id not in team_game.roster:
            for component in ['goals', 'assists', 'points']:
                post_process_streak(
                    single_player_streaks, raw_streaks, component,
                    plr_id, team_game.team, max_streak_lengths)

        for plr_game in player_stats:
            if (
                plr_game['game_id'] == team_game.game_id and
                plr_game['player_id'] == plr_id and
                plr_game['team'] == team_game.team
            ):
                for component in ['goals', 'assists', 'points']:
                    if plr_game[component]:
                        raw_streaks[component]['length'] += 1
                        raw_streaks[component][
                            'goals'] += plr_game['goals']
                        raw_streaks[component][
                            'assists'] += plr_game['assists']
                        raw_streaks[component][
                            'points'] += plr_game['points']
                        raw_streaks[component][
                            'range'].append(team_game.game_date)
                    else:
                        post_process_streak(
                            single_player_streaks, raw_streaks, component,
                            plr_id, team_game.team, max_streak_lengths)
                break
    # finally ending all on-going streaks
    else:
        for component in ['goals', 'assists', 'points']:
            post_process_streak(
                single_player_streaks, raw_streaks, component,
                plr_id, team_game.team, max_streak_lengths)
    # retrieving last game date for current team
    last_team_game_date = team_games[plr_team][-1].game_date

    return combine_single_player_streaks(
        single_player_streaks, max_streak_lengths, last_team_game_date)


def combine_single_player_streaks(
    single_player_streaks, max_streak_lengths, last_team_game_date
):
    """
    Combines all collected player scoring streaks determining the longest and
    (possibly) current ones as well.
    """
    all_single_player_streaks = list()

    for component in single_player_streaks:
        for streak in single_player_streaks[component]:
            streak_d = streak._asdict()
            streak_d['last_name'] = players[str(streak.player_id)]['last_name']
            streak_d['full_name'] = " ".join((
                players[str(streak.player_id)]['first_name'],
                players[str(streak.player_id)]['last_name']
            ))
            streak_d['position'] = players[str(streak.player_id)]['position']
            streak_d['age'] = players[str(streak.player_id)]['age']
            streak_d['iso_country'] = players[
                str(streak.player_id)]['iso_country']
            # setting default indicators for longest and current streaks
            streak_d['longest'] = False
            streak_d['current'] = False
            if streak.length == max_streak_lengths[component]:
                streak_d['longest'] = True
            if streak.to_date == last_team_game_date:
                streak_d['current'] = True
            all_single_player_streaks.append(streak_d)

    return all_single_player_streaks


if __name__ == '__main__':

    src_path = os.path.join(TGT_DIR, GAME_SRC)
    player_src_path = os.path.join(CONFIG['tgt_processing_dir'], PLAYER_SRC)
    player_stats_src_path = os.path.join(TGT_DIR, PLAYER_STATS_SRC)

    # loading games
    games = json.loads(open(src_path).read())
    player_stats = json.loads(open(player_stats_src_path).read())[-1]
    players = json.loads(open(player_src_path).read())
    players = {int(k): v for (k, v) in players.items()}

    teams = set()
    player_teams = set()
    # collecting teams
    [teams.add(game['home_abbr']) for game in games]
    [teams.add(game['road_abbr']) for game in games]
    # collecting games played by each team and player
    [player_teams.add((
        player_stat['player_id'],
        player_stat['team'])) for player_stat in player_stats]
    # collecting indivudual team games
    team_games = collect_team_games(games, teams)

    all_streaks = list()

    # retrieving scoring streaks in parallel threads
    with ThreadPoolExecutor(max_workers=8) as threads:
        tasks = {threads.submit(
            single_task, plr_id, plr_team, team_games, player_stats, players
        ): (
            plr_id, plr_team) for plr_id, plr_team in player_teams}
        for completed_task in as_completed(tasks):
            all_streaks.extend(completed_task.result())

    # dumping results to JSON
    tgt_streak_path = os.path.join(TGT_DIR, STREAK_DATA_TGT)
    open(tgt_streak_path, 'w').write(json.dumps(all_streaks, indent=2))
