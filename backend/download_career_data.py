#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import yaml
import requests

from lxml import html

CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

PLR_ID_REGEX = re.compile(R"\-(\d+)\/")

POSITIONS = {
    'Stürmer': 'FO', 'Verteidiger': 'DE', 'Torwart': 'GK'
}
SKATER_CATEGORIES = [
    'gp', 'g', 'a', 'pts', 'plus_minus', 'pim', 'ppg', 'shg', 'gwg', 'sog', 'sh_pctg'
]
GOALIE_CATEGORIES = [
    'gp', 'min', 'w', 't', 'l', 'so', 'ga', 'gaa', 'sv', 'sv_pctg'
]

ALL_PLAYERS_SRC = 'del_players.json'

CURRENT_SEASON = 2020

PLR_IDS_TO_SKIP = [1567]


if __name__ == '__main__':

    del_base_url = CONFIG['del_base_url']
    team_url_component = CONFIG['url_components']['team_profile']
    teams = CONFIG['teams']

    all_player_src_path = os.path.join(CONFIG['tgt_processing_dir'], ALL_PLAYERS_SRC)
    all_players = json.loads(open(all_player_src_path).read())

    # setting up target directories and paths
    tgt_dir = os.path.join(CONFIG['tgt_base_dir'], 'career_stats')
    if not os.path.isdir(tgt_dir):
        os.makedirs(tgt_dir)
    per_player_tgt_dir = os.path.join(tgt_dir, 'per_player')
    if not os.path.isdir(per_player_tgt_dir):
        os.makedirs(per_player_tgt_dir)
    tgt_path = os.path.join(tgt_dir, 'pre_season_career_stats.json')

    careers = list()
    # set of processed player ids to avoid duplicate entries in final data set
    # have to check whether this will lead to problems with legitimate player team changes during the season
    processed_plr_ids = set()
    # loading players ids where there is an existing career dataset available
    existing_career_datasets = set()
    pre_season_career_data = json.loads(open(tgt_path).read())
    for item in pre_season_career_data:
        existing_career_datasets.add(item['player_id'])

    for team_id in list(teams.keys())[:]:
        # setting up team page url
        team_url = "/".join((del_base_url, team_url_component, str(team_id)))
        print("+ Accessing %s to get links to player pages" % team_url)

        r = requests.get(team_url)
        doc = html.fromstring(r.text)

        # retrieving active players' urls from team page
        plr_urls = set(doc.xpath("//div[@class='profile']/ancestor::a/@href"))

        # TODO: download in parallel
        for plr_url in plr_urls:
            # setting up complete player page url
            plr_url = "/".join((del_base_url, plr_url))
            # retrieving player id from player page url
            match = re.search(PLR_ID_REGEX, plr_url)
            if match:
                plr_id = int(match.group(1))

            # checking whether current player has already been processed in this run, i.e. because he switched
            # teams but is still registered with both
            if plr_id in processed_plr_ids:
                print("=> Career data for player id %d (URL: %s) already collected previously" % (plr_id, plr_url))
                continue

            # checking whether an existing career dataset is already available for current player
            if plr_id not in existing_career_datasets:
                print("+ Downloading new dataset for player id %d from %s" % (plr_id, plr_url))
            else:
                continue

            print("+ Collecting data from %s" % plr_url)

            r = requests.get(plr_url)
            doc = html.fromstring(r.text)

            # retrieving player's position and full name
            position = full_name = ''
            position = doc.xpath("//span[@class='position']/text()")
            if position:
                position = POSITIONS.get(position.pop(0), 'NA')
            full_name = doc.xpath("//span[@class='name']/text()")
            if full_name:
                full_name = full_name.pop(0)

            # retrieving table rows with career stats from player page
            trs = doc.xpath("//th[@class='acenlef']/ancestor::tr")
            # setting up player career stats dictionary
            plr_career_stats = dict()
            plr_career_stats['player_id'] = plr_id
            # retrieving name of player from dictionary of all players
            plr_career_stats['first_name'] = all_players[str(plr_id)]['first_name']
            plr_career_stats['last_name'] = all_players[str(plr_id)]['last_name']
            # TODO: check and mark different position from dictionary of all players (?)
            plr_career_stats['position'] = position
            plr_career_stats['seasons'] = list()
            plr_career_stats['career'] = dict()

            # we no longer need to retrieve stats for current season from here as we're doing it separately in
            # processing step

            # getting stats from previous seasons
            for tr in trs:
                single_stat_line = dict()
                season_season_type_team = tr.xpath("th/span[@class='hidedesktop']/text()")
                # retrieving season, season type and team from table row
                if len(season_season_type_team) == 2:
                    season_season_type, team = season_season_type_team
                    if season_season_type.endswith('PO'):
                        season, season_type = season_season_type.split()
                    else:
                        season = season_season_type
                        season_type = 'RS'
                    try:
                        season = int(season.split("/")[0])
                    except ValueError:
                        # print("+ Unable to retrieve season from '%s'" % season)
                        continue
                    single_stat_line['season'] = season
                    single_stat_line['season_type'] = season_type
                    single_stat_line['team'] = team
                # retrieving full career season from according table rows
                else:
                    career_type = season_season_type_team.pop(0)
                    if career_type.endswith('Hauptrunden'):
                        season_type = 'RS'
                    elif career_type.endswith('Playoffs'):
                        season_type = 'PO'
                    else:
                        season_type = 'all'
                    single_stat_line['season_type'] = season_type

                # retrieving table cells in table row
                tds = tr.xpath("td/text()")

                # skipping seasons when player didn't play at all
                if tds[0].startswith('0'):
                    continue

                # retrieving skater stats
                if position != 'GK':
                    for category, td in zip(SKATER_CATEGORIES, tds):
                        if not td.endswith('%'):
                            single_stat_line[category] = int(td)
                        else:
                            # re-calculating shooting percentage
                            if single_stat_line['sog']:
                                single_stat_line[category] = round(
                                    single_stat_line['g'] / single_stat_line['sog'] * 100., 2)
                            else:
                                single_stat_line[category] = 0.0
                    single_stat_line['gpg'] = round(single_stat_line['g'] / single_stat_line['gp'], 2)
                    single_stat_line['apg'] = round(single_stat_line['a'] / single_stat_line['gp'], 2)
                    single_stat_line['ptspg'] = round(single_stat_line['pts'] / single_stat_line['gp'], 2)
                # retrieving goalie stats
                else:
                    for category, td in zip(GOALIE_CATEGORIES, tds):
                        if category in ['gaa', 'sv_pctg']:
                            continue
                        if category == 'min':
                            single_stat_line[category] = td
                        else:
                            single_stat_line[category] = int(td)
                    else:
                        # transforming minutes string to time on ice in seconds
                        minutes, seconds = [int(t) for t in single_stat_line['min'].split(":")]
                        single_stat_line['toi'] = minutes * 60 + seconds
                        # calculating shots against
                        single_stat_line['sa'] = single_stat_line['sv'] + single_stat_line['ga']
                        # re-calculating save percentage
                        if single_stat_line['sa']:
                            single_stat_line['sv_pctg'] = round(
                                100 - single_stat_line['ga'] / single_stat_line['sa'] * 100., 3)
                        # re-calculating goals against average
                        if single_stat_line['ga']:
                            single_stat_line['gaa'] = round(single_stat_line['ga'] * 3600 / single_stat_line['toi'], 2)
                        else:
                            single_stat_line['gaa'] = 0

                # adding single season stats to according container
                if 'season' in single_stat_line:
                    plr_career_stats['seasons'].append(single_stat_line)
                # adding full career stats to according container
                else:
                    plr_career_stats['career'][single_stat_line['season_type']] = single_stat_line

            # exporting single player career stats
            plr_career_stats['seasons'] = list(reversed(plr_career_stats['seasons']))
            if 'PO' in plr_career_stats['career']:
                plr_career_stats['career'] = {
                    'RS': plr_career_stats['career']['RS'],
                    'PO': plr_career_stats['career']['PO'],
                    'all': plr_career_stats['career']['all']
                }

            plr_tgt_path = os.path.join(per_player_tgt_dir, "%d.json" % plr_id)
            open(plr_tgt_path, 'w').write(json.dumps(plr_career_stats, indent=2))

            careers.append(plr_career_stats)
            # adding current player id to set of already processed ones
            processed_plr_ids.add(plr_id)

    careers = sorted(careers, key=lambda k: k['player_id'])

    if os.path.isfile(tgt_path):
        existing_careers = json.loads(open(tgt_path).read())
        # existing_careers = dict((plr['player_id'], plr) for plr in existing_careers)

    tgt_careers = existing_careers

    for plr in careers:
        tgt_careers.append(plr)

    # exporting all players' career stats to single file
    open(tgt_path, 'w').write(json.dumps(tgt_careers, indent=2))
