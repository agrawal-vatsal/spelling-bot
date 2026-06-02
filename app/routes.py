"""Custom FastAPI routes registered before the Pipecat runner sets up its own.

Imported at the top of app/bot.py so these routes are wired up as soon as the
runner loads the bot module — before _setup_frontend_routes() adds the default
redirect from GET / to /client/.  FastAPI uses first-match ordering, so whichever
handler is registered first wins.
"""

import os

from fastapi.responses import FileResponse
from pipecat.runner.run import app

_STATIC = os.path.join(os.path.dirname(__file__), "static")


@app.get("/", include_in_schema=False)
@app.get("/game", include_in_schema=False)
async def serve_game():
    return FileResponse(os.path.join(_STATIC, "index.html"))
