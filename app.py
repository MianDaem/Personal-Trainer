from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.yaml"
PROFILE_FILE = BASE_DIR / "user_profiles.csv"
DEFAULT_BUDGET = 50000.0
ADMIN_ROLE = "admin"
EXPENSE_COLUMNS = ["Date", "Category", "Item", "Amount"]
PROFILE_COLUMNS = ["username", "full_name", "email", "phone", "monthly_budget", "currency", "city", "notes"]
CATEGORY_OPTIONS = ["Food", "Transport", "Bills", "Shopping", "Entertainment", "Health", "Education", "Other"]


def ensure_config() -> dict:
    if not CONFIG_FILE.exists():
        initial_config = {
            "credentials": {"usernames": {}},
            "cookie": {"expiry_days": 30, "key": "auth_key", "name": "expense_cookie"},
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            yaml.dump(initial_config, file, default_flow_style=False)
    with open(CONFIG_FILE, encoding="utf-8") as file:
        config = yaml.load(file, Loader=SafeLoader) or {}
    config.setdefault("credentials", {}).setdefault("usernames", {})
    config.setdefault("cookie", {"expiry_days": 30, "key": "auth_key", "name": "expense_cookie"})
    return config


def save_config(config: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        yaml.dump(config, file, default_flow_style=False, sort_keys=False)


def ensure_profile_storage() -> None:
    if not PROFILE_FILE.exists():
        pd.DataFrame(columns=PROFILE_COLUMNS).to_csv(PROFILE_FILE, index=False)


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(34, 197, 94, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(59, 130, 246, 0.14), transparent 26%),
                linear-gradient(180deg, #07111f 0%, #0f172a 45%, #122033 100%);
            color: #e2e8f0;
        }
        [data-testid="stSidebar"] {
            background: rgba(5, 12, 24, 0.94);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        .hero-card, .glass-card {
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 22px;
            padding: 1.15rem 1.1rem;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.24);
        }
        .hero-card h1, .hero-card h3 {
            color: #f8fafc;
            margin-bottom: 0.25rem;
        }
        .muted { color: #94a3b8; font-size: 0.96rem; }
        .pill {
            display: inline-block; padding: 0.24rem 0.7rem; border-radius: 999px;
            margin-right: 0.35rem; margin-bottom: 0.35rem;
            background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.25); color: #d1fae5;
            font-size: 0.84rem;
        }
        .stButton > button, .stFormSubmitButton > button {
            width: 100%; min-height: 2.85rem; border-radius: 14px;
            border: 1px solid rgba(34, 197, 94, 0.28);
            background: linear-gradient(135deg, #144f3a 0%, #1d6d53 100%);
            color: #f8fafc; font-weight: 600;
        }
        div[data-testid="stMetric"] {
            background: rgba(15, 23, 42, 0.65);
            border: 1px solid rgba(148, 163, 184, 0.14);
            padding: 0.8rem; border-radius: 18px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_user_file(username: str) -> Path:
    return BASE_DIR / f"data_{username}_expenses.csv"


def ensure_user_file(username: str) -> Path:
    user_file = get_user_file(username)
    if not user_file.exists():
        pd.DataFrame(columns=EXPENSE_COLUMNS).to_csv(user_file, index=False)
    return user_file


def read_expenses(username: str) -> pd.DataFrame:
    df = pd.read_csv(ensure_user_file(username))
    if df.empty:
        return pd.DataFrame(columns=EXPENSE_COLUMNS)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
    return df.dropna(subset=["Date"]).copy()


def save_expenses(username: str, df: pd.DataFrame) -> None:
    output = df.copy()
    output["Date"] = pd.to_datetime(output["Date"]).dt.strftime("%Y-%m-%d")
    output.to_csv(ensure_user_file(username), index=False)


def read_profiles() -> pd.DataFrame:
    ensure_profile_storage()
    profiles = pd.read_csv(PROFILE_FILE)
    for column in PROFILE_COLUMNS:
        if column not in profiles.columns:
            profiles[column] = ""
    return profiles[PROFILE_COLUMNS].copy()


def save_profiles(df: pd.DataFrame) -> None:
    output = df.copy()
    for column in PROFILE_COLUMNS:
        if column not in output.columns:
            output[column] = ""
    output[PROFILE_COLUMNS].to_csv(PROFILE_FILE, index=False)


def build_full_name(username: str, config: dict) -> str:
    details = config["credentials"]["usernames"].get(username, {})
    full_name = f"{str(details.get('first_name') or '').strip()} {str(details.get('last_name') or '').strip()}".strip()
    return full_name or username.title()


def get_user_profile(username: str, config: dict) -> dict:
    profiles = read_profiles()
    record = profiles[profiles["username"] == username]
    default_profile = {
        "username": username,
        "full_name": build_full_name(username, config),
        "email": config["credentials"]["usernames"].get(username, {}).get("email", ""),
        "phone": "",
        "monthly_budget": DEFAULT_BUDGET,
        "currency": "Rs",
        "city": "",
        "notes": "",
    }
    if record.empty:
        profiles.loc[len(profiles)] = default_profile
        save_profiles(profiles)
        return default_profile
    row = record.iloc[0].to_dict()
    row["monthly_budget"] = float(row.get("monthly_budget", DEFAULT_BUDGET) or DEFAULT_BUDGET)
    row["full_name"] = row.get("full_name") or default_profile["full_name"]
    row["email"] = row.get("email") or default_profile["email"]
    row["phone"] = row.get("phone", "")
    row["currency"] = row.get("currency") or "Rs"
    row["city"] = row.get("city", "")
    row["notes"] = row.get("notes", "")
    return row


def save_user_profile(profile: dict) -> None:
    profiles = read_profiles()
    profiles = profiles[profiles["username"] != profile["username"]]
    profiles.loc[len(profiles)] = profile
    save_profiles(profiles)


def sync_profile_from_config(username: str, profile: dict, config: dict) -> dict:
    profile["full_name"] = build_full_name(username, config)
    profile["email"] = config["credentials"]["usernames"].get(username, {}).get("email", profile.get("email", ""))
    return profile


def user_is_admin(username: str, config: dict) -> bool:
    roles = config["credentials"]["usernames"].get(username, {}).get("roles")
    if isinstance(roles, list):
        return ADMIN_ROLE in roles
    if isinstance(roles, str):
        return roles.lower() == ADMIN_ROLE
    return username == "admin"


def get_activity_rows(config: dict) -> pd.DataFrame:
    rows = []
    for username in sorted(config["credentials"]["usernames"].keys()):
        expense_df = read_expenses(username)
        profile = get_user_profile(username, config)
        rows.append({
            "Username": username,
            "Full Name": profile["full_name"],
            "Email": profile["email"],
            "Transactions": len(expense_df),
            "Total Spent": round(expense_df["Amount"].sum(), 2) if not expense_df.empty else 0.0,
            "Last Activity": expense_df["Date"].max().strftime("%Y-%m-%d") if not expense_df.empty else "No activity",
            "Monthly Budget": profile["monthly_budget"],
            "Admin": "Yes" if user_is_admin(username, config) else "No",
        })
    return pd.DataFrame(rows)


def delete_user(username: str, config: dict) -> None:
    config["credentials"]["usernames"].pop(username, None)
    save_config(config)
    profiles = read_profiles()
    save_profiles(profiles[profiles["username"] != username])
    user_file = get_user_file(username)
    if user_file.exists():
        user_file.unlink()


def update_user_credentials(username: str, email: str, first_name: str, last_name: str, password: str | None, make_admin: bool, config: dict) -> str:
    details = config["credentials"]["usernames"][username]
    details["email"] = email.strip()
    details["first_name"] = first_name.strip()
    details["last_name"] = last_name.strip()
    details["roles"] = [ADMIN_ROLE] if make_admin else None
    if password:
        details["password"] = stauth.Hasher([password]).generate()[0]
    save_config(config)
    profile = get_user_profile(username, config)
    profile["full_name"] = build_full_name(username, config)
    profile["email"] = email.strip()
    save_user_profile(profile)
    return "User credentials updated."


def render_auth_screen(authenticator, config: dict) -> None:
    st.title("Expense Command Center")
    st.caption("Track spending, manage monthly budget, and review insights from one place.")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab2:
        try:
            before_count = len(config["credentials"]["usernames"])
            if authenticator.register_user(location="main"):
                after_count = len(config["credentials"]["usernames"])
                if after_count > before_count:
                    latest_username = sorted(config["credentials"]["usernames"].keys())[-1]
                    config["credentials"]["usernames"][latest_username]["roles"] = None
                    save_config(config)
                    st.success("Registration successful. Please switch to Login.")
                else:
                    st.info("Fill out the form to create a new account.")
        except Exception as exc:
            if "already exists" in str(exc).lower():
                st.error("This username is already taken. Please choose another one.")
            else:
                st.error(f"Registration Error: {exc}")
    with tab1:
        authenticator.login(location="main")
        if st.session_state.get("authentication_status") is False:
            st.error("Username/password is incorrect")
        elif st.session_state.get("authentication_status") is None:
            st.info("Please login or register to manage your expenses.")


def render_sidebar(username: str, name: str, authenticator, profile: dict):
    st.sidebar.title(f"Welcome, {name}")
    st.sidebar.caption(f"Account: {username}")
    st.sidebar.markdown("---")
    with st.sidebar.form("expense_form"):
        exp_date = st.date_input("Date", date.today())
        category = st.selectbox("Category", CATEGORY_OPTIONS)
        item = st.text_input("Item Name")
        amount = st.number_input("Amount", min_value=0.0, step=50.0)
        submitted = st.form_submit_button("Save Expense")
    if submitted:
        if item.strip() and amount > 0:
            return exp_date, category, item.strip(), float(amount)
        st.sidebar.error("Please enter a valid item and amount greater than zero.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Profile & Budget")
    with st.sidebar.form("profile_form"):
        full_name = st.text_input("Full Name", value=profile["full_name"])
        phone = st.text_input("Phone", value=profile["phone"])
        city = st.text_input("City", value=profile["city"])
        monthly_budget = st.number_input("Monthly Budget", min_value=0.0, value=float(profile["monthly_budget"]), step=500.0)
        currency = st.text_input("Currency", value=profile["currency"])
        notes = st.text_area("Notes", value=profile["notes"])
        save_profile_clicked = st.form_submit_button("Save Personal Details")
    if save_profile_clicked:
        profile["full_name"] = full_name.strip() or profile["full_name"]
        profile["phone"] = phone.strip()
        profile["city"] = city.strip()
        profile["monthly_budget"] = float(monthly_budget)
        profile["currency"] = currency.strip() or "Rs"
        profile["notes"] = notes.strip()
        save_user_profile(profile)
        st.sidebar.success("Personal details updated.")

    st.sidebar.markdown("---")
    authenticator.logout("Logout", "sidebar")
    return None, "", "", 0.0


def render_filters(df: pd.DataFrame):
    st.sidebar.markdown("---")
    st.sidebar.header("Filter Analytics")
    view_option = st.sidebar.radio("Select Scope:", ["All-Time", "Current Month", "Custom Date Range"])
    display_df = df.copy()
    title_text = "All-Time Statistics"
    if view_option == "Current Month":
        current_month = date.today().strftime("%Y-%m")
        display_df = df[df["Date"].dt.strftime("%Y-%m") == current_month]
        title_text = f"Stats for {date.today().strftime('%B %Y')}"
    elif view_option == "Custom Date Range":
        today = date.today()
        start_default = today - pd.Timedelta(days=7)
        date_range = st.sidebar.date_input("Select Range", value=(start_default, today), max_value=today)
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            display_df = df[(df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)]
            title_text = f"Stats from {start_date} to {end_date}"
        else:
            st.info("Please select both a start and end date in the sidebar.")
            st.stop()
    return display_df, title_text


def render_dashboard(df: pd.DataFrame, display_df: pd.DataFrame, profile: dict, name: str) -> None:
    currency = profile["currency"] or "Rs"
    st.markdown(
        f"""
        <div class="hero-card">
            <h1>{name}'s Expense Dashboard</h1>
            <p class="muted">Monthly budget: <strong>{currency}{profile['monthly_budget']:,.0f}</strong> | City: <strong>{profile['city'] or 'Not set'}</strong></p>
            <span class="pill">Budget-aware tracking</span><span class="pill">Personal details</span><span class="pill">Live analytics</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total = display_df["Amount"].sum() if not display_df.empty else 0.0
    avg_transaction = display_df["Amount"].mean() if not display_df.empty else 0.0
    month_df = df[df["Date"].dt.strftime("%Y-%m") == date.today().strftime("%Y-%m")]
    monthly_spent = month_df["Amount"].sum() if not month_df.empty else 0.0
    remaining_budget = max(float(profile["monthly_budget"]) - monthly_spent, 0.0)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Spent", f"{currency}{total:,.2f}")
    m2.metric("Average Transaction", f"{currency}{avg_transaction:,.2f}")
    m3.metric("This Month Spent", f"{currency}{monthly_spent:,.2f}")
    m4.metric("Remaining Budget", f"{currency}{remaining_budget:,.2f}")

    col1, col2 = st.columns(2)
    with col1:
        if not display_df.empty:
            st.plotly_chart(px.pie(display_df, values="Amount", names="Category", hole=0.35, title="Spending by Category"), use_container_width=True)
        else:
            st.info("No data available for this filter.")
    with col2:
        budget_frame = pd.DataFrame({"Type": ["Spent Budget", "Remaining Budget"], "Amount": [monthly_spent, remaining_budget]})
        st.plotly_chart(px.pie(budget_frame, values="Amount", names="Type", hole=0.45, title="Monthly Budget Status"), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        if not display_df.empty:
            daily_trend = display_df.groupby("Date")["Amount"].sum().reset_index()
            st.plotly_chart(px.area(daily_trend, x="Date", y="Amount", title="Daily Spending Trend"), use_container_width=True)
    with c2:
        if not display_df.empty:
            top_items = display_df.groupby("Item")["Amount"].sum().sort_values(ascending=False).head(7).reset_index()
            st.plotly_chart(px.bar(top_items, x="Amount", y="Item", orientation="h", title="Top Expense Items"), use_container_width=True)


def render_history(display_df: pd.DataFrame, df: pd.DataFrame, username: str, profile: dict) -> None:
    currency = profile["currency"] or "Rs"
    st.markdown("---")
    st.subheader("Transaction History")
    if not display_df.empty:
        st.dataframe(display_df.sort_values("Date", ascending=False), use_container_width=True, column_config={
            "Amount": st.column_config.NumberColumn(format=f"{currency}%.2f"),
            "Date": st.column_config.DateColumn(format="DD/MM/YYYY"),
        })
    else:
        st.info("No transactions found for the selected filter.")

    with st.expander("Manage Filtered Data"):
        left, right = st.columns(2)
        with left:
            if not display_df.empty:
                delete_options = {f"{idx}: {row['Item']} ({currency}{row['Amount']:.2f})": idx for idx, row in display_df.iterrows()}
                selected = st.selectbox("Select entry", list(delete_options.keys()))
                if st.button("Confirm Delete"):
                    save_expenses(username, df.drop(delete_options[selected]))
                    st.success("Entry removed.")
                    st.rerun()
        with right:
            confirm = st.checkbox("Enable filtered reset")
            if st.button("Clear Filtered Data", disabled=not confirm):
                save_expenses(username, df[~df.index.isin(display_df.index)])
                st.warning("Filtered records cleared.")
                st.rerun()


def render_admin_panel(config: dict, current_username: str) -> None:
    st.markdown("---")
    st.subheader("Admin Panel")
    activity_df = get_activity_rows(config)
    if not activity_df.empty:
        st.dataframe(activity_df, use_container_width=True, hide_index=True)
    usernames = sorted(config["credentials"]["usernames"].keys())
    selected_user = st.selectbox("Manage user", usernames)
    details = config["credentials"]["usernames"][selected_user]
    profile = get_user_profile(selected_user, config)
    tab1, tab2, tab3 = st.tabs(["Activity", "Update Credentials", "Delete User"])
    with tab1:
        user_expenses = read_expenses(selected_user)
        if user_expenses.empty:
            st.info("This user has no expense activity yet.")
        else:
            st.dataframe(user_expenses.sort_values("Date", ascending=False).head(20), use_container_width=True, hide_index=True)
    with tab2:
        with st.form("admin_update_form"):
            email = st.text_input("Email", value=details.get("email", ""))
            first_name = st.text_input("First Name", value=details.get("first_name", ""))
            last_name = st.text_input("Last Name", value=details.get("last_name", ""))
            new_password = st.text_input("New Password", type="password", placeholder="Leave blank to keep current password")
            make_admin = st.checkbox("Grant admin access", value=user_is_admin(selected_user, config))
            submitted = st.form_submit_button("Update User")
        if submitted:
            st.success(update_user_credentials(selected_user, email, first_name, last_name, new_password or None, make_admin, config))
            st.rerun()
        st.markdown(f"<div class='glass-card'><h3>Stored Profile</h3><p class='muted'>Budget: {profile['currency']}{float(profile['monthly_budget']):,.0f}</p><p class='muted'>Phone: {profile['phone'] or 'Not set'} | City: {profile['city'] or 'Not set'}</p></div>", unsafe_allow_html=True)
    with tab3:
        if selected_user == current_username:
            st.warning("You cannot delete your own active account from this session.")
        else:
            confirm_delete = st.checkbox(f"I understand deleting `{selected_user}` removes their account and expense file.")
            if st.button("Delete User", disabled=not confirm_delete):
                delete_user(selected_user, config)
                st.success("User deleted successfully.")
                st.rerun()


def main() -> None:
    config = ensure_config()
    ensure_profile_storage()
    st.set_page_config(page_title="Personal Spend Tracker", layout="wide")
    apply_styles()
    authenticator = stauth.Authenticate(config["credentials"], config["cookie"]["name"], config["cookie"]["key"], config["cookie"]["expiry_days"])

    if not st.session_state.get("authentication_status"):
        render_auth_screen(authenticator, config)
        return

    username = st.session_state["username"]
    profile = sync_profile_from_config(username, get_user_profile(username, config), config)
    save_user_profile(profile)
    name = profile["full_name"]

    exp_date, category, item, amount = render_sidebar(username, name, authenticator, profile)
    if item and amount > 0:
        df = read_expenses(username)
        df = pd.concat([df, pd.DataFrame([[exp_date, category, item, amount]], columns=EXPENSE_COLUMNS)], ignore_index=True)
        save_expenses(username, df)
        st.sidebar.success("Expense recorded.")
        st.rerun()

    df = read_expenses(username)
    if df.empty:
        st.title(f"Hello {name}")
        st.info("Your expense history is empty. Add your first expense from the sidebar.")
    else:
        display_df, title_text = render_filters(df)
        st.subheader(title_text)
        render_dashboard(df, display_df, profile, name)
        render_history(display_df, df, username, profile)

    if user_is_admin(username, config):
        render_admin_panel(config, username)


if __name__ == "__main__":
    main()
