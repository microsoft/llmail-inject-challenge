import azure.functions as func

from apis import auth_api, internal_api, jobs_api, scenarios_api, teams_api, users_api, leaderboard_api
from queues import results_queue, deadletter_queue
from ui import ui

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Mount the /auth API
app.register_functions(auth_api)

# Mount the /internal API
app.register_functions(internal_api)

# Mount the /teams/.../jobs API
app.register_functions(jobs_api)

# Mount the /leaderboard API
app.register_functions(leaderboard_api)

# Mount the /scenarios API
app.register_functions(scenarios_api)

# Mount the /teams API
app.register_functions(teams_api)

# Mount the /users API
app.register_functions(users_api)

# Mount the queue triggers
app.register_functions(results_queue)
app.register_functions(deadletter_queue)

app.register_functions(ui)
