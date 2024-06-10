import json

import redis
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import command

try:
    redis_client = redis.StrictRedis(host="localhost", port=6379, db=0)
    redis_client.ping()
except redis.ConnectionError:
    raise

project_json_path = "projects.json"
with open(project_json_path) as f:
    project_data = json.load(f)


class ProjectPlugin(MachineBasePlugin):
    @command("/project")
    async def project(self, command):
        text = command.text.strip()
        project_name = text.strip().lower()
        if not project_name:
            await command.say(
                "Please specify a technology. Usage: /project <tech_name>"
            )
            return
        try:
            cached_project = redis_client.get(project_name)
            if cached_project:
                project = json.loads(cached_project)
            else:
                project = project_data.get(project_name)
                if project:
                    redis_client.setex(project_name, 48 * 60 * 60, json.dumps(project))
        except Exception:
            await command.say(
                "There was an error processing your request. Please try again later."
            )
            return

        if project:
            project_list = "\n".join(project)
            message = (
                f"Hello , here the information about '{project_name}':\n{project_list}"
            )
        else:
            message = f"Hello , the project '{project_name}' is not recognized. Please try different query."

        await command.say(message)
