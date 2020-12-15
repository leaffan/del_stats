#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml

from datetime import datetime

from git import Repo

CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

if __name__ == '__main__':

    repo = Repo(CONFIG['tgt_base_dir'])
    # dealing with possibly existing untracked files first
    if repo.untracked_files:
        for untracked_file in repo.untracked_files:
            if os.path.splitext(untracked_file)[-1].lower() in ['.csv', '.json']:
                print("Adding previously untracked file '%s' to data repository" % untracked_file)
                repo.index.add([untracked_file])

    # dealing with changed files
    changed_files = [item.a_path for item in repo.index.diff(None)]
    if changed_files:
        repo.index.add(changed_files)

    if repo.is_dirty():
        commit_message = "Add changes through %s" % datetime.now().strftime("%Y-%m-%d %H:%M")
        print("Committing changes to data repository with message '%s'" % commit_message)
        repo.index.commit(commit_message)

    repo.close()
