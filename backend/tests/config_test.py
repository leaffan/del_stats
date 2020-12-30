#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml

import requests

CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'config.yml')))


def test_mock():
    assert 1 == 1


def test_config_exists():
    assert type(CONFIG) is dict and CONFIG


def test_config_dirs():
    for key in CONFIG:
        if key.endswith('_dir'):
            assert os.path.isdir(CONFIG[key])


def test_config_urls():
    for key in CONFIG:
        if key.endswith('_url'):
            if 'archive' in key:
                continue
            r = requests.get(CONFIG[key])
            assert r.status_code == 200
