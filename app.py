from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import datetime
import random
import json
import re
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Optional AI / Search libraries
try:
    import openai
    OPENAI_API_KEY = os.getenv("OPEN_API_KEY")
    openai.api_key = OPENAI_API_KEY
except Exception:
    openai = None

try:
    import wikipedia
except Exception:
    wikipedia = None

try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

app = Flask(__name__)
app.secret_key = "neeku_ndhuku_maawa"

# ------------------- LOGIN DATA -------------------
users = {}  # In-memory (replace with DB later)

# ------------------- DATA FILES -------------------
REMINDERS_FILE = "data/reminders.json"
TODO_FILE = "data/todo.json"
NOTES_FILE = "data/notes.json"
CALENDAR_FILE = "data/calendar.json"

# ------------------- HELPERS -------------------
def load_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def translate_text(text, target_lang="en"):
    return text

def get_directions_osrm(origin, destination):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{origin};{destination}?overview=false&annotations=duration,distance"
        data = requests.get(url, timeout=8).json()
        if "routes" in data and len(data["routes"]) > 0:
            route = data["routes"][0]
            duration_sec = route["duration"]
            distance_m = route["distance"]
            eta_text = f"{int(duration_sec // 60)} mins"
            distance_text = f"{int(distance_m / 1000)} km"
            return {"eta_text": eta_text, "distance_text": distance_text}
        return {"error": "No route found."}
    except Exception as e:
        return {"error": str(e)}

# ------------------- LOGIN ROUTES -------------------
@app.route('/')
def home():
    if "user" in session:
        return redirect(url_for("index"))
    return redirect(url_for("login"))

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        if email in users and check_password_hash(users[email], password):
            session['user'] = email
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password", "error")
    return render_template("login.html")

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        if email in users:
            flash("Email already registered!", "error")
        else:
            users[email] = generate_password_hash(password)
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
    return render_template("login.html", register=True)

@app.route('/logout')
def logout():
    session.pop("user", None)
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

# ------------------- ASSISTANT ROUTES -------------------
@app.route("/index")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    if "user" not in session:
        return jsonify({"reply": "Please login first!"})

    user_msg = request.json.get("message", "").strip()
    user_msg_lower = user_msg.lower()
    target_lang = "en"

    # -------- Greetings --------
    greetings = {
        "hi": ["Heyy! Best hi ever 😎", "Hello! How's life?", "Hiya! What's up?"],
        "hello": ["Hello hello! How's your day?", "Hey! Glad you said hi 😄"],
        "good morning": ["Morning! Rise & shine ☀️", "Good morning bro! Coffee ready? ☕"],
        "good afternoon": ["Good afternoon! Lunch time 🍔", "Hey! Chill afternoon 😎"],
        "good evening": ["Evening vibes! Tea or coffee? ☕", "Good evening! Relax time 😄"],
        "good night": ["Night bro! Sweet dreams 🌙", "Sleep tight! 😴"],
        "thanks": ["Edisav le!", "Always bro! 😎"]
    }
    for key, replies in greetings.items():
        if key in user_msg_lower:
            return jsonify({"reply": translate_text(random.choice(replies), target_lang)})

    # -------- Traffic / Directions --------
    m_tr1 = re.search(r"(traffic|directions|route)\s+from\s+(.+?)\s+to\s+(.+)$", user_msg_lower)
    m_tr2 = re.search(r"traffic.*\bto\s+(.+?)\s+from\s+(.+)$", user_msg_lower)
    if m_tr1 or m_tr2:
        if m_tr1:
            origin = m_tr1.group(2).strip()
            dest = m_tr1.group(3).strip()
        else:
            dest = m_tr2.group(1).strip()
            origin = m_tr2.group(2).strip()
        res = get_directions_osrm(origin, dest)
        if "error" in res:
            out = f"Couldn't fetch traffic right now. {res['error']}"
        else:
            out = f"Route: {origin} → {dest}\nETA: {res['eta_text']}\nDistance: {res['distance_text']}"
        return jsonify({"reply": translate_text(out, target_lang)})

    # -------- Weather --------
    if "weather" in user_msg_lower:
        city = "Hyderabad"
        WEATHER_API_KEY =  os.getenv("WEATHER_API_KEY")
        try:
            url = f"https://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}&aqi=no"
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            if "current" in data:
                weather = data["current"]["condition"]["text"]
                temp = data["current"]["temp_c"]
                out = f"🌤 Weather in {city}: {weather}, {temp}°C"
                return jsonify({"reply": translate_text(out, target_lang)})
            else:
                return jsonify({"reply": translate_text("Weather info not found for this city.", target_lang)})
        except requests.exceptions.RequestException as e:
            return jsonify({"reply": translate_text(f"Weather service error: {str(e)}", target_lang)})
        except ValueError:
            return jsonify({"reply": translate_text("Failed to parse weather data.", target_lang)})

    # -------- Time & Date --------
    if "time" in user_msg_lower or "date" in user_msg_lower:
        now = datetime.datetime.now()
        out = f"🕒 Current date & time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        return jsonify({"reply": translate_text(out, target_lang)})

    # -------- Reminders / ToDo / Notes / Calendar --------
    if "padha chooskundham" in user_msg_lower:
        reminders = load_json(REMINDERS_FILE)
        if reminders:
            rem_text = "\n".join([f"{t} – {task}" for t, task in reminders.items()])
            return jsonify({"reply": translate_text(rem_text, target_lang)})
        return jsonify({"reply": translate_text("No reminders set.", target_lang)})

    if "set reminder" in user_msg_lower:
        match = re.search(r"set reminder (.+) at (.+)", user_msg_lower)
        if match:
            task, time_ = match.groups()
            reminders = load_json(REMINDERS_FILE)
            reminders[time_] = task
            save_json(REMINDERS_FILE, reminders)
            return jsonify({"reply": translate_text(f"Reminder set: {task} at {time_}", target_lang)})

    if "add task" in user_msg_lower:
        m = re.search(r"add task (.+)", user_msg_lower)
        if m:
            task = m.group(1)
            todo = load_json(TODO_FILE)
            todo[str(len(todo)+1)] = task
            save_json(TODO_FILE, todo)
            return jsonify({"reply": translate_text(f"Task added: {task}", target_lang)})

    if "show tasks" in user_msg_lower:
        todo = load_json(TODO_FILE)
        if todo:
            tasks = "\n".join([f"{k}. {v}" for k, v in todo.items()])
            return jsonify({"reply": translate_text(f"📝 Your tasks:\n{tasks}", target_lang)})
        return jsonify({"reply": translate_text("No tasks added yet.", target_lang)})

    if "add note" in user_msg_lower:
        m = re.search(r"add note (.+)", user_msg_lower)
        if m:
            note = m.group(1)
            notes = load_json(NOTES_FILE)
            notes[str(len(notes)+1)] = note
            save_json(NOTES_FILE, notes)
            return jsonify({"reply": translate_text(f"Note saved: {note}", target_lang)})

    if "show notes" in user_msg_lower:
        notes = load_json(NOTES_FILE)
        if notes:
            all_notes = "\n".join([f"{k}. {v}" for k, v in notes.items()])
            return jsonify({"reply": translate_text(f"📓 Your notes:\n{all_notes}", target_lang)})
        return jsonify({"reply": translate_text("No notes saved yet.", target_lang)})

    if "add event" in user_msg_lower:
        m = re.search(r"add event (.+) on (.+)", user_msg_lower)
        if m:
            event, date = m.groups()
            calendar = load_json(CALENDAR_FILE)
            calendar[date] = event
            save_json(CALENDAR_FILE, calendar)
            return jsonify({"reply": translate_text(f"Event '{event}' added on {date}", target_lang)})

    if "show events" in user_msg_lower:
        calendar = load_json(CALENDAR_FILE)
        if calendar:
            events = "\n".join([f"{d} – {ev}" for d, ev in calendar.items()])
            return jsonify({"reply": translate_text(f"📅 Events:\n{events}", target_lang)})
        return jsonify({"reply": translate_text("No events in calendar.", target_lang)})

    # -------- Jokes & Motivation --------
    if "joke" in user_msg_lower:
        jokes = [
            "Skeleton fight ante, guts ledu kabatti fight avvaledu 😎",
            "Computer ki break kavali ante, sleep mode ki pampindi 🤣"
        ]
        return jsonify({"reply": translate_text(random.choice(jokes), target_lang)})

    if "motivate" in user_msg_lower:
        quotes = [
            "Bro, chinna step tho start cheyyi… later, boom! 💥",
            "Stress? Oka deep breath, music blast, repeat 🔥"
        ]
        return jsonify({"reply": translate_text(random.choice(quotes), target_lang)})

    # -------- Free Online Courses --------
    if any(p in user_msg_lower for p in ["learn online", "free courses", "study online", "learn new skills"]):
        reply_text = "Hey! Check LearnTrack for free courses! <a href='https://learntrack-a1d1a.web.app' target='_blank'>👉 Click here</a>"
        return jsonify({"reply": translate_text(reply_text, target_lang)})

    # -------- AI / Translate --------
    if openai and ("solve" in user_msg_lower or "doubt" in user_msg_lower or "translate" in user_msg_lower):
        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=f"Answer or translate in simple language:\n{user_msg}",
                max_tokens=200,
                temperature=0.7,
            )
            out = response.choices[0].text.strip()
            return jsonify({"reply": translate_text(out, target_lang)})
        except Exception:
            return jsonify({"reply": translate_text("AI service unavailable.", target_lang)})

    # -------- Wikipedia / DuckDuckGo Fallback --------
    if wikipedia:
        try:
            summary = wikipedia.summary(user_msg, sentences=1)
            if summary:
                return jsonify({"reply": translate_text(summary, target_lang)})
        except Exception:
            pass

    if DDGS:
        try:
            results = list(DDGS().text(user_msg, max_results=2))
            if results:
                snippets = [r.get("body", "") for r in results if "body" in r]
                if snippets:
                    out = "\n\n".join(snippets)
                    return jsonify({"reply": translate_text(out, target_lang)})
        except Exception:
            pass

    # -------- Default Fallback --------
    default_responses = [
        "😄 Ready! Cheppu em kavali?",
        "Bro, cheppandi… em kavali?",
        "Heyy! Ready to chat 😎"
    ]
    return jsonify({"reply": translate_text(random.choice(default_responses), target_lang)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port, debug=False)