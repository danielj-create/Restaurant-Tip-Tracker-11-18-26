# ============================================================
# Restaurant Shift Tracker  -  shift_tracker.py
# Stage 4: Settings, Design and Final Testing
# ============================================================
# How to run: open this file in IDLE and press F5.
#
# How to run the automatic tests: close the app window, then
# type  run_checks()  in the IDLE Shell and press Enter.
#
# Saved shifts are stored in shift_data.json, in the same
# folder as this file.
# ============================================================

import tkinter as tk
from tkinter import messagebox
import datetime
import json
import os


# ============================================================
# SECTION 1: CONSTANTS AND DEFAULT SETTINGS
# ============================================================
# Constants are values that never change while the program runs.
# By tradition their names are written in CAPITAL letters.

APP_TITLE = "Restaurant Shift Tracker"

# The save file. It lives in the same folder as this program.
DATA_FILE_NAME = "shift_data.json"

# Every saved shift must have these keys, or the file counts as damaged.
SHIFT_KEYS = ["id", "date", "minutes", "wage_cents", "cash_tips_cents",
              "card_tips_cents", "tipout_percents", "notes"]

# The three tip-out categories, in the order they appear on screen.
TIPOUT_CATEGORIES = ["kitchen", "busser", "dishwasher"]

# Default settings. Money is always stored in cents ($15.00 = 1500)
# so we never have to worry about decimal rounding errors.
DEFAULT_SETTINGS = {
    "wage_cents": 1500,
    "kitchen_percent": 10,
    "busser_percent": 5,
    "dishwasher_percent": 0,
    "theme": "red",
}

# Preset theme colors. Cortland red is the default.
# Each is dark enough for white header text to stay readable.
THEMES = {
    "red": "#B00B00",
    "blue": "#1F4E99",
    "green": "#2E7D32",
}

# No shift can be longer than 24 hours.
MAX_MINUTES_PER_SHIFT = 24 * 60

# The rows shown in the Earnings Summary box: (key, label).
RESULT_ROWS = [
    ("total_tips", "Total tips"),
    ("kitchen", "Kitchen tip-out"),
    ("busser", "Busser tip-out"),
    ("dishwasher", "Dishwasher tip-out"),
    ("total_tipout", "Total tip-out"),
    ("take_home_tips", "Take-home tips"),
    ("base_pay", "Base pay"),
    ("total_earnings", "Total shift earnings"),
    ("hourly", "Effective hourly earnings"),
]

# Fonts: (font name, size, style)
TITLE_FONT = ("Helvetica", 20, "bold")
HEADING_FONT = ("Helvetica", 14, "bold")
NORMAL_FONT = ("Helvetica", 11)
BOLD_FONT = ("Helvetica", 11, "bold")
SMALL_FONT = ("Helvetica", 9)
# Courier is "monospaced": every letter is the same width,
# which lets the Shift History columns line up.
LIST_FONT = ("Courier", 11)


# ============================================================
# SECTION 2: JSON STORAGE FUNCTIONS
# ============================================================

def get_data_path():
    """Return the full path of shift_data.json, next to this .py file.
    __file__ is the location of this program. Building the path from it
    means the file is found even if IDLE starts in a different folder."""
    folder = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(folder, DATA_FILE_NAME)


def make_empty_data():
    """Return a brand-new data dictionary with no shifts."""
    return {
        "shifts": [],
        "weekly_goals": {},
        "settings": DEFAULT_SETTINGS.copy(),
        "next_shift_id": 1,
    }


def is_valid_data(data):
    """Check that loaded data has the four sections we expect,
    and that every shift has all of its values."""
    for section in ["shifts", "weekly_goals", "settings", "next_shift_id"]:
        if section not in data:
            return False

    for shift in data["shifts"]:
        for key in SHIFT_KEYS:
            if key not in shift:
                return False
    return True


def fill_missing_settings(data):
    """If a setting is missing from the file, use the default value."""
    for key in DEFAULT_SETTINGS:
        if key not in data["settings"]:
            data["settings"][key] = DEFAULT_SETTINGS[key]
    # An unknown theme name would crash the app, so fall back to red
    if data["settings"]["theme"] not in THEMES:
        data["settings"]["theme"] = "red"


def load_data():
    """Load saved data from shift_data.json.
    Returns two things: the data, and a warning message (or None).
    If the file doesn't exist yet, we start fresh with no warning.
    If the file is damaged, we set it aside and start fresh with a warning."""
    path = get_data_path()
    if not os.path.exists(path):
        return make_empty_data(), None

    try:
        # "with" opens the file and closes it again automatically
        with open(path, "r") as file:
            data = json.load(file)
        if not is_valid_data(data):
            raise ValueError("missing or wrong sections")
    except (ValueError, TypeError, OSError):
        # json.load raises a ValueError when the file isn't valid JSON,
        # and a TypeError can happen if the data is the wrong kind of value.
        # Rename the damaged file so it isn't overwritten by our next save.
        backup_path = os.path.join(os.path.dirname(path), "shift_data_damaged.json")
        try:
            os.replace(path, backup_path)
        except OSError:
            pass
        warning = ("Your saved data file was damaged and could not be read.\n"
                   "It was renamed to shift_data_damaged.json, and the app\n"
                   "will start with an empty shift history.")
        return make_empty_data(), warning

    fill_missing_settings(data)
    return data, None


def save_data(data):
    """Save all data to shift_data.json. Returns True if it worked.
    We write to a temporary file first, then swap it in with os.replace().
    If the computer crashes mid-save, the original file is still safe."""
    path = get_data_path()
    temp_path = path + ".tmp"
    try:
        with open(temp_path, "w") as file:
            json.dump(data, file, indent=2)   # indent=2 makes the file readable
        os.replace(temp_path, path)
        return True
    except OSError:
        return False


# ============================================================
# SECTION 3: CALCULATION AND VALIDATION FUNCTIONS
# ============================================================

def dollars_to_cents(text):
    """Turn text like '12.50' or '$12.50' into 1250 cents.
    A blank entry counts as 0.
    Returns None if the text is not a valid dollar amount."""
    text = text.strip().replace("$", "").replace(",", "")
    if text == "":
        return 0

    parts = text.split(".")      # "12.50" becomes ["12", "50"]
    if len(parts) > 2:
        return None              # more than one decimal point

    whole_part = parts[0]
    if whole_part == "":
        whole_part = "0"         # allows entries like ".50"

    decimal_part = ""
    if len(parts) == 2:
        decimal_part = parts[1]
    if len(decimal_part) > 2:
        return None              # more than two decimal places

    # Pad with zeros so ".5" means 50 cents, not 5 cents
    while len(decimal_part) < 2:
        decimal_part = decimal_part + "0"

    # isdigit() is False for letters and minus signs,
    # so this also rejects negative numbers.
    if not whole_part.isdigit() or not decimal_part.isdigit():
        return None

    return int(whole_part) * 100 + int(decimal_part)


def cents_to_text(cents):
    """Turn 1250 cents into the text '$12.50' for display."""
    dollars = cents / 100
    return f"${dollars:.2f}"     # :.2f means "show exactly 2 decimal places"


def cents_to_entry_text(cents):
    """Turn 1250 cents into '12.50' (no $ sign) for putting into an entry box."""
    return f"{cents / 100:.2f}"


def format_duration(minutes):
    """Turn 330 minutes into the text '5h 30m'."""
    return f"{minutes // 60}h {minutes % 60}m"


def parse_whole_number(text, lowest, highest):
    """Turn text into a whole number between lowest and highest.
    A blank entry counts as 0.
    Returns None if the text is invalid or out of range."""
    text = text.strip()
    if text == "":
        return 0
    if not text.isdigit():
        return None              # rejects letters, decimals and negatives
    number = int(text)
    if number < lowest or number > highest:
        return None
    return number


def parse_date(text):
    """Turn text like '2026-11-16' into a date.
    Returns None if the text is not a real date."""
    try:
        return datetime.datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None              # wrong format, or a date like Feb 30


def round_divide(top, bottom):
    """Divide two numbers and round to the nearest whole number.
    Adding 0.5 and then using int() to drop the decimals rounds
    halves up: 2.5 + 0.5 = 3.0 -> 3, and 2.4 + 0.5 = 2.9 -> 2.
    (Python's own round() would turn 2.5 into 2, which is why
    we don't use it for money.)"""
    return int(top / bottom + 0.5)


def calculate_tipouts(total_tips_cents, percents):
    """Work out how much each tip-out category is owed.
    Returns a dictionary of shares (in cents) and the total tip-out."""
    shares = {}
    shares_added = 0
    total_percent = 0
    last_category = None         # last category with a percent above 0

    for category in TIPOUT_CATEGORIES:
        percent = percents[category]
        share = round_divide(total_tips_cents * percent, 100)
        shares[category] = share
        shares_added = shares_added + share
        total_percent = total_percent + percent
        if percent > 0:
            last_category = category

    # The correctly rounded combined tip-out
    total_tipout = round_divide(total_tips_cents * total_percent, 100)

    # If rounding each share separately left us a cent off,
    # fix it on the last category so the amounts add up.
    if last_category is not None:
        shares[last_category] = shares[last_category] + (total_tipout - shares_added)

    return shares, total_tipout


def calculate_shift(shift):
    """Calculate all earnings for one shift.
    'shift' is a dictionary of the entered values.
    Returns a dictionary of results, all money in cents."""
    total_tips = shift["cash_tips_cents"] + shift["card_tips_cents"]
    shares, total_tipout = calculate_tipouts(total_tips, shift["tipout_percents"])
    take_home_tips = total_tips - total_tipout

    # Base pay = wage x hours. We use minutes, so divide by 60.
    base_pay = round_divide(shift["wage_cents"] * shift["minutes"], 60)
    total_earnings = base_pay + take_home_tips

    # We can't divide by zero, so hourly is None when no time was entered.
    if shift["minutes"] > 0:
        hourly = round_divide(total_earnings * 60, shift["minutes"])
    else:
        hourly = None

    results = {
        "total_tips": total_tips,
        "total_tipout": total_tipout,
        "take_home_tips": take_home_tips,
        "base_pay": base_pay,
        "total_earnings": total_earnings,
        "hourly": hourly,
    }
    for category in TIPOUT_CATEGORIES:
        results[category] = shares[category]
    return results


# ============================================================
# SECTION 4: SHIFT MANAGEMENT AND STATISTICS FUNCTIONS
# ============================================================
# These functions only change the data dictionary in memory.
# Saving to the file is a separate step (save_data), which lets
# run_checks() test them without touching your real saved shifts.

def find_shift(data, shift_id):
    """Return the shift with this ID, or None if there isn't one."""
    for shift in data["shifts"]:
        if shift["id"] == shift_id:
            return shift
    return None


def add_shift(data, shift):
    """Give a new shift the next ID number and add it to the list.
    IDs are never reused, even after a shift is deleted."""
    shift["id"] = data["next_shift_id"]
    data["next_shift_id"] = data["next_shift_id"] + 1
    data["shifts"].append(shift)
    return shift["id"]


def update_shift(data, shift_id, new_shift):
    """Replace an existing shift, keeping its ID. Returns True if found."""
    for index in range(len(data["shifts"])):
        if data["shifts"][index]["id"] == shift_id:
            new_shift["id"] = shift_id
            data["shifts"][index] = new_shift
            return True
    return False


def delete_shift(data, shift_id):
    """Remove the shift with this ID. Returns True if found."""
    for index in range(len(data["shifts"])):
        if data["shifts"][index]["id"] == shift_id:
            data["shifts"].pop(index)
            return True
    return False


def shift_sort_key(shift):
    """Tell sorted() what to sort each shift by: its date.
    Dates like '2026-11-16' sort correctly as text because the year
    comes first."""
    return shift["date"]


def get_sorted_shifts(data):
    """Return the shifts with the most recent date first."""
    return sorted(data["shifts"], key=shift_sort_key, reverse=True)


def get_week_start(day):
    """Return the Monday of the week that 'day' falls in.
    weekday() gives Monday = 0, Tuesday = 1, ... Sunday = 6,
    so subtracting that many days always lands on Monday."""
    return day - datetime.timedelta(days=day.weekday())


def get_week_shifts(data, week_start):
    """Return a list of the shifts from Monday week_start through Sunday."""
    week_end = week_start + datetime.timedelta(days=6)
    week_shifts = []
    for shift in data["shifts"]:
        shift_date = parse_date(shift["date"])
        if shift_date is None:
            continue                       # skip a shift with an unreadable date
        if shift_date >= week_start and shift_date <= week_end:
            week_shifts.append(shift)
    return week_shifts


def calculate_week_totals(data, week_start):
    """Add up earnings, time and shift count for one week.
    The average hourly rate is total earnings divided by total time,
    not an average of each shift's hourly rate."""
    total_earnings = 0
    total_minutes = 0
    week_shifts = get_week_shifts(data, week_start)
    for shift in week_shifts:
        total_earnings = total_earnings + calculate_shift(shift)["total_earnings"]
        total_minutes = total_minutes + shift["minutes"]

    if total_minutes > 0:
        hourly = round_divide(total_earnings * 60, total_minutes)
    else:
        hourly = None
    return {
        "earnings": total_earnings,
        "minutes": total_minutes,
        "shift_count": len(week_shifts),
        "hourly": hourly,
    }


def get_goal(data, week_start):
    """Return the goal (in cents) for a week, or None if none is set.
    Goals are stored by the week's Monday date, like '2026-11-16'."""
    return data["weekly_goals"].get(week_start.isoformat())


def set_goal(data, week_start, goal_cents):
    """Set a week's goal. A goal of 0 removes the goal for that week."""
    key = week_start.isoformat()
    if goal_cents == 0:
        if key in data["weekly_goals"]:
            del data["weekly_goals"][key]
    else:
        data["weekly_goals"][key] = goal_cents


def calculate_goal_progress(earned_cents, goal_cents):
    """Return the amount still needed and the percent of the goal reached."""
    remaining = goal_cents - earned_cents
    if remaining < 0:
        remaining = 0                      # the goal was passed
    percent = round_divide(earned_cents * 100, goal_cents)
    return remaining, percent


def earnings_by_date(data):
    """Combine all shifts on the same date.
    Returns a dictionary like {"2026-11-16": 23700, "2026-11-17": 9500}."""
    totals = {}
    for shift in data["shifts"]:
        earnings = calculate_shift(shift)["total_earnings"]
        if shift["date"] in totals:
            totals[shift["date"]] = totals[shift["date"]] + earnings
        else:
            totals[shift["date"]] = earnings
    return totals


def get_daily_totals(data, week_start):
    """Return a list of 7 earnings amounts, Monday through Sunday.
    Days with no shifts count as 0."""
    totals = earnings_by_date(data)
    daily = []
    for day_number in range(7):
        day = week_start + datetime.timedelta(days=day_number)
        daily.append(totals.get(day.isoformat(), 0))   # .get gives 0 if missing
    return daily


def date_total_key(pair):
    """Sort key for (date, earnings) pairs: sort by the earnings."""
    return pair[1]


def get_top_dates(data, how_many):
    """Return up to 'how_many' (date, earnings) pairs, highest earnings first."""
    pairs = []
    totals = earnings_by_date(data)
    for date_text in totals:
        pairs.append((date_text, totals[date_text]))
    pairs = sorted(pairs, key=date_total_key, reverse=True)
    return pairs[:how_many]               # [:5] keeps only the first 5 items


# ============================================================
# SECTION 5: TKINTER SCREEN FUNCTIONS
# ============================================================

def build_window(app):
    """Create the header, navigation buttons and content area."""
    root = app["root"]
    root.title(APP_TITLE)
    root.geometry("880x680")
    root.minsize(820, 640)

    color = THEMES[app["settings"]["theme"]]

    # Header: a colored bar with the app name in white
    header = tk.Frame(root, bg=color, padx=20, pady=12)
    header.pack(fill="x")
    header_label = tk.Label(header, text=APP_TITLE, font=TITLE_FONT,
                            bg=color, fg="white")
    header_label.pack(anchor="w")
    app["header"] = header                 # saved so apply_theme can recolor them
    app["header_label"] = header_label

    # Navigation buttons.
    # A button's command must be a function to call LATER, when it is
    # clicked. Writing command=show_dashboard(app) would run it right
    # away. "lambda:" makes a tiny unnamed function that, when the
    # button is clicked, runs show_dashboard(app) with our app dictionary.
    nav = tk.Frame(root, pady=8)
    nav.pack(fill="x", padx=20)
    tk.Button(nav, text="Dashboard", width=12, font=NORMAL_FONT,
              command=lambda: show_dashboard(app)).pack(side="left", padx=4)
    tk.Button(nav, text="Log Shift", width=12, font=NORMAL_FONT,
              command=lambda: show_log_shift(app)).pack(side="left", padx=4)
    tk.Button(nav, text="Shift History", width=12, font=NORMAL_FONT,
              command=lambda: show_history(app)).pack(side="left", padx=4)
    tk.Button(nav, text="Settings", width=12, font=NORMAL_FONT,
              command=lambda: show_settings(app)).pack(side="left", padx=4)

    # The content area: each screen function fills this frame
    content = tk.Frame(root, padx=20, pady=10)
    content.pack(fill="both", expand=True)
    app["content"] = content


def apply_theme(app):
    """Recolor the header after the theme changes. The other screens
    use the theme color automatically each time they are drawn."""
    color = THEMES[app["settings"]["theme"]]
    app["header"].config(bg=color)
    app["header_label"].config(bg=color)


def clear_content(app):
    """Remove everything from the content area before showing a new screen."""
    for widget in app["content"].winfo_children():
        widget.destroy()


# ---------- Dashboard screen ----------

def format_nice_date(day):
    """Turn a date into text like 'Mon Nov 16'."""
    return day.strftime("%a %b %d")


def show_dashboard(app):
    """Show the Dashboard for the week stored in app["week_start"].
    Everything is recalculated from the saved shifts each time,
    so it is always up to date after adding, editing or deleting."""
    clear_content(app)
    content = app["content"]
    week_start = app["week_start"]
    totals = calculate_week_totals(app["data"], week_start)

    build_week_navigation(app, content, week_start)

    cards = tk.Frame(content)
    cards.pack(fill="x", pady=(10, 0))
    summary_frame = tk.LabelFrame(cards, text="Week Summary", font=HEADING_FONT,
                                  padx=12, pady=8)
    summary_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    goal_frame = tk.LabelFrame(cards, text="Weekly Goal", font=HEADING_FONT,
                               padx=12, pady=8)
    goal_frame.grid(row=0, column=1, sticky="nsew")

    best_frame = tk.LabelFrame(cards, text="Best Days (all weeks)",
                               font=HEADING_FONT, padx=12, pady=8)
    best_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(10, 0))
    chart_frame = tk.LabelFrame(cards, text="Daily Earnings", font=HEADING_FONT,
                                padx=12, pady=8)
    chart_frame.grid(row=1, column=1, sticky="nsew", pady=(10, 0))

    build_week_summary(summary_frame, totals)
    build_goal_area(app, goal_frame, totals["earnings"])
    build_best_dates(app, best_frame)
    draw_week_chart(app, chart_frame, week_start)

    tk.Button(content, text="Log a New Shift", font=BOLD_FONT,
              command=lambda: show_log_shift(app)).pack(anchor="w", pady=12)


def build_week_navigation(app, parent, week_start):
    """Show which week is selected, with Previous, This Week and Next buttons."""
    week_end = week_start + datetime.timedelta(days=6)
    row = tk.Frame(parent)
    row.pack(fill="x")
    title = ("Week of " + format_nice_date(week_start) + " - " +
             format_nice_date(week_end) + ", " + str(week_end.year))
    tk.Label(row, text=title, font=HEADING_FONT).pack(side="left")

    tk.Button(row, text="Next Week >", font=NORMAL_FONT,
              command=lambda: change_week(app, 7)).pack(side="right")
    tk.Button(row, text="This Week", font=NORMAL_FONT,
              command=lambda: change_week(app, 0)).pack(side="right", padx=6)
    tk.Button(row, text="< Previous Week", font=NORMAL_FONT,
              command=lambda: change_week(app, -7)).pack(side="right")


def change_week(app, days):
    """Move the dashboard forward or back. days=0 jumps to the current week."""
    if days == 0:
        app["week_start"] = get_week_start(datetime.date.today())
    else:
        app["week_start"] = app["week_start"] + datetime.timedelta(days=days)
    show_dashboard(app)


def add_info_row(frame, row, label_text, value_text):
    """Add one 'label: value' line to a dashboard card."""
    tk.Label(frame, text=label_text, font=NORMAL_FONT).grid(
        row=row, column=0, sticky="w", pady=2)
    tk.Label(frame, text=value_text, font=BOLD_FONT).grid(
        row=row, column=1, sticky="e", pady=2, padx=(20, 0))


def build_week_summary(frame, totals):
    """Show the week's earnings, time worked, shift count and hourly average."""
    if totals["hourly"] is None:
        hourly_text = "No shifts yet"
    else:
        hourly_text = cents_to_text(totals["hourly"]) + "/hr"
    add_info_row(frame, 0, "Total earnings", cents_to_text(totals["earnings"]))
    add_info_row(frame, 1, "Hours worked", format_duration(totals["minutes"]))
    add_info_row(frame, 2, "Shifts worked", str(totals["shift_count"]))
    add_info_row(frame, 3, "Average hourly (with tips)", hourly_text)


# ---------- Settings screen ----------

def show_settings(app, message=""):
    """Show the Settings screen: default wage, default tip-outs and theme."""
    clear_content(app)
    content = app["content"]
    settings = app["settings"]
    tk.Label(content, text="Settings", font=HEADING_FONT).pack(anchor="w")
    if message != "":
        tk.Label(content, text=message, font=BOLD_FONT,
                 fg=THEMES[settings["theme"]]).pack(anchor="w")

    defaults_frame = tk.LabelFrame(content, text="Defaults for New Shifts",
                                   font=HEADING_FONT, padx=12, pady=8)
    defaults_frame.pack(anchor="w", pady=(8, 0))
    build_settings_entries(app, defaults_frame)
    tk.Label(defaults_frame, font=SMALL_FONT, justify="left",
             text="Changing these only affects new shifts. Saved shifts keep\n"
                  "the wage and tip-out percentages they were recorded with."
             ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

    theme_frame = tk.LabelFrame(content, text="Interface Color",
                                font=HEADING_FONT, padx=12, pady=8)
    theme_frame.pack(anchor="w", pady=(10, 0))
    build_theme_choices(app, theme_frame)

    tk.Button(content, text="Save Settings", font=BOLD_FONT,
              command=lambda: on_save_settings(app)).pack(anchor="w", pady=12)


def build_settings_entries(app, frame):
    """Create the entry boxes for the default wage and tip-out percents.
    They use the same keys as the Log Shift form ("wage", "kitchen", ...)
    so the same checking function, read_tipout_percents, works for both."""
    settings = app["settings"]
    fields = [
        ("wage", "Default hourly wage ($)", cents_to_entry_text(settings["wage_cents"])),
        ("kitchen", "Default kitchen tip-out (%)", str(settings["kitchen_percent"])),
        ("busser", "Default busser tip-out (%)", str(settings["busser_percent"])),
        ("dishwasher", "Default dishwasher tip-out (%)", str(settings["dishwasher_percent"])),
    ]
    app["settings_form"] = {}
    row = 0
    for key, label_text, start_value in fields:
        tk.Label(frame, text=label_text, font=NORMAL_FONT).grid(
            row=row, column=0, sticky="w", pady=3)
        entry = tk.Entry(frame, width=10, font=NORMAL_FONT)
        entry.insert(0, start_value)
        entry.grid(row=row, column=1, sticky="w", pady=3, padx=(10, 0))
        app["settings_form"][key] = entry
        row = row + 1


def build_theme_choices(app, frame):
    """Create one radio button per theme, each with a color sample.
    A StringVar is a special Tkinter variable that a group of radio
    buttons share: clicking a button stores that button's value in it."""
    app["theme_choice"] = tk.StringVar(value=app["settings"]["theme"])
    column = 0
    for theme_name in THEMES:
        tk.Radiobutton(frame, text=theme_name.capitalize(), font=NORMAL_FONT,
                       variable=app["theme_choice"], value=theme_name).grid(
            row=0, column=column, sticky="w")
        tk.Label(frame, text="      ", bg=THEMES[theme_name]).grid(
            row=0, column=column + 1, sticky="w", padx=(0, 24))
        column = column + 2


def on_save_settings(app):
    """Check the settings, store them, save the file and apply the theme."""
    form = app["settings_form"]
    wage = dollars_to_cents(form["wage"].get())
    if wage is None:
        show_input_error("The default wage must be a dollar amount like 15 or 15.50.")
        return
    percents = read_tipout_percents(form)
    if percents is None:
        return                              # an error was already shown

    # Change the existing settings dictionary, so app["settings"] and
    # app["data"]["settings"] (the same dictionary) both see the new values
    settings = app["settings"]
    settings["wage_cents"] = wage
    settings["kitchen_percent"] = percents["kitchen"]
    settings["busser_percent"] = percents["busser"]
    settings["dishwasher_percent"] = percents["dishwasher"]
    settings["theme"] = app["theme_choice"].get()

    message = "Settings saved."
    if not save_data(app["data"]):
        message = "Settings changed, but they could not be written to shift_data.json."
    apply_theme(app)
    show_settings(app, message)


def build_goal_area(app, frame, earned):
    """Show the week's goal, how much is left, a progress bar,
    and a box for setting or changing the goal."""
    goal = get_goal(app["data"], app["week_start"])
    if goal is None:
        add_info_row(frame, 0, "Goal", "Not set")
        add_info_row(frame, 1, "Remaining", "-")
        add_info_row(frame, 2, "Progress", "-")
        percent = 0
    else:
        remaining, percent = calculate_goal_progress(earned, goal)
        add_info_row(frame, 0, "Goal", cents_to_text(goal))
        add_info_row(frame, 1, "Remaining", cents_to_text(remaining))
        add_info_row(frame, 2, "Progress", str(percent) + "%")

    draw_progress_bar(app, frame, percent)

    entry_row = tk.Frame(frame)
    entry_row.grid(row=4, column=0, columnspan=2, sticky="w")
    tk.Label(entry_row, text="New goal ($):", font=NORMAL_FONT).pack(side="left")
    goal_entry = tk.Entry(entry_row, width=10, font=NORMAL_FONT)
    goal_entry.pack(side="left", padx=6)
    tk.Button(entry_row, text="Set Goal", font=NORMAL_FONT,
              command=lambda: on_set_goal(app, goal_entry)).pack(side="left")


def draw_progress_bar(app, frame, percent):
    """Draw a simple progress bar on a Canvas.
    A Canvas is a drawing area. (0, 0) is its top-left corner, and
    create_rectangle(x1, y1, x2, y2) draws a box between two corners."""
    bar_width = 260
    canvas = tk.Canvas(frame, width=bar_width, height=20, highlightthickness=0)
    canvas.grid(row=3, column=0, columnspan=2, sticky="w", pady=8)
    canvas.create_rectangle(0, 0, bar_width, 20, fill="#E0E0E0", outline="#B0B0B0")

    shown_percent = percent
    if shown_percent > 100:
        shown_percent = 100                # the bar stops when it is full
    filled_width = bar_width * shown_percent / 100
    if filled_width > 0:
        color = THEMES[app["settings"]["theme"]]
        canvas.create_rectangle(0, 0, filled_width, 20, fill=color, outline=color)


def on_set_goal(app, goal_entry):
    """Save a new goal for the selected week. Entering 0 removes the goal."""
    goal = dollars_to_cents(goal_entry.get())
    if goal is None or goal_entry.get().strip() == "":
        show_input_error("Enter the goal as a dollar amount, like 800 or 800.00.\n"
                         "Enter 0 to remove this week's goal.")
        return
    set_goal(app["data"], app["week_start"], goal)
    if not save_data(app["data"]):
        show_input_error("The goal could not be written to shift_data.json.")
    show_dashboard(app)


def build_best_dates(app, frame):
    """Show the highest-earning date and the top 5 dates.
    All shifts on the same date are added together first."""
    top_dates = get_top_dates(app["data"], 5)
    if len(top_dates) == 0:
        tk.Label(frame, text="No shifts saved yet.\nYour best days will appear here.",
                 font=NORMAL_FONT, justify="left").pack(anchor="w")
        return

    best_date, best_amount = top_dates[0]
    tk.Label(frame, text="Best day: " + best_date + "  " + cents_to_text(best_amount),
             font=BOLD_FONT).pack(anchor="w", pady=(0, 6))

    if len(top_dates) < 5:
        tk.Label(frame, text="Your top 5 days appear once you have shifts on "
                 "5 different dates (" + str(len(top_dates)) + " so far).",
                 font=NORMAL_FONT, wraplength=260, justify="left").pack(anchor="w")
        return

    rank = 1
    for date_text, amount in top_dates:
        line = str(rank) + ".  " + date_text + "    " + cents_to_text(amount)
        tk.Label(frame, text=line, font=NORMAL_FONT).pack(anchor="w")
        rank = rank + 1


def draw_week_chart(app, frame, week_start):
    """Draw a bar for each day of the week on a Canvas.
    The tallest bar is the best day of the week; the others are
    drawn in proportion to it. On a Canvas, y = 0 is the TOP,
    so a bar is drawn from the bottom line up to a smaller y value."""
    width = 360
    height = 165
    bottom = 135                    # the y position of the bars' base line
    tallest = 105                   # the height of the biggest bar
    canvas = tk.Canvas(frame, width=width, height=height, highlightthickness=0)
    canvas.pack()

    daily = get_daily_totals(app["data"], week_start)
    best = max(daily)               # max() returns the largest number in a list
    color = THEMES[app["settings"]["theme"]]
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    canvas.create_line(0, bottom, width, bottom, fill="#909090")
    for day_number in range(7):
        x_center = 26 + day_number * 51
        amount = daily[day_number]
        if amount > 0:
            bar_height = tallest * amount / best
            canvas.create_rectangle(x_center - 15, bottom - bar_height,
                                    x_center + 15, bottom, fill=color, outline=color)
            dollars = "$" + str(round_divide(amount, 100))   # whole dollars fit better
            canvas.create_text(x_center, bottom - bar_height - 9,
                               text=dollars, font=SMALL_FONT)
        canvas.create_text(x_center, bottom + 14, text=day_names[day_number],
                           font=NORMAL_FONT)

    if best == 0:
        canvas.create_text(width / 2, bottom / 2, text="No earnings this week yet.",
                           font=NORMAL_FONT)


# ---------- Log Shift screen ----------

def show_log_shift(app, shift_id=None):
    """Show the Log Shift screen: the form on the left, results on the right.
    shift_id=None is a default value: calling show_log_shift(app) gives an
    empty form for a new shift, and show_log_shift(app, 3) edits shift #3."""
    clear_content(app)
    content = app["content"]
    app["editing_id"] = shift_id

    if shift_id is None:
        title = "Log Shift"
    else:
        title = "Edit Shift #" + str(shift_id)
    tk.Label(content, text=title, font=HEADING_FONT).grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

    form_frame = tk.Frame(content)
    form_frame.grid(row=1, column=0, sticky="nw", padx=(0, 30))

    results_frame = tk.LabelFrame(content, text="Earnings Summary",
                                  font=HEADING_FONT, padx=15, pady=10)
    results_frame.grid(row=1, column=1, sticky="nw")

    buttons_frame = tk.Frame(content)
    buttons_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=12)

    build_shift_form(app, form_frame)
    build_results_area(app, results_frame)
    build_form_buttons(app, buttons_frame)

    # When editing, fill the form with the shift's original information
    if shift_id is not None:
        shift = find_shift(app["data"], shift_id)
        if shift is not None:
            fill_form(app, shift)


def build_shift_form(app, frame):
    """Create the labels and entry boxes for the Log Shift form.
    The entry boxes are saved in app["form"] so other functions can read them."""
    settings = app["settings"]
    today = datetime.date.today().isoformat()       # like "2026-11-18"
    wage_text = f"{settings['wage_cents'] / 100:.2f}"

    # Each tuple is (key, label text, starting value)
    fields = [
        ("date", "Date (YYYY-MM-DD)", today),
        ("hours", "Hours worked", ""),
        ("minutes", "Additional minutes (0-59)", "0"),
        ("wage", "Hourly base wage ($)", wage_text),
        ("cash_tips", "Cash tips ($)", ""),
        ("card_tips", "Credit card tips ($)", ""),
        ("kitchen", "Kitchen tip-out (%)", str(settings["kitchen_percent"])),
        ("busser", "Busser tip-out (%)", str(settings["busser_percent"])),
        ("dishwasher", "Dishwasher tip-out (%)", str(settings["dishwasher_percent"])),
    ]

    app["form"] = {}
    row = 0
    for key, label_text, start_value in fields:
        tk.Label(frame, text=label_text, font=NORMAL_FONT).grid(
            row=row, column=0, sticky="w", pady=3)
        entry = tk.Entry(frame, width=14, font=NORMAL_FONT)
        entry.insert(0, start_value)
        entry.grid(row=row, column=1, sticky="w", pady=3, padx=(10, 0))
        app["form"][key] = entry
        row = row + 1

    # Notes use a Text box so they can be more than one line
    tk.Label(frame, text="Notes (optional)", font=NORMAL_FONT).grid(
        row=row, column=0, sticky="nw", pady=3)
    notes_box = tk.Text(frame, width=26, height=3, font=NORMAL_FONT)
    notes_box.grid(row=row, column=1, sticky="w", pady=3, padx=(10, 0))
    app["form"]["notes"] = notes_box


def build_form_buttons(app, frame):
    """Create the Calculate and Save buttons (plus Cancel when editing)."""
    tk.Button(frame, text="Calculate Earnings", font=BOLD_FONT,
              command=lambda: on_calculate(app)).pack(side="left", padx=(0, 8))

    if app["editing_id"] is None:
        save_text = "Save Shift"
    else:
        save_text = "Save Changes"
    tk.Button(frame, text=save_text, font=BOLD_FONT,
              command=lambda: on_save_shift(app)).pack(side="left", padx=(0, 8))

    if app["editing_id"] is not None:
        tk.Button(frame, text="Cancel", font=NORMAL_FONT,
                  command=lambda: show_history(app)).pack(side="left")


def set_entry_text(entry, text):
    """Replace whatever is in an entry box with new text."""
    entry.delete(0, "end")
    entry.insert(0, text)


def fill_form(app, shift):
    """Put a saved shift's information into the form (used for editing)."""
    form = app["form"]
    set_entry_text(form["date"], shift["date"])
    set_entry_text(form["hours"], str(shift["minutes"] // 60))
    set_entry_text(form["minutes"], str(shift["minutes"] % 60))
    set_entry_text(form["wage"], cents_to_entry_text(shift["wage_cents"]))
    set_entry_text(form["cash_tips"], cents_to_entry_text(shift["cash_tips_cents"]))
    set_entry_text(form["card_tips"], cents_to_entry_text(shift["card_tips_cents"]))
    for category in TIPOUT_CATEGORIES:
        set_entry_text(form[category], str(shift["tipout_percents"][category]))
    form["notes"].insert("1.0", shift["notes"])

    # Show the shift's earnings right away
    show_results(app, calculate_shift(shift))


def build_results_area(app, frame):
    """Create the Earnings Summary labels. The value labels are saved
    in app["result_labels"] so we can change their text later."""
    app["result_labels"] = {}
    row = 0
    for key, label_text in RESULT_ROWS:
        font = NORMAL_FONT
        if key == "total_earnings":
            font = BOLD_FONT                     # make the main total stand out
        tk.Label(frame, text=label_text + ":", font=font).grid(
            row=row, column=0, sticky="w", pady=3)
        value_label = tk.Label(frame, text="-", font=font, width=14, anchor="e")
        value_label.grid(row=row, column=1, sticky="e", pady=3)
        app["result_labels"][key] = value_label
        row = row + 1


def show_input_error(message):
    """Show a pop-up error for an invalid entry."""
    messagebox.showerror("Invalid entry", message)


def read_tipout_percents(form):
    """Read the three tip-out boxes.
    Returns a dictionary of percents, or None if something is invalid."""
    percents = {}
    total = 0
    for category in TIPOUT_CATEGORIES:
        value = parse_whole_number(form[category].get(), 0, 100)
        if value is None:
            show_input_error(category.capitalize() +
                             " tip-out must be a whole number from 0 to 100.")
            return None
        percents[category] = value
        total = total + value

    if total > 100:
        show_input_error("The tip-out percentages add up to more than 100%.")
        return None
    return percents


def read_form(app):
    """Read and check everything on the Log Shift form.
    Returns a shift dictionary, or None if an entry is invalid."""
    form = app["form"]

    hours = parse_whole_number(form["hours"].get(), 0, 24)
    if hours is None:
        show_input_error("Hours worked must be a whole number from 0 to 24.")
        return None
    minutes = parse_whole_number(form["minutes"].get(), 0, 59)
    if minutes is None:
        show_input_error("Additional minutes must be a whole number from 0 to 59.")
        return None
    total_minutes = hours * 60 + minutes
    if total_minutes > MAX_MINUTES_PER_SHIFT:
        show_input_error("A shift cannot be longer than 24 hours.")
        return None

    wage = dollars_to_cents(form["wage"].get())
    cash = dollars_to_cents(form["cash_tips"].get())
    card = dollars_to_cents(form["card_tips"].get())
    if wage is None or cash is None or card is None:
        show_input_error("Wage and tips must be dollar amounts like 15 or 15.50\n"
                         "(no negatives, at most two decimal places).")
        return None

    percents = read_tipout_percents(form)
    if percents is None:
        return None

    # "1.0" means line 1, character 0 (the start of the Text box)
    notes = form["notes"].get("1.0", "end").strip()

    shift = {
        "date": form["date"].get().strip(),   # checked when saving (Stage 2)
        "minutes": total_minutes,
        "wage_cents": wage,
        "cash_tips_cents": cash,
        "card_tips_cents": card,
        "tipout_percents": percents,
        "notes": notes,
    }
    return shift


def show_results(app, results):
    """Put calculated results into the Earnings Summary labels."""
    labels = app["result_labels"]
    for key, label_text in RESULT_ROWS:
        if key == "hourly":
            continue                             # handled separately below
        labels[key].config(text=cents_to_text(results[key]))

    if results["hourly"] is None:
        labels["hourly"].config(text="Enter hours")
    else:
        labels["hourly"].config(text=cents_to_text(results["hourly"]) + "/hr")


def on_calculate(app):
    """Runs when Calculate Earnings is clicked. Nothing is saved."""
    shift = read_form(app)
    if shift is None:
        return                                   # an error was already shown
    results = calculate_shift(shift)
    show_results(app, results)


def on_save_shift(app):
    """Runs when Save Shift / Save Changes is clicked.
    Saving needs a real date and a time worked above zero."""
    shift = read_form(app)
    if shift is None:
        return

    shift_date = parse_date(shift["date"])
    if shift_date is None:
        show_input_error("Please enter a real date in the form YYYY-MM-DD,\n"
                         "for example 2026-11-16.")
        return
    shift["date"] = shift_date.isoformat()    # store dates the same way every time

    if shift["minutes"] <= 0:
        show_input_error("To save a shift, enter the hours and/or minutes worked.")
        return

    data = app["data"]
    if app["editing_id"] is None:
        shift_id = add_shift(data, shift)
        message = "Shift #" + str(shift_id) + " saved."
    else:
        update_shift(data, app["editing_id"], shift)
        message = "Shift #" + str(app["editing_id"]) + " updated."

    if not save_data(data):
        show_input_error("The shift could not be written to shift_data.json.\n"
                         "Check that the program's folder isn't read-only.")
        message = message + " (Warning: not written to the save file.)"
    show_history(app, message)


# ---------- Shift History screen ----------

def format_history_row(shift):
    """Build one line of the history list, with columns lined up.
    text.ljust(12) adds spaces after the text until it is 12 characters
    long, and text.rjust(11) adds spaces before it."""
    results = calculate_shift(shift)
    hours = format_duration(shift["minutes"])
    tips = cents_to_text(results["total_tips"])
    tipout = cents_to_text(results["total_tipout"])
    take_home = cents_to_text(results["take_home_tips"])
    earnings = cents_to_text(results["total_earnings"])
    return (shift["date"].ljust(12) + hours.rjust(8) + tips.rjust(11) +
            tipout.rjust(11) + take_home.rjust(11) + earnings.rjust(11))


def show_history(app, message=""):
    """Show the Shift History screen: the list, the buttons and a details box.
    'message' is an optional status line, such as 'Shift #3 saved.'"""
    clear_content(app)
    content = app["content"]
    tk.Label(content, text="Shift History", font=HEADING_FONT).pack(anchor="w")

    if message != "":
        color = THEMES[app["settings"]["theme"]]
        tk.Label(content, text=message, font=BOLD_FONT, fg=color).pack(anchor="w")

    build_history_list(app, content)
    build_history_buttons(app, content)

    details_frame = tk.LabelFrame(content, text="Shift Details",
                                  font=HEADING_FONT, padx=12, pady=8)
    details_frame.pack(fill="x", pady=(4, 0))
    app["details_label"] = tk.Label(details_frame, font=NORMAL_FONT, justify="left",
                                    text="Click a shift in the list to see its details.")
    app["details_label"].pack(anchor="w")


def build_history_list(app, parent):
    """Create the list of saved shifts, most recent first.
    app["history_ids"] remembers which shift ID is on each line,
    so line 0 of the list matches app["history_ids"][0], and so on."""
    header = ("Date".ljust(12) + "Hours".rjust(8) + "Tips".rjust(11) +
              "Tip-out".rjust(11) + "Take-home".rjust(11) + "Earnings".rjust(11))
    tk.Label(parent, text=header, font=LIST_FONT).pack(anchor="w", pady=(8, 0))

    list_frame = tk.Frame(parent)
    list_frame.pack(anchor="w")
    # exportselection=False keeps the selection when you click elsewhere
    listbox = tk.Listbox(list_frame, font=LIST_FONT, width=64, height=10,
                         exportselection=False)
    scrollbar = tk.Scrollbar(list_frame, command=listbox.yview)
    listbox.config(yscrollcommand=scrollbar.set)   # links the list and scrollbar
    listbox.pack(side="left")
    scrollbar.pack(side="left", fill="y")

    app["history_ids"] = []
    for shift in get_sorted_shifts(app["data"]):
        listbox.insert("end", format_history_row(shift))
        app["history_ids"].append(shift["id"])

    if len(app["history_ids"]) == 0:
        listbox.insert("end", "No shifts saved yet. Click New Shift to add one.")

    # When the selection changes, Tkinter calls our function and passes it
    # an "event" value. Our lambda accepts that value but doesn't need it.
    listbox.bind("<<ListboxSelect>>", lambda event: on_history_select(app))
    app["history_list"] = listbox


def build_history_buttons(app, parent):
    """Create the New, Edit and Delete buttons."""
    buttons = tk.Frame(parent)
    buttons.pack(anchor="w", pady=8)
    tk.Button(buttons, text="New Shift", font=NORMAL_FONT, width=12,
              command=lambda: show_log_shift(app)).pack(side="left", padx=(0, 8))
    tk.Button(buttons, text="Edit Shift", font=NORMAL_FONT, width=12,
              command=lambda: on_edit_shift(app)).pack(side="left", padx=(0, 8))
    tk.Button(buttons, text="Delete Shift", font=NORMAL_FONT, width=12,
              command=lambda: on_delete_shift(app)).pack(side="left")


def get_selected_shift_id(app):
    """Return the ID of the shift selected in the list, or None."""
    selection = app["history_list"].curselection()   # a tuple like (2,)
    if len(selection) == 0:
        return None
    line_number = selection[0]
    if line_number >= len(app["history_ids"]):
        return None              # the "No shifts saved yet" line was clicked
    return app["history_ids"][line_number]


def build_details_text(shift):
    """Build the multi-line text shown in the Shift Details box."""
    results = calculate_shift(shift)
    percents = shift["tipout_percents"]
    notes = shift["notes"]
    if notes == "":
        notes = "(none)"
    line1 = (f"Shift #{shift['id']}   Date: {shift['date']}   "
             f"Time worked: {format_duration(shift['minutes'])}")
    line2 = (f"Wage: {cents_to_text(shift['wage_cents'])}/hr   "
             f"Cash tips: {cents_to_text(shift['cash_tips_cents'])}   "
             f"Card tips: {cents_to_text(shift['card_tips_cents'])}")
    line3 = "Tip-out:"
    for category in TIPOUT_CATEGORIES:
        line3 = line3 + f"  {category} {percents[category]}% ({cents_to_text(results[category])})"
    line4 = (f"Base pay: {cents_to_text(results['base_pay'])}   "
             f"Take-home tips: {cents_to_text(results['take_home_tips'])}   "
             f"Total: {cents_to_text(results['total_earnings'])}")
    line5 = "Notes: " + notes
    # "\n" starts a new line
    return line1 + "\n" + line2 + "\n" + line3 + "\n" + line4 + "\n" + line5


def on_history_select(app):
    """Show the full details of the shift that was clicked."""
    shift_id = get_selected_shift_id(app)
    if shift_id is None:
        return
    shift = find_shift(app["data"], shift_id)
    app["details_label"].config(text=build_details_text(shift))


def on_edit_shift(app):
    """Open the selected shift in the Log Shift form."""
    shift_id = get_selected_shift_id(app)
    if shift_id is None:
        show_input_error("Please click a shift in the list first.")
        return
    show_log_shift(app, shift_id)


def on_delete_shift(app):
    """Delete the selected shift after asking the user to confirm."""
    shift_id = get_selected_shift_id(app)
    if shift_id is None:
        show_input_error("Please click a shift in the list first.")
        return
    shift = find_shift(app["data"], shift_id)

    # askyesno shows Yes and No buttons and returns True if Yes was clicked
    question = ("Delete shift #" + str(shift_id) + " on " + shift["date"] +
                "?\nThis cannot be undone.")
    if not messagebox.askyesno("Delete Shift", question):
        return

    delete_shift(app["data"], shift_id)
    if not save_data(app["data"]):
        show_input_error("The change could not be written to shift_data.json.")
        return
    show_history(app, "Shift #" + str(shift_id) + " deleted.")


# ============================================================
# SECTION 6: TESTING FUNCTIONS
# ============================================================

def check(outcomes, test_name, actual, expected):
    """Compare a result to what we expected and print PASS or FAIL."""
    if actual == expected:
        print("PASS:", test_name)
        outcomes.append(True)
    else:
        print("FAIL:", test_name, "- expected", expected, "but got", actual)
        outcomes.append(False)


def make_sample_shift(minutes, wage, cash, card, kitchen, busser, dishwasher):
    """Build a sample shift dictionary for testing (money in cents)."""
    return {
        "date": "2026-11-16",
        "minutes": minutes,
        "wage_cents": wage,
        "cash_tips_cents": cash,
        "card_tips_cents": card,
        "tipout_percents": {"kitchen": kitchen, "busser": busser,
                            "dishwasher": dishwasher},
        "notes": "",
    }


def check_calculations(outcomes):
    """Test the shift calculations with sample shifts."""
    # The example from the assignment: 5 hours at $15, $40 cash, $60 card,
    # 10% kitchen, 5% busser
    r = calculate_shift(make_sample_shift(300, 1500, 4000, 6000, 10, 5, 0))
    check(outcomes, "Total tips", r["total_tips"], 10000)
    check(outcomes, "Kitchen tip-out", r["kitchen"], 1000)
    check(outcomes, "Busser tip-out", r["busser"], 500)
    check(outcomes, "Total tip-out", r["total_tipout"], 1500)
    check(outcomes, "Take-home tips", r["take_home_tips"], 8500)
    check(outcomes, "Base pay", r["base_pay"], 7500)
    check(outcomes, "Total earnings", r["total_earnings"], 16000)
    check(outcomes, "Effective hourly", r["hourly"], 3200)

    # A zero-tip shift: 4 hours at $15, no tips
    r = calculate_shift(make_sample_shift(240, 1500, 0, 0, 10, 5, 0))
    check(outcomes, "Zero tips: tip-out", r["total_tipout"], 0)
    check(outcomes, "Zero tips: earnings", r["total_earnings"], 6000)
    check(outcomes, "Zero tips: hourly", r["hourly"], 1500)

    # Extra minutes: 5 hours 30 minutes at $15 = $82.50
    r = calculate_shift(make_sample_shift(330, 1500, 0, 0, 0, 0, 0))
    check(outcomes, "Base pay with minutes", r["base_pay"], 8250)

    # No hours entered: preview works, hourly shows as None
    r = calculate_shift(make_sample_shift(0, 1500, 5000, 0, 10, 0, 0))
    check(outcomes, "Preview with no hours", r["take_home_tips"], 4500)
    check(outcomes, "No hours: hourly is None", r["hourly"], None)

    # Rounding fix: $10.01 in tips, 33% to each category.
    # Each share rounds to $3.30, but 99% of $10.01 rounds to $9.91,
    # so the dishwasher (last category) gets the extra cent.
    r = calculate_shift(make_sample_shift(60, 0, 1001, 0, 33, 33, 33))
    check(outcomes, "Rounding: total tip-out", r["total_tipout"], 991)
    check(outcomes, "Rounding: last share adjusted", r["dishwasher"], 331)
    check(outcomes, "Rounding: shares add up",
          r["kitchen"] + r["busser"] + r["dishwasher"], r["total_tipout"])


def check_input_parsing(outcomes):
    """Test that valid entries are accepted and invalid ones rejected."""
    check(outcomes, "Money '12.5'", dollars_to_cents("12.5"), 1250)
    check(outcomes, "Money '$1,200.00'", dollars_to_cents("$1,200.00"), 120000)
    check(outcomes, "Money blank is 0", dollars_to_cents(""), 0)
    check(outcomes, "Money 'abc' rejected", dollars_to_cents("abc"), None)
    check(outcomes, "Money '-5' rejected", dollars_to_cents("-5"), None)
    check(outcomes, "Money '12.345' rejected", dollars_to_cents("12.345"), None)
    check(outcomes, "Percent '10'", parse_whole_number("10", 0, 100), 10)
    check(outcomes, "Percent '150' rejected", parse_whole_number("150", 0, 100), None)
    check(outcomes, "Percent '7.5' rejected", parse_whole_number("7.5", 0, 100), None)
    check(outcomes, "Percent '-3' rejected", parse_whole_number("-3", 0, 100), None)
    check(outcomes, "Date '2026-02-30' rejected", parse_date("2026-02-30"), None)
    check(outcomes, "Date '2026-11-16' accepted",
          parse_date("2026-11-16"), datetime.date(2026, 11, 16))


def check_shift_records(outcomes):
    """Test adding, editing and deleting shifts.
    Uses a separate test data dictionary that is never saved,
    so your real shift_data.json is not touched."""
    data = make_empty_data()

    # Two shifts on the same date, plus one on an earlier date
    first_id = add_shift(data, make_sample_shift(300, 1500, 4000, 6000, 10, 5, 0))
    second_id = add_shift(data, make_sample_shift(240, 1500, 2000, 0, 10, 5, 0))
    older = make_sample_shift(180, 1500, 1000, 0, 0, 0, 0)
    older["date"] = "2026-11-10"
    older_id = add_shift(data, older)
    check(outcomes, "Same date: both shifts saved", len(data["shifts"]), 3)
    check(outcomes, "Each shift gets a unique ID", [first_id, second_id, older_id], [1, 2, 3])

    # Most recent date first (same-date shifts stay in the order entered)
    order = []
    for shift in get_sorted_shifts(data):
        order.append(shift["id"])
    check(outcomes, "History sorted newest first", order, [1, 2, 3])

    # Editing updates the existing shift instead of adding a duplicate
    edited = make_sample_shift(300, 1500, 5000, 6000, 10, 5, 0)
    update_shift(data, first_id, edited)
    check(outcomes, "Edit keeps the same number of shifts", len(data["shifts"]), 3)
    check(outcomes, "Edit changes the saved values",
          find_shift(data, first_id)["cash_tips_cents"], 5000)

    # Deleting removes only the chosen shift, and IDs are not reused
    delete_shift(data, second_id)
    check(outcomes, "Delete removes one shift", len(data["shifts"]), 2)
    check(outcomes, "Deleted shift is gone", find_shift(data, second_id), None)
    check(outcomes, "Next ID is not reused",
          add_shift(data, make_sample_shift(60, 1500, 0, 0, 0, 0, 0)), 4)


def check_data_file_rules(outcomes):
    """Test the save-file checks without reading or writing the real file."""
    data = make_empty_data()
    add_shift(data, make_sample_shift(300, 1500, 4000, 6000, 10, 5, 0))
    check(outcomes, "Good data passes the file check", is_valid_data(data), True)

    # json.dumps/json.loads turn data into JSON text and back, all in memory
    copy = json.loads(json.dumps(data))
    check(outcomes, "Data survives conversion to JSON", copy, data)

    check(outcomes, "Damaged data is detected",
          is_valid_data({"shifts": "oops"}), False)
    broken = make_empty_data()
    broken["shifts"].append({"id": 1, "date": "2026-11-16"})
    check(outcomes, "Shift with missing values is detected",
          is_valid_data(broken), False)


def make_week_test_data():
    """Build test data: two shifts on Mon Nov 16, one on Sun Nov 22,
    plus one shift just before and one just after that week."""
    data = make_empty_data()
    dates_and_shifts = [
        ("2026-11-16", make_sample_shift(300, 1500, 4000, 6000, 10, 5, 0)),  # $160.00
        ("2026-11-16", make_sample_shift(240, 1500, 2000, 0, 10, 5, 0)),     # $77.00
        ("2026-11-22", make_sample_shift(360, 1500, 3000, 0, 0, 0, 0)),      # $120.00
        ("2026-11-15", make_sample_shift(120, 1500, 0, 0, 0, 0, 0)),         # $30.00
        ("2026-11-23", make_sample_shift(120, 1500, 0, 0, 0, 0, 0)),         # $30.00
    ]
    for date_text, shift in dates_and_shifts:
        shift["date"] = date_text
        add_shift(data, shift)
    return data


def check_weeks_and_goals(outcomes):
    """Test week dates, weekly totals, best dates and goal progress."""
    monday = datetime.date(2026, 11, 16)
    check(outcomes, "Week start from a Wednesday",
          get_week_start(datetime.date(2026, 11, 18)), monday)
    check(outcomes, "Week start from a Sunday",
          get_week_start(datetime.date(2026, 11, 22)), monday)
    check(outcomes, "Week start from a Monday",
          get_week_start(monday), monday)

    data = make_week_test_data()
    totals = calculate_week_totals(data, monday)
    check(outcomes, "Weekly total earnings", totals["earnings"], 35700)
    check(outcomes, "Weekly total time", totals["minutes"], 900)
    check(outcomes, "Weekly shift count (other weeks left out)", totals["shift_count"], 3)
    check(outcomes, "Weekly average hourly (total / time)", totals["hourly"], 2380)
    empty = calculate_week_totals(data, datetime.date(2026, 1, 5))
    check(outcomes, "Empty week has no hourly average", empty["hourly"], None)

    check(outcomes, "Same-date shifts combined",
          earnings_by_date(data)["2026-11-16"], 23700)
    check(outcomes, "Highest-earning date", get_top_dates(data, 5)[0],
          ("2026-11-16", 23700))
    check(outcomes, "Top dates with too little data",
          len(get_top_dates(make_empty_data(), 5)), 0)

    set_goal(data, monday, 50000)
    check(outcomes, "Goal saved by Monday's date", data["weekly_goals"], {"2026-11-16": 50000})
    check(outcomes, "Goal progress (under goal)",
          calculate_goal_progress(totals["earnings"], 50000), (14300, 71))
    check(outcomes, "Goal progress (over goal)",
          calculate_goal_progress(60000, 50000), (0, 120))
    set_goal(data, monday, 0)
    check(outcomes, "Goal of 0 removes the goal", get_goal(data, monday), None)


def check_chart_and_settings(outcomes):
    """Test the chart's daily totals and the settings rules."""
    data = make_week_test_data()
    monday = datetime.date(2026, 11, 16)
    check(outcomes, "Daily totals for the bar chart (Mon to Sun)",
          get_daily_totals(data, monday), [23700, 0, 0, 0, 0, 0, 12000])

    # Changing the default settings must not change saved shifts
    before = calculate_shift(find_shift(data, 1))["total_earnings"]
    data["settings"]["wage_cents"] = 2500
    data["settings"]["kitchen_percent"] = 20
    after = calculate_shift(find_shift(data, 1))["total_earnings"]
    check(outcomes, "New settings don't change saved shifts", after, before)

    # An unknown theme name in the file falls back to red
    data["settings"]["theme"] = "purple"
    fill_missing_settings(data)
    check(outcomes, "Unknown theme falls back to red", data["settings"]["theme"], "red")

    # A missing setting is filled in with its default value
    del data["settings"]["busser_percent"]
    fill_missing_settings(data)
    check(outcomes, "Missing setting gets its default", data["settings"]["busser_percent"], 5)


def run_checks():
    """Run all tests using sample data. Does not touch any saved data."""
    print("Running checks...")
    outcomes = []
    check_calculations(outcomes)
    check_input_parsing(outcomes)
    check_shift_records(outcomes)
    check_data_file_rules(outcomes)
    check_weeks_and_goals(outcomes)
    check_chart_and_settings(outcomes)

    passed = 0
    for outcome in outcomes:
        if outcome:
            passed = passed + 1
    print(f"\n{passed} of {len(outcomes)} checks passed.")


# ============================================================
# SECTION 7: PROGRAM STARTUP
# ============================================================

def main():
    """Create the app dictionary, build the window and start Tkinter."""
    app = {}
    app["root"] = tk.Tk()

    # Load saved shifts (or start fresh). The settings live inside the data,
    # so app["settings"] and app["data"]["settings"] are the same dictionary.
    data, warning = load_data()
    app["data"] = data
    app["settings"] = data["settings"]
    app["editing_id"] = None
    app["week_start"] = get_week_start(datetime.date.today())  # this week's Monday

    build_window(app)
    show_dashboard(app)       # the Dashboard is the home screen

    if warning is not None:
        messagebox.showwarning("Saved data problem", warning)

    app["root"].mainloop()    # keeps the window open and responding to clicks


# Start the program
main()
