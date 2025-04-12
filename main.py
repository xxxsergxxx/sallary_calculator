import streamlit as st
import pandas as pd
from datetime import date, datetime

# 📌 Святкові дні України (2025)
ukr_holidays_2025 = [
    "2025-01-01", "2025-01-07", "2025-03-08",
    "2025-04-20", "2025-05-01", "2025-05-09",
    "2025-06-08", "2025-06-28", "2025-08-24",
    "2025-10-14", "2025-12-25"
]
ukr_holidays_2025 = [datetime.strptime(d, "%Y-%m-%d").date() for d in ukr_holidays_2025]

# 📌 Назви місяців українською
ukr_months = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
    5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
    9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень"
}

# 📌 Дні тижня українською
ukr_weekdays = {
    0: 'Понеділок', 1: 'Вівторок', 2: 'Середа',
    3: 'Четвер', 4: 'П’ятниця', 5: 'Субота', 6: 'Неділя'
}

# 📌 Сайдбар
st.sidebar.title("⚙️ Налаштування")
rate = st.sidebar.number_input("Тариф (грн/год)", value=10.0, step=0.5)
start_date = st.sidebar.date_input("Початкова дата", value=date(2025, 1, 1))
end_date = st.sidebar.date_input("Кінцева дата", value=date(2025, 1, 31))

if start_date > end_date:
    st.error("❌ Початкова дата не може бути пізніше кінцевої")
    st.stop()

# 📤 Завантаження табелю з файлу
uploaded_file = st.file_uploader("📤 Завантажити табель з файлу", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file, parse_dates=["Дата"])
    required_cols = {"Дата", "Кількість годин"}
    if not required_cols.issubset(df.columns):
        st.error("❌ Файл повинен містити колонки 'Дата' та 'Кількість годин'")
    else:
        df["Дата"] = pd.to_datetime(df["Дата"])
        df["День тижня"] = df["Дата"].dt.dayofweek.map(ukr_weekdays)
        df["Свято"] = df["Дата"].dt.date.isin(ukr_holidays_2025).map({True: "Так", False: "Ні"})
        st.session_state.edited_df = df.copy()

# 📅 Генерація табелю при першому запуску
if "edited_df" not in st.session_state:
    all_days = pd.date_range(start=start_date, end=end_date, freq='D')
    df = pd.DataFrame({"Дата": all_days})
    df["День тижня"] = df["Дата"].dt.dayofweek.map(ukr_weekdays)
    df["Свято"] = df["Дата"].dt.date.isin(ukr_holidays_2025).map({True: "Так", False: "Ні"})
    df["Кількість годин"] = ""
    st.session_state.edited_df = df.copy()

# 🕗 Автозаповнення
st.title("📋 Табель робочих годин")
auto_fill = st.checkbox("🕗 Автоматично заповнити 8 годин для робочих днів")

df_to_edit = st.session_state.edited_df.copy()

if auto_fill:
    def auto_fill_hours(row):
        if (row["День тижня"] not in ["Субота", "Неділя"]) and row["Свято"] == "Ні":
            return 8.0 if row["Кількість годин"] in [None, "", 0, 0.0] else row["Кількість годин"]
        return row["Кількість годин"]

    df_to_edit["Кількість годин"] = df_to_edit.apply(auto_fill_hours, axis=1)

# ✏️ Редагування
edited_df = st.data_editor(
    df_to_edit,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Кількість годин": st.column_config.NumberColumn(
            "Кількість годин",
            help="Введіть кількість відпрацьованих годин за день",
            min_value=0,
            max_value=24,
            step=0.5,
            format="%.1f"
        )
    },
    disabled=["Дата", "День тижня", "Свято"]
)

# 💾 Збереження
st.session_state.edited_df = edited_df

# 💸 Розрахунок зарплати
def calculate_salary_details(row, rate):
    hours = row["Кількість годин"]
    day = row["День тижня"]
    is_holiday = row["Свято"] == "Так"

    if pd.isna(hours) or hours == "":
        return pd.Series([0.0, 0.0, 0.0, 0.0])

    hours = float(hours)

    if day == "Неділя" or is_holiday:
        gross = hours * rate * 2.0
    elif day == "Субота":
        if hours <= 2:
            gross = hours * rate * 1.5
        else:
            gross = 2 * rate * 1.5 + (hours - 2) * rate * 2.0
    else:
        if hours <= 8:
            gross = hours * rate
        elif hours <= 10:
            gross = 8 * rate + (hours - 8) * rate * 1.5
        else:
            gross = 8 * rate + 2 * rate * 1.5 + (hours - 10) * rate * 2.0

    pdfo = gross * 0.18
    military = gross * 0.050
    clean = gross - pdfo - military

    return pd.Series([gross, clean, pdfo, military])

edited_df[["Брудна зарплата", "Чиста зарплата", "ПДФО", "Військовий збір"]] = edited_df.apply(
    lambda row: calculate_salary_details(row, rate=rate), axis=1
)

# 📊 Підсумки
st.markdown("### 📊 Підсумки")
col1, col2 = st.columns(2)
col1.metric("💰 Брудна зарплата", f"{edited_df['Брудна зарплата'].sum():.2f} грн")
col2.metric("🧾 Чиста зарплата", f"{edited_df['Чиста зарплата'].sum():.2f} грн")

# 💾 Збереження у файл
month_name = ukr_months[start_date.month]
year = start_date.year
file_name = f"Табель_{month_name}_{year}.csv"

st.download_button(
    label="💾 Завантажити табель",
    data=edited_df.to_csv(index=False).encode('utf-8-sig'),
    file_name=file_name,
    mime="text/csv"
)
