#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import json
import yaml
import operator

from collections import defaultdict

CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '..', 'config.yml')))

ALL_PLAYERS = os.path.join(CONFIG['tgt_processing_dir'], 'del_players.json')

SEASON = 2019


def get_scorers_in_period(scorer_combos, period):
    """
    Gets scorer/assistant combos in specified period.
    """
    for event in period:
        if event['type'] == 'goal':
            # skipping unassisted goals
            if not event['data']['assistants']:
                continue
            # retrieving scorer id
            scorer = event['data']['scorer']['playerId']
            # retrieving primary assistant id
            prim_assistant = event['data']['assistants'][0]['playerId']
            # increasing counter for scorer/assistant combination by one
            scorer_combos[(scorer, prim_assistant)] += 1

    return scorer_combos


if __name__ == '__main__':

    scorer_combos = defaultdict(int)

    # retrieving scorer/assistant combinations from game events
    for game_type in CONFIG['game_types']:
        src_dir = os.path.join(
            CONFIG['base_data_dir'], 'game_events', str(SEASON), str(game_type)
        )
        if not os.path.isdir(src_dir):
            continue
        for event_file in os.listdir(src_dir)[:]:
            periods = json.loads(open(os.path.join(
                src_dir, event_file)).read())
            for key in ['1', '2', '3', 'overtime']:
                scorer_combos = get_scorers_in_period(
                    scorer_combos, periods[key])

    # sorting scorer combos by number of occurrences
    scorer_combos = sorted(
        # scorer_combos.items(), key=lambda x: x[1], reverse=True)
        scorer_combos.items(), key=operator.itemgetter(1), reverse=True)

    # consolidating sorted list
    # loading list of all players
    all_players = json.loads(open(ALL_PLAYERS).read())
    final_list = list()
    for scorer_assistant_ids, count in scorer_combos:
        combo = dict()
        scorer_id, assistant_id = [str(id) for id in scorer_assistant_ids]
        scorer = all_players[scorer_id]
        assistant = all_players[assistant_id]
        combo['scorer_id'] = scorer_id
        combo['scorer'] = " ".join((scorer['first_name'], scorer['last_name']))
        combo['prim_assistant_id'] = assistant_id
        combo['prim_assistant'] = " ".join(
            (assistant['first_name'], assistant['last_name']))
        combo['count'] = count
        final_list.append(combo)

    # csv output
    out_fields = final_list[0].keys()

    tgt_csv_path = os.path.join(
        CONFIG['tgt_processing_dir'], "%d_scorer_combos.csv" % SEASON)

    with open(tgt_csv_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        dict_writer = csv.DictWriter(
            output_file, out_fields, delimiter=';', lineterminator='\n',
            extrasaction='ignore')
        dict_writer.writeheader()
        dict_writer.writerows(final_list)
