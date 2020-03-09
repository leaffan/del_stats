#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import json
import yaml
from collections import defaultdict

CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '..', 'config.yml')))

ALL_PLAYERS = os.path.join(CONFIG['tgt_processing_dir'], 'del_players.json')
TGT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SEASON = 2019


def get_power_play_combos_in_period(
    period, game, pp_goals_by_team, pp_goals_by_team_forwards, all_players
):
    """
    Gets power play player/forward combos in specified period of given game.
    """
    for event in period:
        if event['type'] == 'goal':
            # skipping non power-play goals
            if not event['data']['balance'].startswith('PP'):
                continue
            # retrieving scoring team
            home_road = event['data']['team']
            if home_road == 'home':
                team = game['teamInfo']['home']['shortcut']
            else:
                team = game['teamInfo']['visitor']['shortcut']

            # if necessary creating new goal counter for
            # current team
            if team not in pp_goals_by_team:
                pp_goals_by_team[team] = defaultdict(int)
                pp_goals_by_team_forwards[team] = defaultdict(int)

            players_on_ice = list()
            forwards_on_ice = list()

            for plr in event['data']['attendants']['positive']:
                plr_id = plr['playerId']
                plr_pos = all_players[str(plr_id)]['position']
                # skipping goaltenders
                if plr_pos == 'GK':
                    continue
                # singling out forwards
                if plr_pos == 'FO':
                    forwards_on_ice.append(plr_id)
                # adding player id to list of all player ids on ice
                # for this goal
                players_on_ice.append(plr_id)

            # sorting collected player ids
            players_on_ice = sorted(players_on_ice)
            forwards_on_ice = sorted(forwards_on_ice)

            # incrementing goal counter for current combination of
            # players and forwards
            pp_goals_by_team[team][tuple(players_on_ice)] += 1
            pp_goals_by_team_forwards[team][tuple(forwards_on_ice)] += 1

    return pp_goals_by_team, pp_goals_by_team_forwards


if __name__ == '__main__':

    pp_goals_by_team = dict()
    pp_goals_by_team_forwards = dict()

    # loading list of all players
    all_players = json.loads(open(ALL_PLAYERS).read())

    # retrieving power play line combinations from goals in game events
    for game_type in CONFIG['game_types']:
        games_dir = os.path.join(
            CONFIG['base_data_dir'], 'game_info', str(SEASON), str(game_type))
        events_dir = os.path.join(
            CONFIG['base_data_dir'], 'game_events', str(SEASON), str(game_type)
        )
        if not (os.path.isdir(games_dir) and os.path.isdir(events_dir)):
            continue
        for game_src in os.listdir(games_dir):
            game = json.loads(open(os.path.join(games_dir, game_src)).read())
            event_src_path = os.path.join(events_dir, game_src)

            if not os.path.isfile(event_src_path):
                continue

            events = json.loads(open(event_src_path).read())

            for period_key in ['1', '2', '3', 'overtime']:

                pp_goals_by_team, pp_goals_by_team_forwards = (
                    get_power_play_combos_in_period(
                        events[period_key], game,
                        pp_goals_by_team, pp_goals_by_team_forwards,
                        all_players))

    # consolidating lists
    final_players = list()
    final_forwards = list()

    for team in pp_goals_by_team:
        for plr_ids in pp_goals_by_team[team]:
            plr_names = sorted([
                all_players[str(plr_id)]['last_name'] for plr_id in plr_ids])
            final_players.append(
                (team, ", ".join(plr_names), pp_goals_by_team[team][plr_ids]))
        for plr_ids in pp_goals_by_team_forwards[team]:
            plr_names = sorted([
                all_players[str(plr_id)]['last_name'] for plr_id in plr_ids])
            final_forwards.append((
                team, ", ".join(plr_names),
                pp_goals_by_team_forwards[team][plr_ids]))

    # preparing csv output
    csv_target_dir = os.path.join(CONFIG['tgt_processing_dir'], '_analysis')
    csv_target_path_players = os.path.join(
        csv_target_dir, "%d_pp_players_on_ice.csv" % SEASON)
    csv_target_path_forwards = os.path.join(
        csv_target_dir, "%d_pp_forwards_on_ice.csv" % SEASON)

    # csv output
    with open(
        csv_target_path_players, 'w', encoding='utf-8', newline=''
    ) as out_file:
        out_file.write('\ufeff')
        w = csv.writer(out_file, delimiter=';')
        w.writerow(['team', 'players_on_ice', 'pp_goals'])
        w.writerows(final_players)
    with open(
        csv_target_path_forwards, 'w', encoding='utf-8', newline=''
    ) as out_file:
        out_file.write('\ufeff')
        w = csv.writer(out_file, delimiter=';')
        w.writerow(['team', 'forwards_on_ice', 'pp_goals'])
        w.writerows(final_forwards)
