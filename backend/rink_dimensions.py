#!/usr/bin/env python
# -*- coding: utf-8 -*-

from shapely.geometry import Point, Polygon

X_TO_M = 0.3048
Y_TO_M = 0.1524

HOME_GOAL_COORDS = [-87., 0.]
ROAD_GOAL_COORDS = [87., 0.]

HOME_GOAL = Point(X_TO_M * HOME_GOAL_COORDS[0], Y_TO_M * HOME_GOAL_COORDS[1])
ROAD_GOAL = Point(X_TO_M * ROAD_GOAL_COORDS[0], Y_TO_M * ROAD_GOAL_COORDS[1])

polygon_names = [
    'HOME_SLOT', 'ROAD_SLOT',
    'HOME_BLUE_LINE', 'ROAD_BLUE_LINE',
    'HOME_LEFT', 'ROAD_LEFT',
    'HOME_RIGHT', 'ROAD_RIGHT',
    'HOME_NEUTRAL_ZONE', 'ROAD_NEUTRAL_ZONE',
    'HOME_BEHIND_GOAL', 'ROAD_BEHIND_GOAL',
]

HOME_SLOT = [[52, 46], [67, 46], [87, 8], [87, -8], [67, -46], [52, -46]]
ROAD_SLOT = [[-52, 46], [-67, 46], [-87, 8], [-87, -8], [-67, -46], [-52, -46]]

HOME_BLUE_LINE = [[29, 100], [52, 100], [52, -100], [29, -100]]
ROAD_BLUE_LINE = [[-29, 100], [-52, 100], [-52, -100], [-29, -100]]

HOME_LEFT = [[52, 100], [87, 100], [87, 8], [67, 46], [52, 46]]
HOME_RIGHT = [[52, -100], [87, -100], [87, -8], [67, -46], [52, -46]]

ROAD_LEFT = [[-52, -100], [-87, -100], [-87, -8], [-67, -46], [-52, -46]]
ROAD_RIGHT = [[-52, 100], [-87, 100], [-87, 8], [-67, 46], [-52, 46]]

HOME_NEUTRAL_ZONE = [[0, 100], [0, -100], [29, -100], [29, 100]]
ROAD_NEUTRAL_ZONE = [[0, 100], [0, -100], [-29, -100], [-29, 100]]

HOME_BEHIND_GOAL = [[87, 100], [87, -100], [105, -100], [105, 100]]
ROAD_BEHIND_GOAL = [[-87, 100], [-87, -100], [-105, -100], [-105, 100]]

polygons = list(zip(
    polygon_names,
    [Polygon(
        [[X_TO_M * x, Y_TO_M * y] for x, y in globals()[poly_name]]
    ) for poly_name in polygon_names]
))

if __name__ == '__main__':

    for name, py in polygons:
        print(name)
        print(py)
