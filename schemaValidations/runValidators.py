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

with open("gameTeamStats.schema", "r") as content:
    gameTeamStatsSchema = (json.load(content))

with open("leagueTeamStats.schema", "r") as content:
    leagueTeamStatsSchema = (json.load(content))

with open("exampleFiles/shiftData.json", "r") as content:
    shiftTimeTestString = (json.load(content))

with open("exampleFiles/gameHeader.json", "r") as content:
    gameHeaderTestString = (json.load(content))

with open("exampleFiles/roster.json", "r") as content:
    rosterTestString = (json.load(content))

with open("exampleFiles/schedule.json", "r") as content:
    scheduleTestString = (json.load(content))

with open("exampleFiles/periodEvents.json", "r") as content:
    periodEventsTestString = (json.load(content))

with open("exampleFiles/gameTeamStats.json", "r") as content:
    gameTeamStatsTestString = (json.load(content))

with open("exampleFiles/leagueTeamStats.json", "r") as content:
    leagueTeamStatsTestString = (json.load(content))

validate(instance=shiftTimeTestString, schema=shiftTimeSchema)
validate(instance=gameHeaderTestString, schema=gameHeaderSchema)
validate(instance=rosterTestString, schema=rosterSchema)
validate(instance=scheduleTestString, schema=scheduleSchema)
validate(instance=periodEventsTestString, schema=periodEventsSchema)
validate(instance=gameTeamStatsTestString, schema=gameTeamStatsSchema)
validate(instance=leagueTeamStatsTestString, schema=leagueTeamStatsSchema)

print('All validations passed.')
