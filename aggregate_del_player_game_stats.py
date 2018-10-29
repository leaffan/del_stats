#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from datetime import timedelta

from collections import defaultdict

PLAYER_GAME_STATS_SRC = 'del_player_game_stats.json'
AGGREGATED_PLAYER_STATS_TGT = 'del_player_game_stats_aggregated.json'


TO_COLLECT = [
    'no', 'position', 'first_name', 'last_name', 'full_name', 'country',
    'shoots',
]
TO_AGGREGATE_INTS = [
    'game_played', 'goals', 'assists', 'primary_assists', 'secondary_assists',
    'points', 'pim', 'plus', 'minus', 'plus_minus', 'pp_goals', 'pp_assists',
    'pp_primary_assists', 'pp_secondary_assists', 'pp_points', 'sh_goals',
    'gw_goals', 'shots', 'shots_on_goal', 'shots_missed', 'shots_blocked',
    'faceoffs', 'faceoffs_won', 'faceoffs_lost', 'blocked_shots', 'shifts',
]
TO_AGGREGATE_TIMES = [
    'time_on_ice', 'time_on_ice_pp', 'time_on_ice_sh',
]


if __name__ == '__main__':

    src_path = os.path.join('data', PLAYER_GAME_STATS_SRC)
    tgt_path = os.path.join('data', AGGREGATED_PLAYER_STATS_TGT)

    player_game_stats = json.loads(open(src_path).read())

    print(len(player_game_stats))

    players_with_teams = set()

    player_data = dict()
    aggregated_stats = dict()
    aggregate_time_stats = dict()

    for game_stat_line in player_game_stats:

        player_team_key = (game_stat_line['player_id'], game_stat_line['team'])

        if player_team_key not in aggregated_stats:
            aggregated_stats[player_team_key] = defaultdict(int)
            aggregate_time_stats[player_team_key] = defaultdict(timedelta)
            player_data[player_team_key] = defaultdict(set)

        for attr in TO_COLLECT:
            player_data[player_team_key][attr].add(game_stat_line[attr])

        for attr in TO_AGGREGATE_INTS:
            aggregated_stats[player_team_key][attr] += game_stat_line[attr]

        for attr in TO_AGGREGATE_TIMES:
            aggregate_time_stats[player_team_key][attr] += timedelta(
                seconds=sum([x * y for x, y in zip(
                    [60, 60, 1],
                    [int(token) for token in game_stat_line[attr].split(":")]
                )])
            )

    aggregated_stats_as_list = list()

    for player_id, team in aggregated_stats:

        key = (player_id, team)

        for pd_item in player_data[key]:
            if len(player_data[key][pd_item]) > 1:
                print(
                    "+ %s (%s) registered with " % (
                        list(player_data[key]['full_name'])[-1], team) +
                    "multiple values for '%s': %s" % (
                        pd_item,
                        ", ".join([str(s) for s in player_data[key][pd_item]]))
                )

        basic_values = dict()
        basic_values['player_id'] = player_id
        basic_values['team'] = team

        for attr in TO_COLLECT:
            basic_values[attr] = list(player_data[key][attr])[-1]

        all_values = {
            **basic_values,
            **aggregated_stats[key], **aggregate_time_stats[key]
        }
        aggregated_stats_as_list.append(all_values)

    open(tgt_path, 'w').write(
        json.dumps(aggregated_stats_as_list, indent=2, default=str))
