"""Nextcloud Talk Bot that echoes user messages."""

import re
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Response
from nc_py_api import NextcloudApp, talk_bot
from nc_py_api.ex_app import AppAPIAuthMiddleware, atalk_bot_msg, run_app, set_handlers

# Lifespan context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    set_handlers(app, enabled_handler)
    yield

APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)

# Define the bot globally
ECHO_BOT = talk_bot.TalkBot("/echo_talk_bot", "Echo Bot", "Usage: `@talk_lim your_message`")

def echo_talk_bot_process_request(message: talk_bot.TalkBotMessage):
    try:
        # Ignore system messages
        if message.object_name != "message":
            return
        
        # Check for the message starting with @talk_lim
        if message.object_content["message"].startswith("@talk_lim"):
            user_message = message.object_content["message"][len("@talk_lim"):].strip()
            # Send reply to chat
            ECHO_BOT.send_message(f"@talk_lim {user_message}", message)
    except Exception as e:
        ECHO_BOT.send_message(f"Exception: {e}", message)

@APP.post("/echo_talk_bot")
async def echo_talk_bot(
    message: Annotated[talk_bot.TalkBotMessage, Depends(atalk_bot_msg)],
    background_tasks: BackgroundTasks,
):
    # Process the request in the background
    background_tasks.add_task(echo_talk_bot_process_request, message)
    # Return Response immediately for Nextcloud
    return Response()

def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    print(f"enabled={enabled}")
    try:
        # Register or unregister the bot within the Nextcloud system
        ECHO_BOT.enabled_handler(enabled, nc)
    except Exception as e:
        return str(e)
    return ""

if __name__ == "__main__":
    run_app("main:APP", log_level="trace")