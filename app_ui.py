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


def update_sheets(df, worksheet_name):
    try:
        st.cache_data.clear()
        df_to_save = pd.DataFrame(df).astype(str)
        # עדכון הגיליון
        conn.update(worksheet=worksheet_name, data=df_to_save)
        st.success(f"✅ הנתונים סונכרנו בהצלחה ללשונית {worksheet_name} בגוגל!")
        st.balloons()
    except Exception as e:
        st.error(f"❌ שגיאת סנכרון לגוגל: {e}")


def get_data(worksheet_name, expected_cols):
    try:
        # קריאה ישירה מגוגל עם ttl=0 כדי למנוע זיכרון ישן
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=expected_cols)
        return df.astype(str)
    except:
        return pd.DataFrame(columns=expected_cols)


# --- פונקציות ניהול נתונים (המפתח לפתרון) ---

def load_data(file, default_cols):
    # הגדרת מפה פשוטה בין שם הקובץ ללשונית בגוגל
    mapping = {
        STUDENTS_FILE: "students",
        DB_FILE: "submissions",
        CONFIG_FILE: "config"
    }

    if file in mapping:
        try:
            # קריאה ישירה בלי לבדוק מטא-דאטה
            df = conn.read(worksheet=mapping[file], ttl=0)
            if df is not None and not df.empty:
                return df.astype(str)
        except Exception as e:
            st.error(f"שגיאת טעינה מגוגל ({mapping[file]}): {e}")

    # אם נכשל, ננסה מהקובץ המקומי (ליתר ביטחון)
    if os.path.exists(file):
        return pd.read_csv(file, dtype={'ת"ז': str}).fillna("")
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