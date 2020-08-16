#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import json

TGT_STATS_TPL = 'goalie_stats'

if __name__ == '__main__':

    if os.path.isfile("%s.json" % TGT_STATS_TPL):
        all_goalie_stats = json.loads(open("%s.json" % TGT_STATS_TPL).read())

    print(len(all_goalie_stats))

    flat_list = list()

    for goalie in all_goalie_stats:
        for stat_line in goalie['stats']:
            single_stat_line = dict()
            single_stat_line['name'] = goalie['name']
            single_stat_line['ep_id'] = goalie['ep_id']
            for key in stat_line:
                single_stat_line[key] = stat_line[key]
            single_stat_line['toi'] = "'" + single_stat_line['toi']
            flat_list.append(single_stat_line)

    tgt_csv_path = "%s.csv" % TGT_STATS_TPL

    keys = flat_list[0].keys()

    with open(tgt_csv_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\ufeff')
        dict_writer = csv.DictWriter(
            output_file, keys, delimiter=';', extrasaction='ignore',
            lineterminator='\n')
        dict_writer.writeheader()
        dict_writer.writerows(flat_list)
