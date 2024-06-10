import json

import redis
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command

# Initialize Redis client
try:
    redis_client = redis.StrictRedis(host="localhost", port=6379, db=0)
    redis_client.ping()
except redis.ConnectionError:
    raise

# Load JSON data
repo_json_path = "repo.json"
with open(repo_json_path) as f:
    repos_data = json.load(f)


def load_data_to_redis():
    for tech, repos in repos_data.items():
        redis_client.setex(tech, 48 * 60 * 60, json.dumps(repos))


# Load data to Redis on startup
load_data_to_redis()


class RepoPlugin(MachineBasePlugin):
    @command("/repo")
    async def repo(self, command):
        tech_name = command.text.strip().lower()

        if not tech_name:
            await command.say("Please specify a technology. Usage: /repo <tech_name>")
            return

        try:
            cached_repos = redis_client.get(tech_name)
            if cached_repos:
                repos = json.loads(cached_repos)
            else:
                repos = repos_data.get(tech_name)
                if repos:
                    redis_client.setex(tech_name, 48 * 60 * 60, json.dumps(repos))
        except Exception:
            await command.say(
                "There was an error processing your request. Please try again later."
            )
            return

        if repos:
            repos_list = "\n".join(repos)
            message = f"Hello, you can implement your '{tech_name}' knowledge here:\n{repos_list}"
        else:
            message = f"Hello, the technology '{tech_name}' is not recognized. Please try again."

        await command.say(message)
