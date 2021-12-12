# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import sys
import traceback
from datetime import datetime
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    TurnContext,
    BotFrameworkAdapter,
    ConversationState,
    UserState,
    MemoryStorage
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity, ActivityTypes
from botmodule import InsightLuisBot
from config import DefaultConfig
import logging
import jinja2
import aiohttp_jinja2
from opencensus.ext.azure.log_exporter import AzureLogHandler
import os
# Bot components
CONFIG = DefaultConfig()
SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)
memstore = MemoryStorage()
constate = ConversationState(memstore)
userstate = UserState(memstore)
# AppInsights Logger 
name = __name__
logger = logging.getLogger(name)
logger.addHandler(AzureLogHandler(
        connection_string=CONFIG.INSIGHTS_CSTRING)
        )
# Error catcher
async def on_error(context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure
    #       application insights.
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity(
        "To continue to run this bot, please fix the bot source code."
    )
    # Send a trace activity if we're talking to the Bot Framework Emulator
    if context.activity.channel_id == "emulator":
        # Create a trace activity that contains the error object
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        # Send a trace activity, which will be displayed in Bot Framework Emulator
        await context.send_activity(trace_activity)
        logger.error(trace_activity)

ADAPTER.on_turn_error = on_error
# Create the bot
BOT = InsightLuisBot(constate, userstate, CONFIG.LUIS_APP_ID, CONFIG.LUIS_KEY, logger)

# Listen for incoming requests on /api/messages
async def messages(req: Request) -> Response:
    # Main bot message handler.
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        return Response(status=415)
    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""
    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return json_response(data=response.body, status=response.status)
    return Response(status=201)

# @routes.get('/{username}')
# async def web_chat(request: web.Request) -> web.Response:
#     context = {
#         'username': request.match_info.get("username", ""),
#         'current_date': 'January 27, 2017'
#     }
#     response = aiohttp_jinja2.render_template("example.html", request,
#                                           context=context)

#     return response
#     pass
#     return Response(status=201)

# Init function and main execution code for aiohttp deployment : 
def init_func(argv):
    APP = web.Application(middlewares=[aiohttp_error_middleware])
    APP.router.add_post("/api/messages", messages)
#     APP.router.add_route("/webchat", web_chat)
#     aiohttp_jinja2.setup(
#     APP, loader=jinja2.FileSystemLoader(os.path.join(os.getcwd(), "templates"))
# )
    return APP

if __name__ == "__main__":
    APP = init_func(None)
    try:
        web.run_app(APP, host="0.0.0.0", port=CONFIG.PORT)
    except Exception as error:
        raise error

# # Keeping below main execution code for local testing with Bot Framework Emulator 

# APP = web.Application(middlewares=[aiohttp_error_middleware])
# APP.router.add_post("/api/messages", messages)
# if __name__ == "__main__":
#     try:
#         web.run_app(APP, host="localhost", port=3978)
#     except Exception as error:
#         raise error