import re
from datetime import datetime
import random
import operator
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import BackgroundTasks, Depends, FastAPI, Response
from nc_py_api import NextcloudApp, talk_bot
from nc_py_api.ex_app import AppAPIAuthMiddleware, atalk_bot_msg, run_app, set_handlers

# Zitate für die Zufallsabfrage
quotes = [
    "The only limit to our realization of tomorrow is our doubts of today. – Franklin D. Roosevelt",
    "Do not watch the clock; do what it does. Keep going. – Sam Levenson",
    "Keep your face always toward the sunshine—and shadows will fall behind you. – Walt Whitman"
]

# To-Do-Liste speichern
todo_list = []

# Unterstützte Operatoren für Berechnungen
operations = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
}

# Lebenszyklus des Bots
@asynccontextmanager
async def lifespan(app: FastAPI):
    set_handlers(app, enabled_handler)
    yield

APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)

# Bot global definieren
TALK_LIM_BOT = talk_bot.TalkBot("/talk_lim_bot", "TALK_LIM Bot", "Usage: `@talk_lim [command]`")

# Funktion für das Verarbeiten der Anfragen
def talk_lim_bot_process_request(message: talk_bot.TalkBotMessage):
    try:
        # Ignoriere `system`-Nachrichten
        if message.object_name != "message":
            return

        # Nachricht analysieren
        message_text = message.object_content["message"]

        # To-Do hinzufügen
        if "@talk_lim add task" in message_text:
            task = message_text.split("@talk_lim add task", 1)[1].strip()
            if task:
                todo_list.append(task)
                TALK_LIM_BOT.send_message(f"Limo Bot: Task '{task}' added to your to-do list.", message)

        # To-Do Liste anzeigen
        elif "@talk_lim list tasks" in message_text:
            if todo_list:
                tasks = "\n".join([f"{idx + 1}. {task}" for idx, task in enumerate(todo_list)])
                TALK_LIM_BOT.send_message(f"Limo Bot: Here are your tasks:\n{tasks}", message)
            else:
                TALK_LIM_BOT.send_message("Limo Bot: Your to-do list is empty.", message)

        # To-Do entfernen
        elif "@talk_lim remove task" in message_text:
            try:
                task_number = int(message_text.split("@talk_lim remove task", 1)[1].strip())
                if 0 < task_number <= len(todo_list):
                    removed_task = todo_list.pop(task_number - 1)
                    TALK_LIM_BOT.send_message(f"Limo Bot: Task '{removed_task}' removed from your to-do list.", message)
                else:
                    TALK_LIM_BOT.send_message(f"Limo Bot: Invalid task number. Please provide a valid number.", message)
            except ValueError:
                TALK_LIM_BOT.send_message(f"Limo Bot: Invalid input. Please provide a valid task number.", message)

        # Berechnungen durchführen
        elif "@talk_lim calc" in message_text:
            calc_expression = message_text.split("@talk_lim calc", 1)[1].strip()
            try:
                # Verarbeite die Berechnung
                match = re.match(r"(\d+)\s*([\+\-\*\/])\s*(\d+)", calc_expression)
                if match:
                    num1 = int(match.group(1))
                    operator = match.group(2)
                    num2 = int(match.group(3))
                    if operator in operations:
                        result = operations[operator](num1, num2)
                        TALK_LIM_BOT.send_message(f"Limo Bot: The result of {num1} {operator} {num2} is {result}", message)
                    else:
                        TALK_LIM_BOT.send_message("Limo Bot: Unsupported operator.", message)
                else:
                    TALK_LIM_BOT.send_message("Limo Bot: Invalid calculation format.", message)
            except Exception as e:
                TALK_LIM_BOT.send_message(f"Limo Bot: Error in calculation: {e}", message)

        # Zeit und Datum Abfragen
        elif "@talk_lim time" in message_text:
            current_time = datetime.now().strftime("%H:%M:%S")
            TALK_LIM_BOT.send_message(f"Limo Bot: Current time is {current_time}", message)

        elif "@talk_lim date" in message_text:
            current_date = datetime.now().strftime("%Y-%m-%d")
            TALK_LIM_BOT.send_message(f"Limo Bot: Today's date is {current_date}", message)

        # Zufälliges Zitat
        elif "@talk_lim quote" in message_text:
            random_quote = random.choice(quotes)
            TALK_LIM_BOT.send_message(f"Limo Bot: {random_quote}", message)

        # Standardantwort, falls kein spezifischer Befehl
        else:
            r = re.search(r"@talk_lim\s*(\([^\)]*\))?\s*(.*)", message_text, re.IGNORECASE)
            if r:
                response_message = r.group(2).strip()
                if response_message:
                    TALK_LIM_BOT.send_message(f"Limo Bot: {response_message}", message)

    except Exception as e:
        TALK_LIM_BOT.send_message(f"Exception: {e}", message)

# Endpunkt für den Bot
@APP.post("/talk_lim_bot")
async def talk_lim_bot(
    message: Annotated[talk_bot.TalkBotMessage, Depends(atalk_bot_msg)],
    background_tasks: BackgroundTasks,
):
    # Verarbeite die Anfragen im Hintergrund
    background_tasks.add_task(talk_lim_bot_process_request, message)
    # Sofortige Antwort an Nextcloud, dass wir die Anfrage erhalten haben
    return Response()

# Aktivierung und Deaktivierung des Bots
def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    print(f"enabled={enabled}")
    try:
        TALK_LIM_BOT.enabled_handler(enabled, nc)
    except Exception as e:
        return str(e)
    return ""

# Anwendung starten
if __name__ == "__main__":
    run_app("main:APP", log_level="trace")

