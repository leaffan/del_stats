from jsonschema import validate
import json

with open("shiftTime.schema", "r") as content:
    shiftTimeSchema = (json.load(content))

with open("gamePerTeam.schema", "r") as content:
    gamePerTeamSchema = (json.load(content))

with open("topGoalies.schema", "r") as content:
    topGoaliesSchema = (json.load(content))

with open("shiftData.json", "r") as content:
    shiftTimeTestString = (json.load(content))


validate(instance=shiftTimeTestString, schema=shiftTimeSchema)
