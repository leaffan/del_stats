#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from datetime import timedelta
from collections import defaultdict

import requests

BASE_URL = 'https://www.del.org/live-ticker'

MATCHES_INSERT = 'matches'
VISUALIZATION_INSERT = 'visualization/shots'

GAME_SRC = 'del_games.json'
PLAYER_GAME_STATS_TGT = 'del_player_game_stats.json'

HOME_STATS_SUFFIX = 'player-stats-home.json'
ROAD_STATS_SUFFIX = 'player-stats-guest.json'
PERIOD_EVENTS_SUFFIX = 'period-events.json'


def get_single_game_player_data(game_id):
    """
    Retrieves statistics for all players participating in specified game.
    """
    game_stat_lines = list()

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

    for home_stat in home_stats:
        player_game = retrieve_single_player_game_stats(
            home_stat, game_id, 'home')
        if player_game['game_played']:
            game_stat_lines.append(player_game)

    for road_stat in road_stats:
        player_game = retrieve_single_player_game_stats(
            road_stat, game_id, 'away')
        if player_game['game_played']:
            game_stat_lines.append(player_game)

    assistants = retrieve_assistants_from_event_data(period_events)

    for gsl in game_stat_lines:
        if gsl['player_id'] in assistants:
            single_assist_dict = assistants[gsl['player_id']]
            gsl['primary_assists'] = single_assist_dict.get('A1', 0)
            gsl['secondary_assists'] = single_assist_dict.get('A2', 0)
            gsl['pp_assists'] = single_assist_dict.get('PPA', 0)
            gsl['pp_primary_assists'] = single_assist_dict.get('PPA1', 0)
            gsl['pp_secondary_assists'] = single_assist_dict.get('PPA2', 0)
            gsl['pp_points'] += gsl['pp_assists']

    return game_stat_lines


def retrieve_single_player_game_stats(data_dict, game_id, key):
    """
    Retrieves single player's statistics in specified game.
    """
    single_player_game = dict()
    single_player_game['game_id'] = game_id
    single_player_game['player_id'] = data_dict['id']
    single_player_game['no'] = data_dict['jersey']
    single_player_game['position'] = data_dict['position']
    single_player_game['first_name'] = data_dict['firstname']
    single_player_game['last_name'] = data_dict['surname']
    single_player_game['full_name'] = data_dict['name']
    single_player_game['country'] = data_dict['nationalityShort']
    single_player_game['shoots'] = data_dict['stick']
    single_player_game['date_of_birth'] = data_dict['dateOfBirth']
    single_player_game['weight'] = data_dict['weight']
    single_player_game['height'] = data_dict['height']
    single_player_game['country_long'] = data_dict['nationality']

    stat_dict = data_dict['statistics']

    single_player_game['team'] = stat_dict['teamShortcut']
    single_player_game['game_played'] = stat_dict['games']
    single_player_game['game_type'] = key
    single_player_game['goals'] = stat_dict['goals'][key]
    single_player_game['assists'] = stat_dict['assists'][key]
    single_player_game['primary_assists'] = 0
    single_player_game['secondary_assists'] = 0
    single_player_game['points'] = stat_dict['points'][key]
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
    single_player_game['blocked_shots'] = stat_dict['blockedShotsByPlayer']
    single_player_game['time_on_ice'] = timedelta(
        seconds=stat_dict['timeOnIce'])
    single_player_game['time_on_ice_pp'] = timedelta(
        seconds=stat_dict['timeOnIcePP'])
    single_player_game['time_on_ice_sh'] = timedelta(
        seconds=stat_dict['timeOnIceSH'])
    single_player_game['shifts'] = stat_dict['shifts']

    return single_player_game


def retrieve_assistants_from_event_data(period_events):
    """
    Retrieves primary and secondary assists from game event data.
    """
    assists_dict = dict()

    for period in period_events:
        events = period_events[period]
        for event in events:
            if event['type'] == 'goal':
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


if __name__ == '__main__':

    # setting up source and target paths
    src_path = os.path.join('data', GAME_SRC)
    tgt_path = os.path.join('data', PLAYER_GAME_STATS_TGT)

    # loading games
    games = json.loads(open(src_path).read())

    # loading existing player game stats
    if os.path.isfile(tgt_path):
        player_game_stats = json.loads(open(tgt_path).read())
    else:
        player_game_stats = list()

    # retrieving set of games already having retrieved player stats for
    registered_games = set([pg['game_id'] for pg in player_game_stats])

    for game in games[:]:

        # skipping already processed games
        if game['game_id'] in registered_games:
            continue

        print("+ Retrieving player stats for %s (%d) vs. %s (%d) [%d]" % (
            game['home_team'], game['home_score'],
            game['road_team'], game['road_score'], game['game_id']))
        single_player_game_stats = get_single_game_player_data(game['game_id'])
        player_game_stats.extend(single_player_game_stats)

    open(tgt_path, 'w').write(
        json.dumps(player_game_stats, indent=2, default=str))