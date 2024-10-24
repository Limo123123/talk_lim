import re
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Response

from nc_py_api import NextcloudApp, talk_bot
from nc_py_api.ex_app import AppAPIAuthMiddleware, atalk_bot_msg, run_app, set_handlers

# Lebenszyklus des Bots
@asynccontextmanager
async def lifespan(app: FastAPI):
    set_handlers(app, enabled_handler)
    yield

APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)

# Bot global definieren
TALK_LIM_BOT = talk_bot.TalkBot("/talk_lim_bot", "TALK_LIM Bot", "Usage: `@talk_lim [message]`")


def talk_lim_bot_process_request(message: talk_bot.TalkBotMessage):
    try:
        # Ignoriere `system`-Nachrichten
        if message.object_name != "message":
            return
        
        # Suchen nach dem @talk_lim Aufruf und den Text danach
        r = re.search(r"@talk_lim\s*(\([^\)]*\))?\s*(.*)", message.object_content["message"], re.IGNORECASE)
        
        if r is None:
            return
        
        # Extrahiere den Text, der nach @talk_lim folgt, außer Klammern
        response_message = r.group(2).strip()
        
        if response_message:
            # Antwort zurücksenden
            TALK_LIM_BOT.send_message(f"Limo Bot: {response_message}", message)
    except Exception as e:
        TALK_LIM_BOT.send_message(f"Exception: {e}", message)


@APP.post("/talk_lim_bot")
async def talk_lim_bot(
    message: Annotated[talk_bot.TalkBotMessage, Depends(atalk_bot_msg)],
    background_tasks: BackgroundTasks,
):
    # Verarbeite die Anfragen im Hintergrund
    background_tasks.add_task(talk_lim_bot_process_request, message)
    # Sofortige Antwort an Nextcloud, dass wir die Anfrage erhalten haben
    return Response()


def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    print(f"enabled={enabled}")
    try:
        TALK_LIM_BOT.enabled_handler(enabled, nc)
    except Exception as e:
        return str(e)
    return ""


if __name__ == "__main__":
    run_app("main:APP", log_level="trace")
