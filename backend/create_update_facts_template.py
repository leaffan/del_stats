#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates a new or updates an existing CSV template for registering certain
interesting facts for each scheduled DEL game.
"""

import os
import sys
import csv
import json
import yaml
import argparse

from dateutil.parser import parse

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

# defining fact categories
FACT_CATEGORIES = [
    "Fakt zur All-Time-Bilanz", "Fakt H2H aktuelle Saison",
    "Fakt Heim", "Fakt Auswärts",
    "Fakt Special Teams Heim", "Fakt Special Teams Auswärts",
    "Player To Watch Heim", "Player To Watch Auswärts",
    "Milestones Heim", "Milestones Auswärts"
]


def get_existing_facts(tgt_path):
    """
    Retrieves existing facts, registering all game ids for which they exist
    in the process.
    """
    game_ids = set()
    existing_facts = list()

    with open(tgt_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            existing_facts.append(row)
            game_ids.add(int(row['Spiel-ID']))

    return game_ids, existing_facts


def prepare_new_facts(schedule, game_ids):
    """
    Prepares new facts for games in specified schedule that are not already
    existing in given list of game IDs. Skipping fixtures that have not been
    specifically scheduled.
    """
    new_facts = list()

    for fixture in sorted(
        schedule, key=lambda k: (k['start_date'], k['game_id'])
    ):
        game_id = fixture['game_id']
        if game_id in game_ids:
            continue
        try:
            game_date_time = parse(fixture['start_date'])
            game_date = game_date_time.strftime("%d.%m.%Y")
            game_time = game_date_time.strftime("%H:%M")
        except ValueError as e:
            if str(e) == 'year 0 is out of range':
                print(
                    "+ Skipping unscheduled fixture '%s' between %s and %s" % (
                        fixture['round'],
                        fixture['home']['name'],
                        fixture['guest']['name']))
                continue
            game_date = None
            game_time = None
        for fact_category in FACT_CATEGORIES:
            line = dict()
            line['Spieltag'] = fixture['round']
            line['Datum'] = game_date
            line['Uhrzeit'] = game_time
            line['Spiel-ID'] = game_id
            line['Heim'] = fixture['home']['shortcut']
            line['Auswärts'] = fixture['guest']['shortcut']
            line['Fakt'] = fact_category
            line['Inhalt'] = ''
            new_facts.append(line)

    return new_facts


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Prepare or update CSV file for DEL matchday facts.')
    parser.add_argument(
        '--initial', dest='initial', required=False,
        action='store_true', help='Re-create template for matchday facts')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, default=2019,
        type=int, metavar='season to prepare matchday facts template for',
        choices=[2016, 2017, 2018, 2019],
        help="The season information will be processed for")

    args = parser.parse_args()

    initial = args.initial
    season = args.season

    schedule_src_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))
    facts_tgt_dir = CONFIG['del_facts_dir']

    src_path = os.path.join(schedule_src_dir, 'full_schedule.json')
    schedule = json.loads(open(src_path).read())
    print("+ Retrieved %d games from full league schedule" % len(schedule))

    if initial:
        # using a different file name for newly created templates to avoid
        # overwriting an existing facts file
        tgt_path = os.path.join(facts_tgt_dir, 'facts_template.csv')
    else:
        tgt_path = os.path.join(facts_tgt_dir, 'facts.csv')

    if not initial and not os.path.isfile(tgt_path):
        print("+ Target facts '%s' file not found" % tgt_path)
        sys.exit(1)

    game_ids = set()
    existing_facts = list()

    # retrieving existing facts
    if not initial:
        game_ids, existing_facts = get_existing_facts(tgt_path)

    print("+ Retrieved %d existing facts" % len(existing_facts))

    # preparing new facts
    new_facts = prepare_new_facts(schedule, game_ids)

    print("+ Prepared %d new facts" % len(new_facts))

    # csv output
    if initial:
        if new_facts:
            out_fields = new_facts[0].keys()
        else:
            print("+ No new facts prepared, no output possible")
            sys.exit(2)
    else:
        out_fields = existing_facts[0].keys()

    with open(tgt_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        dict_writer = csv.DictWriter(
            output_file, out_fields, delimiter=';', lineterminator='\n',
            extrasaction='ignore')
        dict_writer.writeheader()
        for existing_fact in existing_facts:
            dict_writer.writerow(existing_fact)
        for new_fact in new_facts:
            dict_writer.writerow(new_fact)

    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("+ Remember to change encoding of created file to ANSI manually.")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
