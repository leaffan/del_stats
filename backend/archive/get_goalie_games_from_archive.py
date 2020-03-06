#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml

import requests
from lxml import html

# loading configuration from external file
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

user = CONFIG['del_archive_user']
pwd = CONFIG['del_archive_pass']

GOALIE_URL = "/".join((CONFIG['del_archive_base_url'], "toptorhueter_%d.html"))


if __name__ == '__main__':

    goalies = dict()

    for season_id in range(1, 66):
        url = GOALIE_URL % season_id
        r = requests.get(url, auth=(user, pwd))
        doc = html.fromstring(r.text)

        season_info = doc.xpath("//button[@id='btnGroupDrop1']/text()")
        try:
            season = int(season_info[0].split()[-1].split("/")[0])
        except Exception:
            print("+ Unable to retrieve season from page content")
            continue
        season_type = season_info[1].strip()
        print("+ Collecting goalie stats for %s %d" % (season_type, season))

        goalie_names = doc.xpath("//tr[@class='acenter']/td[2]/a/text()")
        goalie_links = doc.xpath("//tr[@class='acenter']/td[2]/a/@href")
        goalie_games_played = doc.xpath("//tr[@class='acenter']/td[10]/text()")

        for name, link, gp in zip(
            goalie_names, goalie_links, goalie_games_played
        ):
            try:
                goalie_id = int(link.replace(".html", "").split("_")[-1])
                print(name, gp, goalie_id)
            except ValueError:
                print(
                    "\t+ Unable to retrieve goalie id " +
                    "for %s from link %s" % (name, link))
                continue
            if goalie_id not in goalies:
                goalies[goalie_id] = dict()
                goalies[goalie_id]['name'] = name
                goalies[goalie_id]['archive_id'] = goalie_id
                goalies[goalie_id]['games_played'] = 0
            goalies[goalie_id]['games_played'] += int(gp)

    goalies_as_list = sorted(
        goalies.values(), key=lambda i: i['games_played'], reverse=True)

    for item in goalies_as_list:
        print(item)

    tgt_path = os.path.join(
        CONFIG['base_data_dir'], 'archive', 'goalie_gp.json')

    open(tgt_path, 'w').write(json.dumps(goalies_as_list, indent=2))
