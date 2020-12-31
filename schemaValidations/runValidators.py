from jsonschema import validate
import json

with open("shiftTime.schema", "r") as content:
    shiftTimeSchema = (json.load(content))

with open("gamePerTeam.schema", "r") as content:
    gamePerTeamSchema = (json.load(content))

with open("topGoalies.schema", "r") as content:
    topGoaliesSchema = (json.load(content))

with open("gameHeader.schema", "r") as content:
    gameHeaderSchema = (json.load(content))

with open("roster.schema", "r") as content:
    rosterSchema = (json.load(content))

with open("schedule.schema", "r") as content:
    scheduleSchema = (json.load(content))

with open("periodEvents.schema") as content:
    periodEventsSchema = (json.load(content))

with open("shiftData.json", "r") as content:
    shiftTimeTestString = (json.load(content))

with open("gameHeader.json", "r") as content:
    gameHeaderTestString = (json.load(content))

with open("roster.json", "r") as content:
    rosterTestString = (json.load(content))

with open("schedule.json", "r") as content:
    scheduleTestString = (json.load(content))

with open("periodEvents.json", "r") as content:
    periodEventsTestString = (json.load(content))

validate(instance=shiftTimeTestString, schema=shiftTimeSchema)
validate(instance=gameHeaderTestString, schema=gameHeaderSchema)
validate(instance=rosterTestString, schema=rosterSchema)
validate(instance=scheduleTestString, schema=scheduleSchema)
validate(instance=periodEventsTestString, schema=periodEventsSchema)

print('All validations passed.')