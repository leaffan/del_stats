#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

from collections import defaultdict

PLAYER_GAME_STATS_SRC = 'del_player_game_stats.json'
AGGREGATED_PLAYER_STATS_TGT = 'del_player_game_stats_aggregated.json'

TO_AGGREGATE = [
    'game_played', 'goals', 'assists', 'primary_assists', 'secondary_assists',
    'points', 'pim', 'plus', 'minus', 'plus_minus', 'pp_goals', 'pp_assists',
    'pp_primary_assists', 'pp_secondary_assists', 'pp_points', 'sh_goals',
    'gw_goals', 'shots', 'shots_on_goal', 'shots_missed', 'shots_blocked',
    'shot_pctg', 'faceoffs', 'faceoffs_won', 'faceoffs_lost', 'blocked_shots',
    'shifts'
]

if __name__ == '__main__':

    src_path = os.path.join('data', PLAYER_GAME_STATS_SRC)
    tgt_path = os.path.join('data', AGGREGATED_PLAYER_STATS_TGT)

    player_game_stats = json.loads(open(src_path).read())

    print(len(player_game_stats))

    players_with_teams = set()

    aggregated_stats = dict()

    for game_stat_line in player_game_stats:

        player_team_key = (game_stat_line['player_id'], game_stat_line['team'])

        if player_team_key not in aggregated_stats:
            aggregated_stats[player_team_key] = defaultdict(int)

        for attr in TO_AGGREGATE:
            aggregated_stats[player_team_key][attr] += game_stat_line[attr]

    aggregated_stats_as_list = list()

    for player_team_key in aggregated_stats:
        values = aggregated_stats[player_team_key]
        player_id, team = player_team_key
        values['player_id'] = player_id
        values['team'] = team
        aggregated_stats_as_list.append(values)

    open(tgt_path, 'w').write(
        json.dumps(aggregated_stats_as_list, indent=2, default=str))
