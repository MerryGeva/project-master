#"https://docs.google.com/forms/d/e/1FAIpQLSf3vGFIikpAHVhZuSTPO04GdsP7BwxejG8lo-Voo0sKIXBdoA/viewform?usp=pp_url&entry.140138051=022168199&entry.1070948481=merry+geva&entry.1153840624=1&entry.760419112=cameras&entry.4763804=jkljsakal"
#"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?output=xlsx"

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

# --- הגדרות אבטחה וחיבור (החליפי בנתונים מהפורם שלך) ---
# ה-URL שנגמר ב-formResponse

FORM_URL = "https://docs.google.com/forms/d/e/18ZgQE2gaWfmIy_cryTeTKLFebUi0DPLopeDgA6IB8NI/formResponse"
SHEET_CSV_URL="https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?output=xlsx"
# FORM_ID = "18ZgQE2gaWfmIy_cryTeTKLFebUi0DPLopeDgA6IB8NI"

# מזהי השדות (entry.xxxx) כפי שמופיעים ב-Pre-filled link של הפורם
ENTRY_IDS = {
    "id": "entry.140138051",  # שדה ת"ז
    "name": "entry.1070948481",  # שדה שם התלמיד
    "stage": "entry.1153840624",  # שדה שלב
    "project": "entry.760419112",  # שדה שם הפרויקט
    "content": "entry.4763804"  # שדה תיאור/לינק
}


TEACHER_PASSWORD = "123"

# --- הגדרות דף ועיצוב ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[st-decorator='sidebar'] { direction: rtl; }
    .stTextInput input { text-align: right; }
    </style>
    """, unsafe_allow_html=True)


# --- פונקציות נתונים ---
def load_data_from_google():
    """טוען את כל ההגשות מהלינק הציבורי שפרסמת"""
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        return df
    except Exception as e:
        return pd.DataFrame()


def send_submission(data):
    """שולח את הנתונים לפורם"""
    payload = {
        ENTRY_IDS["id"]: data['id'],
        ENTRY_IDS["name"]: data['name'],
        ENTRY_IDS["stage"]: data['stage'],
        ENTRY_IDS["project"]: data['project'],
        ENTRY_IDS["content"]: data['content']
    }
    try:
        r = requests.post(FORM_URL, data=payload, timeout=10)
        return r.status_code == 200
    except:
        return False


# --- ניהול התחברות ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

if not st.session_state['logged_in']:
    st.title("🎓 Project Master - כניסה למערכת")
    tab1, tab2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])

    with tab1:
        sid = st.text_input("תעודת זהות (9 ספרות):", max_chars=9)
        sname = st.text_input("שם מלא:")
        if st.button("התחבר כתלמיד"):
            if len(sid) == 9 and sname:
                st.session_state.update({'logged_in': True, 'role': 'student', 'id': sid, 'name': sname})
                st.rerun()
            else:
                st.error("נא למלא ת\"ז תקינה ושם מלא")

    with tab2:
        mpwd = st.text_input("סיסמת מורה:", type="password")
        if st.button("התחבר כמורה"):
            if mpwd == TEACHER_PASSWORD:
                st.session_state.update({'logged_in': True, 'role': 'teacher'})
                st.rerun()
            else:
                st.error("סיסמה שגויה")
else:
    # --- תפריט צד (Sidebar) ---
    st.sidebar.title(f"שלום, {st.session_state.get('name', 'המורה')}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

    # --- ממשק מורה ---
    if st.session_state['role'] == 'teacher':
        st.sidebar.subheader("תפריט ניהול")
        menu = st.sidebar.radio("ניווט:", ["📊 דו\"ח הגשות כיתתי", "📥 בדיקת פרויקטים"])

        # טעינת נתונים בזמן אמת מהגוגל שייטס
        df_all = load_data_from_google()

        if menu == "📊 דו\"ח הגשות כיתתי":
            st.header("מטריצת הגשות כיתתית")
            if not df_all.empty:
                st.dataframe(df_all, use_container_width=True)

                # אפשרות להורדת הקובץ לאקסל
                csv = df_all.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 הורד נתונים כ-CSV", csv, "submissions.csv", "text/csv")
            else:
                st.warning("לא נמצאו נתונים בגיליון או שהלינק הציבורי לא תקין.")

        elif menu == "📥 בדיקת פרויקטים":
            st.header("סקירת הגשות אחרונות")
            st.info("כדי לעדכן סטטוסים (מאושר/תיקון) או לתת הערות, עשי זאת ישירות בגיליון הגוגל שלך.")
            if not df_all.empty:
                # מציג את 10 ההגשות האחרונות
                st.table(df_all.tail(10))

    # --- ממשק תלמיד ---
    elif st.session_state['role'] == 'student':
        st.header("🚀 הגשת שלב בפרויקט")

        # הצגת היסטוריית הגשות אישית (נטען מהגוגל שייטס הציבורי)
        df_all = load_data_from_google()
        if not df_all.empty:
            # סינון לפי הת"ז של התלמיד (בהנחה שת"ז בעמודה השנייה - תלוי בפורם שלך)
            my_history = df_all[df_all.iloc[:, 1].astype(str) == st.session_state['id']]
            if not my_history.empty:
                st.subheader("📍 המצב שלך:")
                st.dataframe(my_history.tail(3))

        stages = ["1. בחירת נושא", "2. אפיון", "3. ניתוח", "4. עיצוב", "5. קידוד", "6. הגשה סופית"]
        stage = st.selectbox("בחר שלב להגשה:", stages)
        p_name = st.text_input("שם הפרויקט:")
        link = st.text_input("קישור לתוצר (GitHub/Drive):")
        notes = st.text_area("הערות נוספות:")

        if st.button("🚀 שלח הגשה", width='stretch'):
            if not p_name or not link:
                st.error("חובה למלא שם פרויקט וקישור.")
            else:
                data = {
                    "id": st.session_state['id'],
                    "name": st.session_state['name'],
                    "stage": stage,
                    "project": p_name,
                    "content": f"Link: {link} | Notes: {notes}"
                }
                with st.spinner("שולח..."):
                    if send_submission(data):
                        st.success("נשלח בהצלחה! המורה יראה את זה תוך רגע.")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("תקלה בשליחה. בדקי שה-URL וה-ENTRY IDs תקינים.")