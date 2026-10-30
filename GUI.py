import os
import re
import json
import time
import base64
import io
import requests

os.environ["DISPLAY"] = ":0"
os.environ["XAUTHORITY"] = "/home/ste/.Xauthority"

import pyautogui

from datetime import datetime

# ============================================================
# CONFIGURAZIONE
# ============================================================

API_KEY = "KEY" #la chiave openrouter.ai personale

MODEL = "nvidia/nemotron-3.5-super-vl:free"

API_URL = "https://openrouter.ai/api/v1/chat/completions"

FOLDER_NAME = "Prova1234"
FILE_NAME = "Prova1234.txt"

MAX_RETRIES = 3
WAIT_AFTER_ACTION = 1.5

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

# ============================================================
# METRICHE
# ============================================================

metrics = {
    "actions_executed": 0,
    "grounding_attempts": 0,
    "grounding_failures": 0,
    "retries": 0,
    "verification_checks": 0,
    "verification_successes": 0,
    "completed": False,
    "start_time": time.time(),
    "operation_log": []
}


def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    metrics["operation_log"].append(entry)


def action_done(description):
    metrics["actions_executed"] += 1
    log(description)


def save_metrics():
    metrics["end_time"] = time.time()
    metrics["execution_time_seconds"] = round(
        metrics["end_time"] - metrics["start_time"], 2
    )

    with open("gui_agent_report.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4, ensure_ascii=False)

    print("\n========== RISULTATO ==========")
    print(json.dumps(metrics, indent=4, ensure_ascii=False))


# ============================================================
# CONTROLLO DISPLAY
# ============================================================

def initialize():
    if API_KEY == "INCOLLA_LA_TUA_CHIAVE_OPENROUTER":
        raise RuntimeError("Inserisci la API KEY OpenRouter nel codice.")

    print("[INFO] DISPLAY:", os.environ.get("DISPLAY"))
    print("[INFO] Risoluzione:", pyautogui.size())

    screenshot = pyautogui.screenshot()
    screenshot.save("debug_initial.png")

    print("[INFO] Screenshot iniziale salvato: debug_initial.png")
    print("[INFO] Premi ESC per interrompere.")
    time.sleep(2)


def check_abort():
    pass

# ============================================================
# SCREENSHOT E MODELLO VISION
# ============================================================

def screenshot_base64():
    image = pyautogui.screenshot()

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def ask_vision(prompt):
    check_abort()

    image_data = screenshot_base64()

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "temperature": 0,
        "max_tokens": 500,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }
        ]
    }

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=90
    )

    response.raise_for_status()

    result = response.json()
    content = result["choices"][0]["message"]["content"]

    if isinstance(content, list):
        content = " ".join(
            item.get("text", "") for item in content
            if isinstance(item, dict)
        )

    return content


def extract_json(text):
    text = text.strip()

    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("Il modello non ha restituito JSON valido.")

    return json.loads(text[start:end + 1])


# ============================================================
# GROUNDING VISIVO
# ============================================================

def locate_target(description, expected_terms=None):
    width, height = pyautogui.size()

    prompt = f"""
You are a GUI visual grounding system.

Current screen resolution: {width} x {height}.

Find this exact visible GUI element:
{description}

Rules:
- Only identify an element that is actually visible.
- Do not guess coordinates.
- Do not identify similar or unrelated elements.
- If the element is not visible, return found=false.
- Return the bounding box in normalized coordinates from 0 to 1000.
- bbox format: [left, top, right, bottom].
- visible_text must contain the text actually visible in the element.

Return ONLY this JSON:
{{
  "found": true,
  "visible_text": "exact visible text",
  "bbox": [100, 100, 200, 150]
}}

If not visible:
{{
  "found": false,
  "visible_text": "",
  "bbox": null
}}
"""

    for attempt in range(1, MAX_RETRIES + 1):
        check_abort()

        metrics["grounding_attempts"] += 1

        try:
            result = extract_json(ask_vision(prompt))

            if not result.get("found"):
                metrics["grounding_failures"] += 1
                continue

            visible = result.get("visible_text", "").strip().lower()

            if expected_terms:
                if not any(term.lower() in visible for term in expected_terms):
                    print("[GROUNDING] Testo non corrispondente:", visible)
                    metrics["grounding_failures"] += 1
                    continue

            bbox = result.get("bbox")

            if not isinstance(bbox, list) or len(bbox) != 4:
                metrics["grounding_failures"] += 1
                continue

            left, top, right, bottom = bbox

            if not all(isinstance(v, (int, float)) for v in bbox):
                metrics["grounding_failures"] += 1
                continue

            if not (
                0 <= left < right <= 1000
                and 0 <= top < bottom <= 1000
            ):
                metrics["grounding_failures"] += 1
                continue

            x = int(((left + right) / 2) * width / 1000)
            y = int(((top + bottom) / 2) * height / 1000)

            return x, y

        except Exception as error:
            print("[GROUNDING ERROR]", error)
            metrics["grounding_failures"] += 1

        if attempt < MAX_RETRIES:
            metrics["retries"] += 1
            time.sleep(1)

    return None


def require_target(description, expected_terms=None):
    coords = locate_target(description, expected_terms)

    if coords is None:
        raise RuntimeError(
            f"Elemento non identificato: {description}"
        )

    return coords


# ============================================================
# INTERAZIONI
# ============================================================

def hover_target(description, expected_terms=None):
    x, y = require_target(description, expected_terms)

    pyautogui.moveTo(x, y, duration=0.35)
    time.sleep(1.5)

    action_done("Hover: " + description)

    pyautogui.screenshot().save("debug_after_hover.png")


def click_target(description, expected_terms=None, double=False):
    x, y = require_target(description, expected_terms)

    if double:
        pyautogui.doubleClick(x, y, interval=0.15)
    else:
        pyautogui.click(x, y)

    action_done("Click: " + description)
    time.sleep(WAIT_AFTER_ACTION)

    pyautogui.screenshot().save("debug_after_click.png")


def verify_visible(description, expected_terms=None):
    metrics["verification_checks"] += 1

    coords = locate_target(description, expected_terms)

    if coords is None:
        return False

    metrics["verification_successes"] += 1
    return True


# ============================================================
# MENU CONTESTUALI
# ============================================================

def open_create_new_submenu():
    hover_target(
        "The context menu entry labelled Create New or New",
        ["Create New", "New"]
    )

    if not verify_visible(
        "The submenu entry labelled Folder",
        ["Folder"]
    ):
        raise RuntimeError(
            "Il sottomenu Create New non è apparso. "
            "Nessun clic è stato eseguito."
        )

    log("Sottomenu aperto: Folder riconosciuto.")


def select_folder():
    open_create_new_submenu()

    click_target(
        "The Folder entry inside the Create New submenu",
        ["Folder"]
    )

    time.sleep(1)


def select_text_file():
    open_create_new_submenu()

    if not verify_visible(
        "The Text File entry inside the Create New submenu",
        ["Blank File"]
    ):
        raise RuntimeError(
            "Text File non è visibile nel sottomenu."
        )

    click_target(
        "The Text File entry inside the Create New submenu",
        ["Blank File"]
    )

    time.sleep(1)


# ============================================================
# CREAZIONE CARTELLA
# ============================================================

def create_folder():
    width, height = pyautogui.size()

    # Area vuota in alto a destra del desktop.
    pyautogui.rightClick(
        int(width * 0.96),
        int(height * 0.24)
    )

    action_done("Click destro sul desktop.")
    time.sleep(1)

    if not verify_visible(
        "The desktop context menu entry Create New or New",
        ["Create New", "New"]
    ):
        raise RuntimeError("Menu contestuale desktop non riconosciuto.")

    select_folder()

    # Inserimento del nome nella casella di creazione.
    pyautogui.write(FOLDER_NAME, interval=0.06)
    pyautogui.press("enter")

    action_done("Inserimento nome cartella: " + FOLDER_NAME)
    time.sleep(2)

    if not verify_visible(
        "The desktop folder named " + FOLDER_NAME,
        [FOLDER_NAME]
    ):
        raise RuntimeError("La cartella non è stata verificata sul desktop.")

    log("Cartella creata e riconosciuta.")


# ============================================================
# APERTURA CARTELLA
# ============================================================

def open_folder():
    click_target(
        "The desktop folder named " + FOLDER_NAME,
        [FOLDER_NAME],
        double=True
    )

    time.sleep(2)

    if not verify_visible(
        "The opened file manager window showing the folder contents",
        ["File", "View"]
    ):
        # Secondo controllo: il file manager potrebbe avere
        # una barra dei menu differente.
        if not verify_visible(
            "An open file manager window displaying the folder contents"
        ):
            raise RuntimeError("Impossibile verificare l'apertura della cartella.")

    log("Cartella aperta.")


# ============================================================
# CREAZIONE FILE
# ============================================================

def create_text_file():
    width, height = pyautogui.size()

    # Clic destro nell'area centrale della finestra aperta.
    pyautogui.rightClick(
        int(width * 0.55),
        int(height * 0.48)
    )

    action_done("Click destro nell'area della cartella.")
    time.sleep(1)

    if not verify_visible(
        "The file manager context menu entry Create New or New",
        ["Create New", "New"]
    ):
        raise RuntimeError("Menu contestuale della cartella non riconosciuto.")

    select_text_file()

    pyautogui.write(FILE_NAME, interval=0.05)
    pyautogui.press("enter")

    action_done("Creazione file: " + FILE_NAME)
    time.sleep(2)

    if not verify_visible(
        "The file named " + FILE_NAME,
        [FILE_NAME]
    ):
        raise RuntimeError("Il file non è stato verificato.")

    log("File creato.")


# ============================================================
# SCRITTURA REPORT
# ============================================================

def open_and_write_report():
    click_target(
        "The file named " + FILE_NAME,
        [FILE_NAME],
        double=True
    )

    time.sleep(3)

    report = [
        "GUI AGENT - OPERATION REPORT",
        "============================",
        "",
        "Task: create a folder and a text file on Lubuntu.",
        "",
        "Operations performed:",
        "1. Opened the desktop context menu.",
        "2. Opened the Create New submenu.",
        "3. Created the folder Prova1234.",
        "4. Opened the folder.",
        "5. Created the file Prova1234.txt.",
        "6. Opened the text file.",
        "",
        "Execution date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "",
        "Result: operations completed up to report writing."
    ]

    for line in report:
        check_abort()
        pyautogui.write(line, interval=0.015)
        pyautogui.press("enter")

    pyautogui.hotkey("ctrl", "s")
    time.sleep(1)

    action_done("Report scritto e salvato.")

    pyautogui.hotkey("alt", "f4")
    time.sleep(2)

    log("Editor chiuso.")


# ============================================================
# CHIUSURA FILE MANAGER
# ============================================================

def close_file_manager():
    pyautogui.hotkey("alt", "f4")
    time.sleep(1)

    action_done("File manager chiuso.")

    if not verify_visible(
        "The Lubuntu desktop background and desktop icons"
    ):
        raise RuntimeError("Ritorno al desktop non verificato.")

    log("Desktop ripristinato.")


# ============================================================
# MAIN
# ============================================================

def main():
    try:
        initialize()

        log("Avvio esperimento GUI Agent.")

        create_folder()
        open_folder()
        create_text_file()
        open_and_write_report()
        close_file_manager()

        metrics["completed"] = True
        log("ESPERIMENTO COMPLETATO.")

    except KeyboardInterrupt as error:
        log("Interruzione: " + str(error))

    except pyautogui.FailSafeException:
        log("Interruzione di sicurezza PyAutoGUI.")

    except Exception as error:
        log("ERRORE: " + str(error))
        print("\n[STOP] L'agente si è fermato. Non esegue altri clic.")

    finally:
        save_metrics()


if __name__ == "__main__":
    main()