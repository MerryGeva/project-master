import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
import time

# --- הגדרות קבצים ---
DB_FILE = "submissions.csv"
STUDENTS_FILE = "students_list.csv"
CONFIG_FILE = "system_config.csv"
TEACHER_PASSWORD = "123"

# --- הגדרות דף ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown(
    "<style>.stApp { direction: rtl; text-align: right; } div[st-decorator='sidebar'] { direction: rtl; }</style>",
    unsafe_allow_html=True)

# --- חיבור ל-Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)


def get_data(worksheet_name, expected_cols):
    try:
        # פקודה ישירה שעוקפת את המטא-דאטה
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is not None and not df.empty:
            return df.astype(str)
    except Exception as e:
        # אם יש שגיאה (כמו ה-200 המעצבן), אנחנו לא מציגים אותה
        # אלא פשוט מחזירים טבלה ריקה וממשיכים ל-CSV המקומי
        pass
    return pd.DataFrame(columns=expected_cols)

def update_sheets(df, worksheet_name):
    try:
        st.cache_data.clear()
        # המרה ל-DataFrame נקי בלי אינדקס
        df_to_save = pd.DataFrame(df).astype(str)

        # שימוש בחיבור הישיר לעדכון
        conn.update(worksheet=worksheet_name, data=df_to_save)

        st.success(f"✅ עודכן בהצלחה בגיליון גוגל ({worksheet_name})")
        st.balloons()
    except Exception as e:
        st.error(f"❌ שגיאת כתיבה: {e}")


def load_data(file, default_cols):
    # מפה שמקשרת בין הקובץ ללשונית בגוגל
    mapping = {
        STUDENTS_FILE: "students",
        DB_FILE: "submissions",
        CONFIG_FILE: "config"
    }

    # 1. נסיון קריאה מגוגל
    if file in mapping:
        df_google = get_data(mapping[file], default_cols)
        if not df_google.empty:
            return df_google

    # 2. אם גוגל נכשל או ריק, קריאה מה-CSV המקומי (שקיים ב-GitHub)
    if os.path.exists(file):
        try:
            return pd.read_csv(file, dtype={'ת"ז': str}).fillna("")
        except:
            return pd.DataFrame(columns=default_cols)

    return pd.DataFrame(columns=default_cols)

def save_data(df, file):
    # 1. שמירה מקומית (תמיד טוב לגיבוי)
    df.to_csv(file, index=False, encoding='utf-8-sig')

    # 2. שליחה לגוגל
    mapping = {
        STUDENTS_FILE: "students",
        DB_FILE: "submissions",
        CONFIG_FILE: "config"
    }
    if file in mapping:
        update_sheets(df, mapping[file])

# --- DEBUG - בדיקת חיבור ---
if st.sidebar.checkbox("בדיקת חיבור גוגל (Debug)"):
    try:
        # ניסיון לקרוא רק את השם של הגיליון
        spreadsheet_id = st.secrets["connections"]["gsheets"]["spreadsheet"]
        st.sidebar.write(f"ID: {spreadsheet_id}")
        # אם ה-inspect נכשל, ננסה פשוט לקרוא שורה אחת
        test_read = conn.read(worksheet="students", nrows=1)
        st.sidebar.success("✅ חיבור תקין לנתונים!")
    except Exception as e:
        st.sidebar.error(f"❌ שגיאת מטא-דאטה: {e}")

# --- טעינת נתונים ראשונית ---
config_df = load_data(CONFIG_FILE, ["שלב", "תאריך יעד"])
if config_df.empty:
    config_df = pd.DataFrame([
        {"שלב": "1. בחירת נושא", "תאריך יעד": "2026-03-01"},
        {"שלב": "2. אפיון", "תאריך יעד": "2026-03-15"}
    ])

subs_df = load_data(DB_FILE,
                    ["זמן הגשה", 'ת"ז', "סיסמה", "שם התלמיד", "שלב", "שם הפרויקט", "תיאור/לינק", "סטטוס", "הערות מורה",
                     "סטטוס זמן"])
students_df = load_data(STUDENTS_FILE, ["ת\"ז", "שם מלא"])

# --- לוגיקת האפליקציה (המשך הקוד שלך) ---
# (כאן מגיע שאר הקוד של הכניסה, ממשק מורה ותלמיד כפי שכתבת)
# הערה: ודאי שבכל מקום שכתבת save_data(df, file) בקוד המקורי, זה נשאר ככה.