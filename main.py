import streamlit as st
import pandas as pd
import calendar
import locale

locale.setlocale(locale.LC_TIME, "uk_UA.UTF-8")  # для Linux/Mac
# locale.setlocale(locale.LC_TIME, "ukr")        # для Windows, якщо підтримується

from datetime import date, datetime






# 📌 national days of Ukraine (2025)
ukr_holidays_2025 = [
    "2025-01-01", "2025-01-07", "2025-03-08",
    "2025-04-20", "2025-05-01", "2025-05-09",
    "2025-06-08", "2025-06-28", "2025-08-24",
    "2025-10-14", "2025-12-25"
]
ukr_holidays_2025 = [datetime.strptime(d, "%Y-%m-%d").date() for d in ukr_holidays_2025]

ukr_months = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
    5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
    9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень"
}


# 📌 Ukrainian days of week
ukr_weekdays = {
    0: 'Понеділок', 1: 'Вівторок', 2: 'Середа',
    3: 'Четвер', 4: 'П’ятниця', 5: 'Субота', 6: 'Неділя'
}

# 📌 Sidebar: sallary
st.sidebar.title("⚙️ Settings")
rate = st.sidebar.number_input("Тариф (грн/год)", value=10.0, step=0.5)
start_date = st.sidebar.date_input("Початкова дата", value=date(2025, 1, 1))
end_date = st.sidebar.date_input("Кінцева дата", value=date(2025, 1, 31))

if "df" in st.session_state:
    month_name = ukr_months[start_date.month]
    year = start_date.year
    file_name = f"Табель_{month_name}_{year}.csv"


    st.download_button(
        label="💾 Завантажити табель",
        data=st.session_state.df.to_csv(index=False).encode('utf-8-sig'),
        file_name=file_name,
        mime="text/csv"
    )



uploaded_file = st.file_uploader("📤 Завантажити табель з файлу", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, parse_dates=["Дата"])
    df["Дата"] = pd.to_datetime(df["Дата"])
    df["День тижня"] = df["Дата"].dt.dayofweek.map(ukr_weekdays)
    df["Свято"] = df["Дата"].dt.date.isin(ukr_holidays_2025).map({True: "Так", False: "Ні"})
    
    st.session_state.df = df
    st.session_state.edited_df = df.copy()  



# 📌 Check diapasone 
if start_date > end_date:
    st.error("❌ Початкова дата не може бути пізніше кінцевої")
    st.stop()

# 📌 Table generation
if "df" not in st.session_state:
    all_days = pd.date_range(start=start_date, end=end_date, freq='D')
    df = pd.DataFrame({"Дата": all_days})
    df["День тижня"] = df["Дата"].dt.dayofweek.map(ukr_weekdays)
    df["Свято"] = df["Дата"].dt.date.isin(ukr_holidays_2025).map({True: "Так", False: "Ні"})
    df["Кількість годин"] = ""
    st.session_state.df = df.copy()

# 📌 Editted table
st.title("📋 Табель робочих годин")


month_name = start_date.strftime('%B')  # назва місяця
year = start_date.year
file_name = f"Табель_{month_name}_{year}.csv"

# 🕗 Botton auto filling 8 hours
if st.button("🕗 Заповнити 8 годин для робочих днів"):
    def auto_fill_hours(row):
        if (row["День тижня"] not in ["Субота", "Неділя"]) and row["Свято"] == "Ні":
            return 8.0
        return row["Кількість годин"]

    df = st.session_state.df.copy()
    df["Кількість годин"] = df.apply(auto_fill_hours, axis=1)
    st.session_state.df = df



# Making editable after filling
edited_df = st.data_editor(
    st.session_state.df,
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

st.session_state.df = edited_df  # Saving changes

# 📌 Function calculation sallary
def calculate_salary_details(row, rate):
    hours = row["Кількість годин"]
    day = row["День тижня"]
    is_holiday = row["Свято"] == "Так"

    if pd.isna(hours) or hours == "":
        return pd.Series([0.0, 0.0, 0.0, 0.0])

    hours = float(hours)

    # brutto
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

    # Відрахування
    pdfo = gross * 0.18
    military = gross * 0.050
    clean = gross - pdfo - military

    return pd.Series([gross, clean, pdfo, military])

# 📌 Calculating sallary
edited_df[["Брудна зарплата", "Чиста зарплата", "ПДФО", "Військовий збір"]] = edited_df.apply(
    lambda row: calculate_salary_details(row, rate=rate), axis=1
)

# # 📌 output table
# st.markdown("### 💸 Розрахована зарплата")
# st.dataframe(edited_df)

# 📌 Summary
st.markdown("### 📊 Підсумки")
col1, col2 = st.columns(2)
col1.metric("💰 Брудна зарплата", f"{edited_df['Брудна зарплата'].sum():.2f} грн")
col2.metric("🧾 Чиста зарплата", f"{edited_df['Чиста зарплата'].sum():.2f} грн")
