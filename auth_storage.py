from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "user_data"

USERS_PATH = DATA_DIR / "users.csv"
PROFILES_PATH = DATA_DIR / "profiles.csv"
WORKOUTS_PATH = DATA_DIR / "workouts.csv"
MEALS_PATH = DATA_DIR / "meals.csv"
PROGRESS_PATH = DATA_DIR / "progress.csv"

USER_COLUMNS = ["username", "password_hash", "created_at"]
PROFILE_COLUMNS = [
    "username",
    "name",
    "age",
    "sex",
    "height_cm",
    "weight_kg",
    "goal",
    "activity",
    "experience",
    "days_per_week",
    "equipment",
    "focus_areas",
]
WORKOUT_COLUMNS = ["username", "date", "exercise", "bodypart", "sets", "reps", "load_kg", "duration_min", "volume"]
MEAL_COLUMNS = ["username", "date", "food_name", "grams", "calories", "protein_g", "carbs_g", "fat_g"]
PROGRESS_COLUMNS = ["username", "date", "weight_kg", "waist_cm", "energy", "notes"]


def default_profile(name: str = "Athlete") -> dict:
    return {
        "name": name,
        "age": 25,
        "sex": "Male",
        "height_cm": 175,
        "weight_kg": 72.0,
        "goal": "Build muscle",
        "activity": "Moderate",
        "experience": "Beginner",
        "days_per_week": 4,
        "equipment": ["Body Only", "Dumbbell", "Machine"],
        "focus_areas": ["Chest", "Back", "Legs"],
    }


def ensure_storage() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for path, columns in [
        (USERS_PATH, USER_COLUMNS),
        (PROFILES_PATH, PROFILE_COLUMNS),
        (WORKOUTS_PATH, WORKOUT_COLUMNS),
        (MEALS_PATH, MEAL_COLUMNS),
        (PROGRESS_PATH, PROGRESS_COLUMNS),
    ]:
        if not path.exists():
            pd.DataFrame(columns=columns).to_csv(path, index=False)


def read_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns].copy()


def write_csv(path: Path, df: pd.DataFrame, columns: list[str]) -> None:
    output = df.copy()
    for col in columns:
        if col not in output.columns:
            output[col] = ""
    output[columns].to_csv(path, index=False)


def list_to_storage(values: list[str]) -> str:
    return "|".join(values)


def storage_to_list(raw: object) -> list[str]:
    if pd.isna(raw) or raw == "":
        return []
    return [item for item in str(raw).split("|") if item]


def normalize_username(username: str) -> str:
    return username.strip().lower()


def hash_password(password: str) -> str:
    return sha256(password.encode("utf-8")).hexdigest()


def register_user(username: str, password: str) -> tuple[bool, str]:
    username = normalize_username(username)
    if len(username) < 3 or not username.replace("_", "").replace("-", "").isalnum():
        return False, "Username must be at least 3 characters and use only letters, numbers, _ or -."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    users_df = read_csv(USERS_PATH, USER_COLUMNS)
    if not users_df[users_df["username"] == username].empty:
        return False, "This username already exists."

    users_df.loc[len(users_df)] = {
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    write_csv(USERS_PATH, users_df, USER_COLUMNS)
    save_profile(username, default_profile(username.title()))
    return True, "Account created successfully."


def authenticate_user(username: str, password: str) -> bool:
    username = normalize_username(username)
    users_df = read_csv(USERS_PATH, USER_COLUMNS)
    match = users_df[users_df["username"] == username]
    if match.empty:
        return False
    return match.iloc[0]["password_hash"] == hash_password(password)


def save_profile(username: str, profile: dict) -> None:
    profiles_df = read_csv(PROFILES_PATH, PROFILE_COLUMNS)
    profiles_df = profiles_df[profiles_df["username"] != username]
    profiles_df.loc[len(profiles_df)] = {
        "username": username,
        "name": profile["name"],
        "age": int(profile["age"]),
        "sex": profile["sex"],
        "height_cm": float(profile["height_cm"]),
        "weight_kg": float(profile["weight_kg"]),
        "goal": profile["goal"],
        "activity": profile["activity"],
        "experience": profile["experience"],
        "days_per_week": int(profile["days_per_week"]),
        "equipment": list_to_storage(profile["equipment"]),
        "focus_areas": list_to_storage(profile["focus_areas"]),
    }
    write_csv(PROFILES_PATH, profiles_df, PROFILE_COLUMNS)


def load_profile(username: str) -> dict:
    profiles_df = read_csv(PROFILES_PATH, PROFILE_COLUMNS)
    match = profiles_df[profiles_df["username"] == username]
    if match.empty:
        profile = default_profile(username.title())
        save_profile(username, profile)
        return profile

    row = match.iloc[0]
    profile = default_profile(str(row["name"]) if pd.notna(row["name"]) else username.title())
    profile.update(
        {
            "name": row["name"],
            "age": int(float(row["age"])),
            "sex": row["sex"],
            "height_cm": int(float(row["height_cm"])),
            "weight_kg": float(row["weight_kg"]),
            "goal": row["goal"],
            "activity": row["activity"],
            "experience": row["experience"],
            "days_per_week": int(float(row["days_per_week"])),
            "equipment": storage_to_list(row["equipment"]),
            "focus_areas": storage_to_list(row["focus_areas"]),
        }
    )
    return profile


def append_record(path: Path, columns: list[str], record: dict) -> None:
    df = read_csv(path, columns)
    df.loc[len(df)] = record
    write_csv(path, df, columns)


def load_user_records(path: Path, columns: list[str], username: str) -> list[dict]:
    df = read_csv(path, columns)
    user_df = df[df["username"] == username].copy()
    if user_df.empty:
        return []
    return user_df.to_dict("records")


def clear_user_records(path: Path, columns: list[str], username: str) -> None:
    df = read_csv(path, columns)
    df = df[df["username"] != username]
    write_csv(path, df, columns)
