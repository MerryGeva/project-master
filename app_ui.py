#"https://docs.google.com/forms/d/e/1FAIpQLSf3vGFIikpAHVhZuSTPO04GdsP7BwxejG8lo-Voo0sKIXBdoA/viewform?usp=pp_url&entry.140138051=022168199&entry.1070948481=merry+geva&entry.1153840624=1&entry.760419112=cameras&entry.4763804=jkljsakal"


import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

# --- הגדרות אבטחה וחיבור (החליפי בנתונים מהפורם שלך) ---
# ה-URL שנגמר ב-formResponse

FORM_URL = "https://docs.google.com/forms/d/e/18ZgQE2gaWfmIy_cryTeTKLFebUi0DPLopeDgA6IB8NI/formResponse"
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

# --- הגדרות דף ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[st-decorator='sidebar'] { direction: rtl; }
    .stTextInput input { text-align: right; }
    </style>
    """, unsafe_allow_html=True)


# --- פונקציות עזר ---
def submit_to_google_form(data):
    """שליחה חרישית ל-Google Form ללא צורך בהרשאות מסובכות"""
    form_data = {
        ENTRY_IDS["id"]: data['id'],
        ENTRY_IDS["name"]: data['name'],
        ENTRY_IDS["stage"]: data['stage'],
        ENTRY_IDS["project"]: data['project'],
        ENTRY_IDS["content"]: data['content']
    }
    try:
        response = requests.post(FORM_URL, data=form_data)
        return response.status_code == 200
    except:
        return False


# --- ניהול מצב (Session State) ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user_id': None, 'user_name': None})

# --- מסך כניסה ---
if not st.session_state['logged_in']:
    st.title("🎓 Project Master - כניסה מאובטחת")
    tab1, tab2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])

    with tab1:
        sid = st.text_input("תעודת זהות:", max_chars=9)
        sname = st.text_input("שם מלא:")
        if st.button("התחבר כתלמיד"):
            if len(sid) == 9 and len(sname) > 1:
                st.session_state.update({'logged_in': True, 'role': 'student', 'user_id': sid, 'user_name': sname})
                st.rerun()
            else:
                st.error("אנא מלא תז תקינה ושם מלא ")

    with tab2:
        mpwd = st.text_input("סיסמת מורה:", type="password")
        if st.button("התחבר כמורה"):
            if mpwd == TEACHER_PASSWORD:
                st.session_state.update({'logged_in': True, 'role': 'teacher'})
                st.rerun()
            else:
                st.error("סיסמה שגויה")

else:
    # --- תפריט צד ---
    st.sidebar.title(f"שלום, {st.session_state.get('user_name', 'מורה')}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

    # --- ממשק תלמיד ---
    if st.session_state['role'] == 'student':
        st.header("🚀 הגשת תוצרים לפרויקט")

        stages = ["1. בחירת נושא", "2. אפיון", "3. ניתוח", "4. עיצוב", "5. קידוד", "6. הגשה סופית"]
        stage = st.selectbox("בחר שלב להגשה:", stages)

        p_name = st.text_input("שם הפרויקט:")
        content = st.text_area("תיאור הביצוע או קישור (GitHub/Drive):")

        if st.button("שלח הגשה למורה", width='stretch'):
            if not p_name or not content:
                st.error("חובה למלא את כל השדות")
            else:
                submission_data = {
                    "id": st.session_state['user_id'],
                    "name": st.session_state['user_name'],
                    "stage": stage,
                    "project": p_name,
                    "content": content
                }

            with st.spinner("שומר נתונים בבסיס הנתונים..."):
                if submit_to_google_form(submission_data):
                    st.success("✅ ההגשה נשלחה בהצלחה! המורה יראה זאת בגיליון שלו.")
                    st.balloons()
                    time.sleep(2)
                else:
                    st.error("תקלה טכנית בשליחה. ודא שהחיבור לאינטרנט תקין.")

    # --- ממשק מורה ---
    elif st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 ממשק ניהול מורה")
        st.write("כדי לראות את ההגשות, היכנסי לגיליון התגובות של ה-Google Form שלך.")

        st.info("💡 בשיטה זו, הנתונים נשמרים ישירות בגיליון גוגל שרק לך יש גישה אליו.")

        # אפשר להוסיף כאן כפתור שיפתח למורה את הגיליון בלינק ישיר
        if st.button("פתח גיליון הגשות (Google Sheets)"):
            st.write("לינק לגיליון שלך כאן...")
