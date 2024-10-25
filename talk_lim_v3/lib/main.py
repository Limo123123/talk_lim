import re
import random
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
from fastapi import BackgroundTasks, Depends, FastAPI, Response
import httpx
from nc_py_api import NextcloudApp, talk_bot
from nc_py_api.ex_app import AppAPIAuthMiddleware, atalk_bot_msg, run_app, set_handlers

# Globale Einstellungen, To-Do-Liste und Zitat-Speicher
settings = {
    "experimentalfunctions": False,
    "notifications": True,
    "language": "Deutsch"  # Standard auf Deutsch
}

tasks = []  # Aufgabenliste
quotes = []  # Liste für Zitate
reminders = []  # Erinnerungen
trivia_questions = [  # Beispiel-Quizfragen
    ("Was ist die Hauptstadt von Frankreich?", "Paris"),
    ("Welcher Planet ist der größte im Sonnensystem?", "Jupiter"),
    ("Wer schrieb 'Sein oder Nichtsein'?", "Shakespeare")
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    set_handlers(app, enabled_handler)
    yield

APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)

# Bot definieren
TALK_LIM_BOT = talk_bot.TalkBot("/talk_lim_bot", "TALK_LIM Bot", "Usage: `@talk_lim [command]`")

# Hauptfunktion zur Verarbeitung von Bot-Anfragen
def talk_lim_bot_process_request(message: talk_bot.TalkBotMessage):
    try:
        if message.object_name != "message":
            return

        message_text = message.object_content["message"]

        # Bot-Einstellungen bearbeiten
        if "@talk_lim settings botrule" in message_text:
            if "experimentalfunctions" in message_text:
                new_setting = message_text.split("experimentalfunctions", 1)[1].strip().lower()
                if new_setting in ["true", "false"]:
                    settings["experimentalfunctions"] = new_setting == "true"
                    TALK_LIM_BOT.send_message(
                        f"Limo Bot: Experimentelle Funktionen auf {new_setting} gesetzt.", message
                    )
                else:
                    TALK_LIM_BOT.send_message("Limo Bot: Ungültige Einstellung. Verwende 'true' oder 'false'.", message)

            elif "language" in message_text:
                new_language = message_text.split("language", 1)[1].strip().lower()
                if new_language in ["deutsch", "english"]:
                    settings["language"] = "Deutsch" if new_language == "deutsch" else "English"
                    TALK_LIM_BOT.send_message(
                        f"Limo Bot: Sprache auf {settings['language']} gesetzt.", message
                    )
                else:
                    TALK_LIM_BOT.send_message("Limo Bot: Ungültige Sprache. Verwende 'deutsch' oder 'english'.", message)

            elif "list" in message_text:
                setting_list = "\n".join([f"{key}: {value}" for key, value in settings.items()])
                TALK_LIM_BOT.send_message(f"Limo Bot: Einstellungen:\n{setting_list}", message)

        # Aufgabenfunktionen
        elif "@talk_lim add task" in message_text:
            task = message_text.split("add task", 1)[1].strip()
            tasks.append(task)
            TALK_LIM_BOT.send_message(f"Limo Bot: Aufgabe hinzugefügt - '{task}'", message)

        elif "@talk_lim list tasks" in message_text:
            task_list = "\n".join([f"{i + 1}. {t}" for i, t in enumerate(tasks)])
            TALK_LIM_BOT.send_message(f"Limo Bot: Aufgaben:\n{task_list}", message)

        elif "@talk_lim remove task" in message_text:
            try:
                task_index = int(message_text.split("remove task", 1)[1].strip()) - 1
                removed_task = tasks.pop(task_index)
                TALK_LIM_BOT.send_message(f"Limo Bot: Entfernte Aufgabe - '{removed_task}'", message)
            except (IndexError, ValueError):
                TALK_LIM_BOT.send_message("Limo Bot: Ungültige Aufgabennummer.", message)

        # Mathe-Berechnungen
        elif "@talk_lim calc" in message_text:
            try:
                expression = message_text.split("calc", 1)[1].strip()
                result = eval(expression)
                TALK_LIM_BOT.send_message(f"Limo Bot: Das Ergebnis von {expression} ist {result}", message)
            except Exception:
                TALK_LIM_BOT.send_message("Limo Bot: Ungültige Berechnung.", message)

        # Datum und Uhrzeit
        elif "@talk_lim time" in message_text:
            current_time = datetime.now().strftime("%H:%M:%S")
            TALK_LIM_BOT.send_message(f"Limo Bot: Aktuelle Uhrzeit ist {current_time}", message)

        elif "@talk_lim date" in message_text:
            current_date = datetime.now().strftime("%Y-%m-%d")
            TALK_LIM_BOT.send_message(f"Limo Bot: Heutiges Datum ist {current_date}", message)

        # Hilfebefehl
        elif "@talk_lim help" in message_text:
            help_message = """
            Limo Bot Befehle:
            - @talk_lim add task [Aufgabe]: Eine Aufgabe zur Aufgabenliste hinzufügen.
            - @talk_lim list tasks: Alle Aufgaben auflisten.
            - @talk_lim remove task [Aufgabennummer]: Eine Aufgabe nach Nummer entfernen.
            - @talk_lim calc [Ausdruck]: Eine mathematische Berechnung durchführen.
            - @talk_lim time: Die aktuelle Uhrzeit anzeigen.
            - @talk_lim date: Das heutige Datum anzeigen.
            - @talk_lim settings botrule experimentalfunctions true/false: Experimentelle Funktionen aktivieren/deaktivieren.
            - @talk_lim settings botrule language [deutsch/english]: Sprache einstellen.
            - @talk_lim settings botrule list: Aktuelle Einstellungen auflisten.
            - @talk_lim add quote [Zitat]: Ein Zitat hinzufügen.
            - @talk_lim list quotes: Alle gespeicherten Zitate auflisten.
            - @talk_lim random quote: Ein zufälliges Zitat anzeigen.
            - @talk_lim start quiz: Ein Trivia-Quiz starten (experimentell).
            - @talk_lim add reminder [Zeit] [Nachricht]: Eine Erinnerung hinzufügen (experimentell).
            """
            if settings["experimentalfunctions"]:
                help_message += "- @talk_lim currency [Betrag] [von_Währung] to [zu_Währung]: Währungsumrechnung (experimentell).\n"
                help_message += "- @talk_lim start quiz: Ein Trivia-Quiz starten (experimentell).\n"
            TALK_LIM_BOT.send_message(f"Limo Bot: Hilfe:\n{help_message}", message)

        # Währungsrechner (experimentell)
        elif settings["experimentalfunctions"] and "@talk_lim currency" in message_text:
            parts = re.findall(r"currency\s(\d+)\s(\w+)\sto\s(\w+)", message_text, re.IGNORECASE)
            if parts:
                amount, from_currency, to_currency = parts[0]
                conversion = convert_currency(float(amount), from_currency.upper(), to_currency.upper())
                if conversion:
                    TALK_LIM_BOT.send_message(
                        f"Limo Bot: {amount} {from_currency} entspricht ungefähr {conversion:.2f} {to_currency}", message
                    )
                else:
                    TALK_LIM_BOT.send_message("Limo Bot: Währungsumrechnung fehlgeschlagen.", message)
            else:
                TALK_LIM_BOT.send_message("Limo Bot: Ungültiger Währungsbefehl.", message)

        # Trivia Quiz (experimentell)
        elif settings["experimentalfunctions"] and "@talk_lim start quiz" in message_text:
            question, answer = random.choice(trivia_questions)
            TALK_LIM_BOT.send_message(f"Limo Bot Quiz: {question}", message)
            # Hier kannst du die Antwort speichern oder eine Interaktion hinzufügen

        # Erinnerungsfunktion (experimentell)
        elif settings["experimentalfunctions"] and "@talk_lim add reminder" in message_text:
            parts = message_text.split("add reminder", 1)[1].strip().split(" ", 1)
            if len(parts) == 2:
                time, reminder_message = parts
                reminders.append((time, reminder_message))
                TALK_LIM_BOT.send_message(f"Limo Bot: Erinnerung für '{reminder_message}' um '{time}' hinzugefügt.", message)
            else:
                TALK_LIM_BOT.send_message("Limo Bot: Ungültiger Erinnerungsbefehl. Verwende '@talk_lim add reminder [Zeit] [Nachricht]'.", message)

        # Zitate-Funktionen
        elif "@talk_lim add quote" in message_text:
            quote = message_text.split("add quote", 1)[1].strip()
            quotes.append(quote)
            TALK_LIM_BOT.send_message(f"Limo Bot: Zitat hinzugefügt - '{quote}'", message)

        elif "@talk_lim list quotes" in message_text:
            quote_list = "\n".join([f"{i + 1}. {q}" for i, q in enumerate(quotes)])
            TALK_LIM_BOT.send_message(f"Limo Bot: Zitate:\n{quote_list}", message)

        elif "@talk_lim random quote" in message_text:
            if quotes:
                random_quote = random.choice(quotes)
                TALK_LIM_BOT.send_message(f"Limo Bot: Zufälliges Zitat - '{random_quote}'", message)
            else:
                TALK_LIM_BOT.send_message("Limo Bot: Keine Zitate vorhanden.", message)

    except Exception as e:
        TALK_LIM_BOT.send_message(f"Limo Bot: Ein Fehler ist aufgetreten - {str(e)}", message)

@APP.post("/talk_lim_bot")
async def talk_lim_bot(
    message: Annotated[talk_bot.TalkBotMessage, Depends(atalk_bot_msg)],
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(talk_lim_bot_process_request, message)
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