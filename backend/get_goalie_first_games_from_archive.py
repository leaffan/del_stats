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

SCORER_URL = "/".join((CONFIG['del_archive_base_url'], "topscorer_%d.html"))

TGT_DIR = os.path.join(CONFIG['base_data_dir'], 'archive')
tgt_path = os.path.join(TGT_DIR, 'goalie_shutouts_first_game.json')

user = CONFIG['del_archive_user']
pwd = CONFIG['del_archive_pass']

processed_goalies = set()
goalie_shutouts = list()


if __name__ == '__main__':
    for season_id in range(1, 65):
        url = SCORER_URL % season_id
        print(url)
        r = requests.get(url, auth=(user, pwd))
        doc = html.fromstring(r.text)

        goalie_trs = doc.xpath(
            "//table[@id='myTable']/tbody/tr/td[7][text() = 'G']/ancestor::tr")

        for tr in goalie_trs:
            full_name = tr.xpath("td/a/text()")[0]
            plr_link = tr.xpath("td/a/@href")[0]
            plr_id = int(plr_link.replace(".html", "").split("_")[-1])
            print("+ Working on %s" % full_name)

            if plr_id in processed_goalies:
                print("\t+ Goalie already processed")
                continue

            purl = "/".join((CONFIG['del_archive_base_url'], plr_link))
            pr = requests.get(purl, auth=(user, pwd))
            pdoc = html.fromstring(pr.text)

            first_game = pdoc.xpath(
                "//table[@class='table mt-2'][2]/tbody/tr[1]" +
                "/td/descendant-or-self::*/text()")

            if not first_game:
                continue

            result = first_game[3].split("(")[0]
            score_for, score_against = [int(x) for x in result.split(":")]

            if not score_against:
                goalie_shutout = dict()
                goalie_shutout['full_name'] = full_name
                goalie_shutout['plr_id'] = plr_id
                goalie_shutout['plr_url'] = purl
                goalie_shutout['game_date'] = first_game[1]
                goalie_shutout['opp_team'] = first_game[2]
                goalie_shutout['result'] = first_game[3]
                goalie_shutout['minutes'] = first_game[4]
                goalie_shutout['goals_against'] = first_game[5]
                goalie_shutout['saves'] = first_game[6]
                goalie_shutout['save_pctg'] = first_game[7]
                print(goalie_shutout)
                goalie_shutouts.append(goalie_shutout)

            processed_goalies.add(plr_id)

        open(tgt_path, 'w').write(json.dumps(goalie_shutouts, indent=2))
