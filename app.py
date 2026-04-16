from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from auth_storage import (
    MEALS_PATH,
    MEAL_COLUMNS,
    PROFILES_PATH,
    PROGRESS_COLUMNS,
    PROGRESS_PATH,
    WORKOUTS_PATH,
    WORKOUT_COLUMNS,
    append_record,
    authenticate_user,
    clear_user_records,
    default_profile,
    ensure_storage,
    load_profile,
    load_user_records,
    normalize_username,
    register_user,
    save_profile,
)


BASE_DIR = Path(__file__).resolve().parent
EXERCISE_PATH = BASE_DIR / "megaGymDataset.csv"
NUTRITION_PATH = BASE_DIR / "nutrition.csv"

st.set_page_config(
    page_title="Titan Coach",
    page_icon="T",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_state() -> None:
    defaults = {
        "authenticated": False,
        "current_user": "",
        "profile_loaded_for": "",
        "profile": default_profile(),
        "workout_log": [],
        "meal_log": [],
        "progress_log": [],
        "selected_plan_exercises": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_user_bundle(username: str) -> None:
    st.session_state.profile = load_profile(username)
    st.session_state.workout_log = load_user_records(WORKOUTS_PATH, WORKOUT_COLUMNS, username)
    st.session_state.meal_log = load_user_records(MEALS_PATH, MEAL_COLUMNS, username)
    st.session_state.progress_log = load_user_records(PROGRESS_PATH, PROGRESS_COLUMNS, username)
    st.session_state.profile_loaded_for = username


def login_user(username: str) -> None:
    normalized = normalize_username(username)
    st.session_state.authenticated = True
    st.session_state.current_user = normalized
    load_user_bundle(normalized)


def logout_user() -> None:
    st.session_state.authenticated = False
    st.session_state.current_user = ""
    st.session_state.profile_loaded_for = ""
    st.session_state.profile = default_profile()
    st.session_state.workout_log = []
    st.session_state.meal_log = []
    st.session_state.progress_log = []


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not EXERCISE_PATH.exists():
        raise FileNotFoundError(f"Missing exercise dataset: {EXERCISE_PATH}")
    if not NUTRITION_PATH.exists():
        raise FileNotFoundError(f"Missing nutrition dataset: {NUTRITION_PATH}")

    exercise_df = pd.read_csv(EXERCISE_PATH)
    nutrition_df = pd.read_csv(NUTRITION_PATH)

    exercise_df.columns = exercise_df.columns.str.strip().str.title()
    nutrition_df.columns = nutrition_df.columns.str.strip().str.lower()

    exercise_df["Bodypart"] = exercise_df["Bodypart"].fillna("Unknown")
    exercise_df["Equipment"] = exercise_df["Equipment"].fillna("Body Only")
    exercise_df["Level"] = exercise_df["Level"].fillna("Beginner")
    exercise_df["Desc"] = exercise_df["Desc"].fillna("No coaching notes available.")
    exercise_df["Rating"] = pd.to_numeric(exercise_df["Rating"], errors="coerce").fillna(0.0)

    numeric_food_cols = [
        "calories",
        "protein_g",
        "carbs_g",
        "fat_g",
        "fiber_g",
        "sugar_g",
        "sodium_mg",
        "health_score",
    ]
    for col in numeric_food_cols:
        if col in nutrition_df.columns:
            nutrition_df[col] = pd.to_numeric(nutrition_df[col], errors="coerce").fillna(0.0)

    nutrition_df["food_name"] = nutrition_df["food_name"].fillna("Unknown food")
    nutrition_df["food_type"] = nutrition_df.get("food_type", pd.Series(dtype="object")).fillna("Other")
    nutrition_df["health_score"] = nutrition_df.get("health_score", pd.Series(dtype="float")).fillna(0.0)
    return exercise_df, nutrition_df


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(109, 187, 142, 0.22), transparent 28%),
                radial-gradient(circle at top right, rgba(245, 158, 11, 0.14), transparent 24%),
                linear-gradient(180deg, #0b1220 0%, #111827 48%, #162032 100%);
            color: #e5eef8;
        }
        [data-testid="stSidebar"] {
            background: rgba(9, 14, 25, 0.94);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        .hero-card, .glass-card, .plan-card, .auth-card {
            background: rgba(15, 23, 42, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 20px;
            padding: 1.2rem 1.1rem;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.24);
            backdrop-filter: blur(8px);
        }
        .hero-card h1, .plan-card h4, .auth-card h2 {
            color: #f8fafc;
            margin-bottom: 0.3rem;
        }
        .muted {
            color: #9fb0c8;
            font-size: 0.96rem;
        }
        .pill {
            display: inline-block;
            background: rgba(125, 211, 167, 0.12);
            color: #cceedd;
            border: 1px solid rgba(125, 211, 167, 0.28);
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
            margin-right: 0.35rem;
            margin-bottom: 0.35rem;
            font-size: 0.86rem;
        }
        .stButton > button {
            width: 100%;
            border-radius: 14px;
            border: 1px solid rgba(125, 211, 167, 0.35);
            background: linear-gradient(135deg, #183446 0%, #215c46 100%);
            color: #f8fafc;
            font-weight: 600;
            min-height: 2.9rem;
        }
        .stButton > button:hover {
            border-color: rgba(255, 255, 255, 0.35);
            color: white;
        }
        div[data-testid="stMetric"] {
            background: rgba(15, 23, 42, 0.65);
            border: 1px solid rgba(148, 163, 184, 0.15);
            padding: 0.8rem;
            border-radius: 18px;
        }
        .section-title {
            margin-top: 0.2rem;
            margin-bottom: 0.75rem;
            color: #f8fafc;
            font-weight: 700;
            letter-spacing: 0.02em;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def activity_factor(activity: str) -> float:
    return {
        "Light": 1.35,
        "Moderate": 1.55,
        "High": 1.75,
        "Athlete": 1.9,
    }.get(activity, 1.55)


def calculate_targets(profile: dict) -> dict:
    weight = profile["weight_kg"]
    height = profile["height_cm"]
    age = profile["age"]

    if profile["sex"] == "Male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    tdee = bmr * activity_factor(profile["activity"])
    calorie_target = max(
        1200,
        tdee + {
            "Lose fat": -450,
            "Build muscle": 250,
            "Maintain": 0,
            "Improve fitness": -100,
        }.get(profile["goal"], 0),
    )

    protein_per_kg = {
        "Lose fat": 2.0,
        "Build muscle": 2.2,
        "Maintain": 1.8,
        "Improve fitness": 1.8,
    }.get(profile["goal"], 1.8)
    fat_grams = weight * 0.8
    protein_grams = weight * protein_per_kg
    remaining_calories = max(calorie_target - ((protein_grams * 4) + (fat_grams * 9)), 0)
    carbs_grams = remaining_calories / 4 if remaining_calories else weight * 2

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "calorie_target": round(calorie_target),
        "protein_target": round(protein_grams),
        "carb_target": round(carbs_grams),
        "fat_target": round(fat_grams),
        "bmi": round(weight / ((height / 100) ** 2), 1),
        "water_liters": round(weight * 0.035, 1),
    }


def session_recommendation(level: str, goal: str) -> tuple[str, str, str]:
    if goal == "Build muscle":
        return {
            "Beginner": ("3", "8-12", "75 sec"),
            "Intermediate": ("4", "8-10", "90 sec"),
            "Advanced": ("4-5", "6-10", "120 sec"),
        }[level]
    if goal == "Lose fat":
        return {
            "Beginner": ("3", "12-15", "45 sec"),
            "Intermediate": ("3-4", "12-16", "45 sec"),
            "Advanced": ("4", "15-20", "30-45 sec"),
        }[level]
    return {
        "Beginner": ("2-3", "10-12", "60 sec"),
        "Intermediate": ("3-4", "10-14", "60-75 sec"),
        "Advanced": ("4", "8-12", "75 sec"),
    }[level]


def build_workout_plan(exercise_df: pd.DataFrame, profile: dict) -> pd.DataFrame:
    focus_areas = profile["focus_areas"] or exercise_df["Bodypart"].dropna().unique().tolist()[:3]
    level = profile["experience"]
    allowed_equipment = set(profile["equipment"])

    filtered = exercise_df[exercise_df["Bodypart"].isin(focus_areas)].copy()
    if allowed_equipment:
        filtered = filtered[filtered["Equipment"].isin(allowed_equipment)]
    if filtered.empty:
        filtered = exercise_df[exercise_df["Bodypart"].isin(focus_areas)].copy()

    filtered = filtered.sort_values(["Bodypart", "Rating"], ascending=[True, False])
    plan_rows = []
    for bodypart in focus_areas:
        group = filtered[filtered["Bodypart"] == bodypart].head(3)
        for _, row in group.iterrows():
            sets, reps, rest = session_recommendation(level, profile["goal"])
            plan_rows.append(
                {
                    "Body Part": row["Bodypart"],
                    "Exercise": row["Title"],
                    "Equipment": row["Equipment"],
                    "Level": row["Level"],
                    "Sets": sets,
                    "Reps": reps,
                    "Rest": rest,
                    "Coaching": row["Desc"],
                }
            )
    return pd.DataFrame(plan_rows)


def summarize_food_log(meal_log: list[dict]) -> dict:
    totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for item in meal_log:
        totals["calories"] += item.get("calories", 0.0)
        totals["protein_g"] += item.get("protein_g", 0.0)
        totals["carbs_g"] += item.get("carbs_g", 0.0)
        totals["fat_g"] += item.get("fat_g", 0.0)
    return totals


def render_hero(profile: dict, targets: dict) -> None:
    badges = "".join(f"<span class='pill'>{area}</span>" for area in profile["focus_areas"])
    st.markdown(
        f"""
        <div class="hero-card">
            <h1>Titan Coach</h1>
            <p class="muted">
                Personal trainer mode is active for <strong>{profile["name"]}</strong>.
                Goal: <strong>{profile["goal"]}</strong> | Experience: <strong>{profile["experience"]}</strong> |
                Training days: <strong>{profile["days_per_week"]}</strong> / week
            </p>
            <div>{badges}</div>
            <p class="muted" style="margin-top: 0.75rem;">
                Daily target: <strong>{targets["calorie_target"]} kcal</strong>,
                <strong>{targets["protein_target"]} g protein</strong>,
                <strong>{targets["water_liters"]} L water</strong>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_auth_screen() -> None:
    left, center, right = st.columns([1, 1.2, 1])
    with center:
        st.markdown(
            """
            <div class="auth-card">
                <h2>Titan Coach Login</h2>
                <p class="muted">Each user gets a separate account, separate dashboard, and separate CSV saved data for profile, goals, workouts, meals, and progress.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log In")
            if submitted:
                if authenticate_user(username, password):
                    login_user(username)
                    st.success("Login successful.")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        with signup_tab:
            with st.form("signup_form"):
                new_username = st.text_input("New username")
                new_password = st.text_input("New password", type="password")
                confirm_password = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Create Account")
            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    success, message, suggestions = register_user(new_username, new_password)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                        if suggestions:
                            st.info("Try one of these usernames: " + ", ".join(suggestions))


def dashboard_tab(exercise_df: pd.DataFrame, targets: dict) -> None:
    profile = st.session_state.profile
    render_hero(profile, targets)

    workout_df = pd.DataFrame(st.session_state.workout_log)
    meal_totals = summarize_food_log(st.session_state.meal_log)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BMI", targets["bmi"])
    c2.metric("TDEE", f'{targets["tdee"]} kcal')
    c3.metric("Workouts logged", len(workout_df))
    c4.metric("Calories eaten", f'{round(meal_totals["calories"])} kcal')

    adherence = round((meal_totals["protein_g"] / max(targets["protein_target"], 1)) * 100)
    s1, s2, s3 = st.columns(3)
    s1.metric("Protein target hit", f"{min(adherence, 999)}%")
    s2.metric("Weekly sessions goal", f"{min(len(workout_df), profile['days_per_week'])} / {profile['days_per_week']}")
    s3.metric("User", st.session_state.current_user)

    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("<h3 class='section-title'>This Week's Focus</h3>", unsafe_allow_html=True)
        plan_df = build_workout_plan(exercise_df, profile)
        if plan_df.empty:
            st.warning("No exercises matched the current profile filters. Adjust equipment or focus areas in the sidebar.")
        else:
            st.dataframe(plan_df[["Body Part", "Exercise", "Sets", "Reps", "Rest"]], use_container_width=True, hide_index=True)

    with right:
        st.markdown("<h3 class='section-title'>Coach Notes</h3>", unsafe_allow_html=True)
        workload_tip = (
            "Add one more set to the main movement if the final set feels easier than RPE 7."
            if profile["experience"] != "Beginner"
            else "Stay one or two reps away from failure and build consistency before adding load."
        )
        meal_tip = (
            "Split protein across 3 to 4 meals to make the target easier to hit."
            if targets["protein_target"] >= 130
            else "Anchor each meal with protein first, then add carbs around training."
        )
        st.markdown(
            f"""
            <div class="hero-card">
                <p><strong>Training:</strong> {workload_tip}</p>
                <p><strong>Nutrition:</strong> {meal_tip}</p>
                <p><strong>Recovery:</strong> Aim for 7 to 9 hours of sleep and at least {targets["water_liters"]} L water.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not workout_df.empty:
        history = workout_df.copy()
        history["date"] = pd.to_datetime(history["date"])
        daily_volume = history.groupby(history["date"].dt.date)["volume"].sum().reset_index()
        daily_volume.columns = ["Date", "Volume"]
        st.markdown("<h3 class='section-title'>Progress Trend</h3>", unsafe_allow_html=True)
        st.line_chart(daily_volume.set_index("Date"))


def workouts_tab(exercise_df: pd.DataFrame) -> None:
    profile = st.session_state.profile
    st.markdown("<h3 class='section-title'>Workout Builder</h3>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    body_parts = sorted(exercise_df["Bodypart"].dropna().unique().tolist())
    equipment_options = sorted(exercise_df["Equipment"].dropna().unique().tolist())
    chosen_body_parts = col1.multiselect("Target muscles", body_parts, default=profile["focus_areas"])
    chosen_equipment = col2.multiselect("Equipment", equipment_options, default=profile["equipment"])
    chosen_level = col3.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"], index=["Beginner", "Intermediate", "Advanced"].index(profile["experience"]))

    filtered = exercise_df.copy()
    if chosen_body_parts:
        filtered = filtered[filtered["Bodypart"].isin(chosen_body_parts)]
    if chosen_equipment:
        filtered = filtered[filtered["Equipment"].isin(chosen_equipment)]
    filtered = filtered.sort_values(["Rating", "Title"], ascending=[False, True])

    sets, reps, rest = session_recommendation(chosen_level, profile["goal"])
    st.caption(f"Coach prescription: {sets} sets | {reps} reps | {rest} rest")

    if filtered.empty:
        st.info("No matching exercises found. Try expanding the equipment or body part filters.")
        return

    for idx, row in filtered.head(12).iterrows():
        st.markdown(
            f"""
            <div class="plan-card">
                <h4>{row["Title"]}</h4>
                <p class="muted">{row["Bodypart"]} | {row["Equipment"]} | {row["Level"]}</p>
                <p>{row["Desc"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2, c3, c4 = st.columns(4)
        performed_sets = c1.number_input("Sets", min_value=1, max_value=10, value=int(str(sets).split("-")[0]), key=f"sets_{idx}")
        performed_reps = c2.text_input("Reps", value=reps, key=f"reps_{idx}")
        load_used = c3.number_input("Weight (kg)", min_value=0.0, value=0.0, step=2.5, key=f"load_{idx}")
        duration = c4.number_input("Minutes", min_value=5, max_value=180, value=20, key=f"mins_{idx}")
        if st.button(f"Log {row['Title']}", key=f"log_{idx}"):
            rep_floor = int(str(performed_reps).split("-")[0]) if str(performed_reps).split("-")[0].isdigit() else 10
            volume = performed_sets * max(rep_floor, 1) * max(load_used if load_used else 1, 1)
            record = {
                "username": st.session_state.current_user,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "exercise": row["Title"],
                "bodypart": row["Bodypart"],
                "sets": performed_sets,
                "reps": performed_reps,
                "load_kg": load_used,
                "duration_min": duration,
                "volume": round(volume, 1),
            }
            st.session_state.workout_log.append(record)
            append_record(WORKOUTS_PATH, WORKOUT_COLUMNS, record)
            st.success(f"{row['Title']} added to your training history.")


def nutrition_tab(nutrition_df: pd.DataFrame, targets: dict) -> None:
    st.markdown("<h3 class='section-title'>Nutrition Coach</h3>", unsafe_allow_html=True)

    meal_totals = summarize_food_log(st.session_state.meal_log)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Calories", f"{round(meal_totals['calories'])} / {targets['calorie_target']}")
    m2.metric("Protein", f"{round(meal_totals['protein_g'])} / {targets['protein_target']} g")
    m3.metric("Carbs", f"{round(meal_totals['carbs_g'])} / {targets['carb_target']} g")
    m4.metric("Fat", f"{round(meal_totals['fat_g'])} / {targets['fat_target']} g")

    search_term = st.text_input("Search food", value="chicken")
    food_types = ["All"] + sorted(nutrition_df["food_type"].dropna().unique().tolist())
    selected_type = st.selectbox("Food type", food_types)

    matches = nutrition_df[nutrition_df["food_name"].str.contains(search_term, case=False, na=False)].copy()
    if selected_type != "All":
        matches = matches[matches["food_type"] == selected_type]
    matches = matches.sort_values(["health_score", "protein_g"], ascending=[False, False]).head(25)

    if matches.empty:
        st.info("No foods matched the current search.")
        return

    st.dataframe(
        matches[["food_name", "calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "health_score"]],
        use_container_width=True,
        hide_index=True,
    )

    choice = st.selectbox("Select food", matches["food_name"].tolist())
    grams = st.slider("Portion size (grams)", min_value=50, max_value=500, value=150, step=25)
    picked = matches[matches["food_name"] == choice].iloc[0]
    portion_scale = grams / 100
    calories = picked["calories"] * portion_scale
    protein = picked["protein_g"] * portion_scale
    carbs = picked["carbs_g"] * portion_scale
    fat = picked["fat_g"] * portion_scale

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Calories", f"{calories:.0f} kcal")
    c2.metric("Protein", f"{protein:.1f} g")
    c3.metric("Carbs", f"{carbs:.1f} g")
    c4.metric("Fat", f"{fat:.1f} g")

    if st.button("Add meal to daily log"):
        record = {
            "username": st.session_state.current_user,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "food_name": choice,
            "grams": grams,
            "calories": round(calories, 1),
            "protein_g": round(protein, 1),
            "carbs_g": round(carbs, 1),
            "fat_g": round(fat, 1),
        }
        st.session_state.meal_log.append(record)
        append_record(MEALS_PATH, MEAL_COLUMNS, record)
        st.success(f"{choice} added to your meal log.")


def progress_tab(targets: dict) -> None:
    st.markdown("<h3 class='section-title'>Progress Tracker</h3>", unsafe_allow_html=True)
    profile = st.session_state.profile
    workout_df = pd.DataFrame(st.session_state.workout_log)
    meal_df = pd.DataFrame(st.session_state.meal_log)

    with st.form("progress_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        weight = c1.number_input("Current weight (kg)", min_value=25.0, max_value=250.0, value=float(profile["weight_kg"]), step=0.5)
        waist = c2.number_input("Waist (cm)", min_value=40.0, max_value=200.0, value=82.0, step=0.5)
        energy = c3.slider("Energy level", min_value=1, max_value=10, value=7)
        notes = st.text_area("Weekly notes", placeholder="Examples: sleep improved, bench felt stronger, appetite low...")
        submitted = st.form_submit_button("Save progress check-in")

    if submitted:
        st.session_state.profile["weight_kg"] = weight
        save_profile(st.session_state.current_user, st.session_state.profile)
        record = {
            "username": st.session_state.current_user,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "weight_kg": weight,
            "waist_cm": waist,
            "energy": energy,
            "notes": notes,
        }
        st.session_state.progress_log.append(record)
        append_record(PROGRESS_PATH, PROGRESS_COLUMNS, record)
        st.success("Progress check-in saved.")

    p1, p2, p3 = st.columns(3)
    p1.metric("Target calories", f"{targets['calorie_target']} kcal")
    p2.metric("Target protein", f"{targets['protein_target']} g")
    p3.metric("Water target", f"{targets['water_liters']} L")

    if not workout_df.empty:
        st.markdown("<h4 class='section-title'>Workout History</h4>", unsafe_allow_html=True)
        st.dataframe(workout_df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)

    if not meal_df.empty:
        st.markdown("<h4 class='section-title'>Meal History</h4>", unsafe_allow_html=True)
        st.dataframe(meal_df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)

    progress_df = pd.DataFrame(st.session_state.progress_log)
    if not progress_df.empty:
        trend = progress_df.copy()
        trend["date"] = pd.to_datetime(trend["date"])
        st.markdown("<h4 class='section-title'>Bodyweight Trend</h4>", unsafe_allow_html=True)
        st.line_chart(trend.set_index("date")[["weight_kg", "waist_cm"]])
    else:
        st.info("Add your first progress check-in to start visual tracking.")


def sidebar_profile(exercise_df: pd.DataFrame) -> None:
    with st.sidebar:
        st.markdown(f"## {st.session_state.current_user}'s Dashboard")
        st.caption("Profile changes can be saved to your own CSV data.")
        profile = st.session_state.profile
        profile["name"] = st.text_input("Name", value=profile["name"])
        profile["age"] = st.number_input("Age", min_value=14, max_value=80, value=int(profile["age"]))
        profile["sex"] = st.selectbox("Sex", ["Male", "Female"], index=0 if profile["sex"] == "Male" else 1)
        profile["height_cm"] = st.number_input("Height (cm)", min_value=120, max_value=230, value=int(profile["height_cm"]))
        profile["weight_kg"] = st.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=float(profile["weight_kg"]), step=0.5)
        profile["goal"] = st.selectbox("Goal", ["Lose fat", "Build muscle", "Maintain", "Improve fitness"], index=["Lose fat", "Build muscle", "Maintain", "Improve fitness"].index(profile["goal"]))
        profile["activity"] = st.selectbox("Lifestyle activity", ["Light", "Moderate", "High", "Athlete"], index=["Light", "Moderate", "High", "Athlete"].index(profile["activity"]))
        profile["experience"] = st.selectbox("Training experience", ["Beginner", "Intermediate", "Advanced"], index=["Beginner", "Intermediate", "Advanced"].index(profile["experience"]))
        profile["days_per_week"] = st.slider("Workout days / week", min_value=2, max_value=7, value=int(profile["days_per_week"]))

        equipment_options = sorted(exercise_df["Equipment"].dropna().unique().tolist())
        body_parts = sorted(exercise_df["Bodypart"].dropna().unique().tolist())

        valid_equipment_defaults = [item for item in profile["equipment"] if item in equipment_options]
        valid_focus_defaults = [item for item in profile["focus_areas"] if item in body_parts]

        if not valid_equipment_defaults:
            valid_equipment_defaults = equipment_options[:3]
        if not valid_focus_defaults:
            valid_focus_defaults = body_parts[:3]

        profile["equipment"] = st.multiselect(
            "Available equipment",
            equipment_options,
            default=valid_equipment_defaults,
        )
        profile["focus_areas"] = st.multiselect(
            "Priority muscle groups",
            body_parts,
            default=valid_focus_defaults,
        )

        if st.button("Save profile"):
            save_profile(st.session_state.current_user, profile)
            st.success("Profile saved.")

        if st.button("Reset all logs"):
            st.session_state.workout_log = []
            st.session_state.meal_log = []
            st.session_state.progress_log = []
            clear_user_records(WORKOUTS_PATH, WORKOUT_COLUMNS, st.session_state.current_user)
            clear_user_records(MEALS_PATH, MEAL_COLUMNS, st.session_state.current_user)
            clear_user_records(PROGRESS_PATH, PROGRESS_COLUMNS, st.session_state.current_user)
            st.success("Training, nutrition, and progress logs cleared for this user.")

        if st.button("Log out"):
            logout_user()
            st.rerun()


def main() -> None:
    init_state()
    ensure_storage()
    apply_styles()
    exercise_df, nutrition_df = load_data()

    if not st.session_state.authenticated:
        render_auth_screen()
        return

    if st.session_state.profile_loaded_for != st.session_state.current_user:
        load_user_bundle(st.session_state.current_user)

    sidebar_profile(exercise_df)
    targets = calculate_targets(st.session_state.profile)

    tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Workouts", "Nutrition", "Progress"])
    with tab1:
        dashboard_tab(exercise_df, targets)
    with tab2:
        workouts_tab(exercise_df)
    with tab3:
        nutrition_tab(nutrition_df, targets)
    with tab4:
        progress_tab(targets)


if __name__ == "__main__":
    main()
