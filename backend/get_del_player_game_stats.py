#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import argparse
import itertools
from datetime import datetime
from collections import defaultdict

import requests
from dateutil.parser import parse

from utils import get_game_info

BASE_URL = 'https://www.del.org/live-ticker'

MATCHES_INSERT = 'matches'
VISUALIZATION_INSERT = 'visualization/shots'

GAME_SRC = 'del_games.json'
PLAYER_GAME_STATS_TGT = 'del_player_game_stats.json'

HOME_STATS_SUFFIX = 'player-stats-home.json'
ROAD_STATS_SUFFIX = 'player-stats-guest.json'
PERIOD_EVENTS_SUFFIX = 'period-events.json'

PENALTY_CATEGORIES = {
    'lazy': ['TRIP', 'HOLD', 'HOOK', 'HO-ST', 'INTRF', 'SLASH'],
    'roughing': ['CHARG', 'ROUGH', 'BOARD', 'CROSS', 'FIST'],
    'reckless': ['HI-ST', 'ELBOW', 'L-HIT', 'CHE-H', 'KNEE', 'CHE-B', 'CLIP'],
    'other': ['THR-S', 'UN-SP', 'DELAY', 'ABUSE', 'TOO-M', 'L-BCH', 'DIVE'],
}

REVERSE_PENALTY_CATEGORIES = dict()
for key, values in PENALTY_CATEGORIES.items():
    for value in values:
        REVERSE_PENALTY_CATEGORIES[value] = key

TGT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
PER_PLAYER_TGT_DIR = 'per_player'
U23_CUTOFF_DATE = parse("1996-01-01")

# default empty line
EMPTY_LINE = [0, 0, 0]
# defining potential lines and positions
LINES = ['1', '2', '3', '4']
POSITIONS = ['d', 'f']
POS_LINES = list(
    map(''.join, itertools.chain(itertools.product(POSITIONS, LINES))))


def get_single_game_player_data(game):
    """
    Retrieves statistics for all players participating in specified game.
    """
    game_stat_lines = list()

    game_id = game['game_id']

    home_stats_url = "%s/%s/%d/%s" % (
        BASE_URL, MATCHES_INSERT, game_id, HOME_STATS_SUFFIX)
    road_stats_url = "%s/%s/%d/%s" % (
        BASE_URL, MATCHES_INSERT, game_id, ROAD_STATS_SUFFIX)
    # shots_url = "%s/%s/%d.json" % (BASE_URL, VISUALIZATION_INSERT, game_id)
    events_url = "%s/%s/%d/%s" % (
        BASE_URL, MATCHES_INSERT, game_id, PERIOD_EVENTS_SUFFIX)

    r = requests.get(home_stats_url)
    home_stats = r.json()
    r = requests.get(road_stats_url)
    road_stats = r.json()
    # r = requests.get(shots_url)
    # shots = r.json()
    r = requests.get(events_url)
    period_events = r.json()

    for home_stat_line in home_stats:
        player_game = retrieve_single_player_game_stats(
            home_stat_line, game, 'home')
        if player_game['games_played']:
            game_stat_lines.append(player_game)

    for road_stat_line in road_stats:
        player_game = retrieve_single_player_game_stats(
            road_stat_line, game, 'away')
        if player_game['games_played']:
            game_stat_lines.append(player_game)

    assistants = retrieve_assistants_from_event_data(period_events)
    penalties = retrieve_penalties_from_event_data(period_events)

    for gsl in game_stat_lines:
        # adding assistant information to player's game stat line
        if gsl['player_id'] in assistants:
            single_assist_dict = assistants[gsl['player_id']]
            gsl['primary_assists'] = single_assist_dict.get('A1', 0)
            gsl['secondary_assists'] = single_assist_dict.get('A2', 0)
            gsl['pp_assists'] = single_assist_dict.get('PPA', 0)
            gsl['pp_primary_assists'] = single_assist_dict.get('PPA1', 0)
            gsl['pp_secondary_assists'] = single_assist_dict.get('PPA2', 0)
            gsl['pp_points'] += gsl['pp_assists']
        # calculating primary points
        gsl['primary_points'] = gsl['goals'] + gsl['primary_assists']
        # adding penalty information to player's game stat line
        if gsl['player_id'] in penalties:
            single_penalty_dict = penalties[gsl['player_id']]
            gsl['penalties'] = single_penalty_dict.get('penalties', 0)
            gsl['pim_from_events'] = single_penalty_dict.get('pim', 0)
            for l in [2, 5, 10, 20]:
                gsl["_%dmin" % l] = single_penalty_dict['durations'].get(l, 0)
            gsl['penalty_shots'] = single_penalty_dict.get('penalty_shots')
            for category in PENALTY_CATEGORIES:
                gsl[category] = single_penalty_dict['categories'].get(
                    category, 0)
        # adding linemate information to player's game stat line
        defense_linemates, forward_linemates, line = get_linemates(gsl, game)
        gsl['line'] = line
        gsl['defense'] = defense_linemates
        gsl['forwards'] = forward_linemates

    return game_stat_lines


def get_linemates(game_stat_line, game):
    """
    Retrieving line mates in specified game for player with with given stat
    line.
    """
    # per default, linemates are non-existing
    defense = EMPTY_LINE[:2]
    forwards = EMPTY_LINE
    line = 0

    if game_stat_line['position'] != 'GK':
        player_id = game_stat_line['player_id']
        # iterating over all possible four lines/two positions
        for pos_line in POS_LINES:
            full_key = "%s_%s" % (game_stat_line['home_road'], pos_line)
            if full_key in game and player_id in game[full_key]:
                break

        # retrieving line number for current player
        if full_key:
            line = int(list(full_key)[-1])

        # complementing line information with players at different positions
        if "_f" in full_key:
            forwards = game[full_key]
            try:
                defense = game[full_key.replace("_f", "_d")]
            except KeyError:
                pass
        elif '_d' in full_key:
            defense = game[full_key]
            try:
                forwards = game[full_key.replace("_d", "_f")]
            except KeyError:
                pass

    return defense, forwards, line


def retrieve_single_player_game_stats(data_dict, game, key):
    """
    Retrieves single player's statistics in specified game.
    """
    game_id = game['game_id']
    # retrieving individual base data
    single_player_game = dict()
    single_player_game['game_id'] = game_id
    single_player_game['schedule_game_id'] = game['schedule_game_id']
    single_player_game['player_id'] = data_dict['id']
    single_player_game['no'] = data_dict['jersey']
    single_player_game['position'] = data_dict['position']
    single_player_game['first_name'] = data_dict['firstname']
    single_player_game['last_name'] = data_dict['surname']
    single_player_game['full_name'] = data_dict['name']
    single_player_game['country'] = data_dict['nationalityShort']
    single_player_game['shoots'] = data_dict['stick']
    single_player_game['weight'] = data_dict['weight']
    single_player_game['height'] = data_dict['height']
    single_player_game['date_of_birth'] = data_dict['dateOfBirth']
    # setting u23 status
    if (
        single_player_game['country'] == 'GER' and
        parse(single_player_game['date_of_birth']) >= U23_CUTOFF_DATE
    ):
        single_player_game['u23'] = True
    else:
        single_player_game['u23'] = False
    # setting up actual stats dictionary
    stat_dict = data_dict['statistics']
    # retrieving game stats for current player
    if key == 'home':
        single_player_game['home_road'] = key
    else:
        single_player_game['home_road'] = "road"
    single_player_game['game_date'] = game['date']
    single_player_game['season'] = game['season']
    single_player_game['season_type'] = game['season_type']
    single_player_game['round'] = game['round']
    single_player_game['team'] = stat_dict['teamShortcut']
    if key == 'home':
        single_player_game['score'] = game['home_score']
        single_player_game['opp_team'] = game['road_abbr']
        single_player_game['opp_score'] = game['road_score']
    else:
        single_player_game['score'] = game['road_score']
        single_player_game['opp_team'] = game['home_abbr']
        single_player_game['opp_score'] = game['home_score']
    if game['shootout_game']:
        single_player_game['game_type'] = 'SO'
    elif game['overtime_game']:
        single_player_game['game_type'] = 'OT'
    else:
        single_player_game['game_type'] = ''
    single_player_game['games_played'] = stat_dict['games']
    single_player_game['goals'] = stat_dict['goals'][key]
    single_player_game['assists'] = stat_dict['assists'][key]
    single_player_game['primary_assists'] = 0
    single_player_game['secondary_assists'] = 0
    single_player_game['points'] = stat_dict['points'][key]
    single_player_game['primary_points'] = 0
    single_player_game['pim'] = stat_dict['penaltyMinutes']
    single_player_game['plus'] = stat_dict['positive']
    single_player_game['minus'] = stat_dict['negative']
    single_player_game['plus_minus'] = (
        stat_dict['positive'] - stat_dict['negative'])
    single_player_game['pp_goals'] = stat_dict['ppGoals']
    single_player_game['pp_assists'] = 0
    single_player_game['pp_primary_assists'] = 0
    single_player_game['pp_secondary_assists'] = 0
    single_player_game['pp_points'] = single_player_game['pp_goals']
    single_player_game['sh_goals'] = stat_dict['shGoals']
    single_player_game['gw_goals'] = stat_dict['gwGoals']
    single_player_game['shots'] = stat_dict['shotsAttempts']
    single_player_game['shots_on_goal'] = stat_dict['shotsOnGoal'][key]
    single_player_game['shots_missed'] = stat_dict['shotsMissed']
    single_player_game['shots_blocked'] = stat_dict['shotsBlocked']
    single_player_game['shot_pctg'] = stat_dict['shotEfficiency']
    single_player_game['faceoffs'] = stat_dict['faceoffsCount']
    single_player_game['faceoffs_won'] = stat_dict['faceoffsWin']
    single_player_game['faceoffs_lost'] = stat_dict['faceoffsLosses']
    if single_player_game['faceoffs']:
        single_player_game['faceoff_pctg'] = round(
            single_player_game['faceoffs_won'] /
            single_player_game['faceoffs'] * 100., 3)
    else:
        single_player_game['faceoff_pctg'] = 0
    single_player_game['blocked_shots'] = stat_dict['blockedShotsByPlayer']
    single_player_game['time_on_ice'] = stat_dict['timeOnIce']
    single_player_game['time_on_ice_pp'] = stat_dict['timeOnIcePP']
    single_player_game['time_on_ice_sh'] = stat_dict['timeOnIceSH']
    single_player_game['shifts'] = stat_dict['shifts']
    single_player_game['penalties'] = 0
    single_player_game['pim_from_events'] = 0
    single_player_game['penalty_shots'] = 0
    if game['first_goal_player_id'] == single_player_game['player_id']:
        single_player_game['first_goals'] = 1
    else:
        single_player_game['first_goals'] = 0
    for l in [2, 5, 10, 20]:
        single_player_game["_%dmin" % l] = 0
    for category in PENALTY_CATEGORIES:
        single_player_game[category] = 0

    return single_player_game


def retrieve_assistants_from_event_data(period_events):
    """
    Retrieves primary and secondary assists from game event data.
    """
    assists_dict = dict()

    for period in period_events:
        events = period_events[period]
        for event in events:
            if event['type'] != 'goal':
                continue
            assist_cnt = 0
            for assistant in event['data']['assistants']:
                assist_cnt += 1
                assist_plr_id = assistant['playerId']
                if assist_plr_id not in assists_dict:
                    assists_dict[assist_plr_id] = defaultdict(int)
                assists_dict[assist_plr_id]["A%d" % assist_cnt] += 1
                if 'PP' in event['data']['balance']:
                    assists_dict[assist_plr_id]["PPA"] += 1
                    assists_dict[assist_plr_id]["PPA%d" % assist_cnt] += 1

    return assists_dict


def retrieve_penalties_from_event_data(period_events):
    """
    Retrieves penalty information from game event data.
    """
    penalties_dict = dict()

    for period in period_events:
        events = period_events[period]
        for event in events:
            if event['type'] != 'penalty':
                continue

            player = event['data']['disciplinedPlayer']
            # skipping penalties w/o a disciplined player
            if player is None:
                continue
            plr_id = player['playerId']

            if plr_id not in penalties_dict:
                penalties_dict[plr_id] = dict()
                penalties_dict[plr_id]['penalties'] = 0
                penalties_dict[plr_id]['infractions'] = defaultdict(int)
                penalties_dict[plr_id]['penalty_shots'] = 0
                penalties_dict[plr_id]['pim'] = 0
                penalties_dict[plr_id]['durations'] = defaultdict(int)
                penalties_dict[plr_id]['categories'] = defaultdict(int)

            duration = event['data']['duration']
            infraction = event['data']['codename']
            pim = int(duration / 60)

            penalties_dict[plr_id]['penalties'] += 1
            penalties_dict[plr_id]['infractions'][infraction] += 1
            penalties_dict[plr_id]['pim'] += pim
            penalties_dict[plr_id]['durations'][pim] += 1

            if infraction not in REVERSE_PENALTY_CATEGORIES:
                print(
                    "Previously unknown infraction '%s' " % infraction +
                    "discovered. Added to 'other' category.")
                penalties_dict[plr_id]['categories']['other'] += 1
            else:
                penalties_dict[plr_id]['categories'][
                    REVERSE_PENALTY_CATEGORIES[infraction]] += 1

            if event['data']['shooting']:
                penalties_dict[plr_id]['penalty_shots'] += 1

    return penalties_dict


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Download DEL player game statistics.')
    parser.add_argument(
        '--initial', dest='initial', required=False,
        action='store_true', help='Re-create list of player games')
    parser.add_argument(
        '--limit', dest='limit', required=False, type=int, default=0,
        help='Number of maximum games to be processed')

    args = parser.parse_args()

    initial = args.initial
    limit = int(args.limit)

    if not os.path.isdir(TGT_DIR):
        os.makedirs(TGT_DIR)
    if not os.path.isdir(os.path.join(TGT_DIR, PER_PLAYER_TGT_DIR)):
        os.makedirs(os.path.join(TGT_DIR, PER_PLAYER_TGT_DIR))

    # setting up source and target paths
    src_path = os.path.join(TGT_DIR, GAME_SRC)
    tgt_path = os.path.join(TGT_DIR, PLAYER_GAME_STATS_TGT)

    # loading games
    games = json.loads(open(src_path).read())

    # loading existing player game stats
    if not initial and os.path.isfile(tgt_path):
        player_game_stats = json.loads(open(tgt_path).read())[-1]
    else:
        player_game_stats = list()

    # setting up container for player game statistics
    per_player_game_stats = defaultdict(list)
    # retrieving set of games we already have retrieved player stats for
    registered_games = set([pg['game_id'] for pg in player_game_stats])

    cnt = 0

    for game in games[:]:
        cnt += 1
        # skipping already processed games
        if game['game_id'] in registered_games:
            continue

        print("+ Retrieving player stats for game %s" % get_game_info(game))
        single_player_game_stats = get_single_game_player_data(game)
        player_game_stats.extend(single_player_game_stats)

        # collecting stat lines on a per-player basis
        for stat_line in single_player_game_stats:
            per_player_game_stats[
                (stat_line['player_id'], stat_line['team'])].append(stat_line)
        if limit and cnt >= limit:
            break

    # retrieving current timestamp to indicate last modification of dataset
    current_datetime = datetime.now().timestamp() * 1000
    output = [current_datetime, player_game_stats]

    # dumping combined game stats for all players
    open(tgt_path, 'w').write(json.dumps(output, indent=2))

    # dumping individual player game stats
    for player_id, team in per_player_game_stats:
        tgt_path = os.path.join(
            TGT_DIR, PER_PLAYER_TGT_DIR, "%s_%d.json" % (team, player_id))

        output = per_player_game_stats[(player_id, team)]
        # optionally adding output to already existing data
        if not initial and os.path.isfile(tgt_path):
            existing_data = json.loads(open(tgt_path).read())
            existing_data.extend(output)
            output = existing_data

        open(tgt_path, 'w').write(json.dumps(output, indent=2))
