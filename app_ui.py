import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

# --- הגדרות אבטחה וחיבור ---
# הלינק הנכון לשליחה (מבוסס על ה-ID ששלחת)
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSf3vGFIikpAHVhZuSTPO04GdsP7BwxejG8lo-Voo0sKIXBdoA/formResponse"

# לינקים ל-CSV של הלשוניות השונות
URL_SUBS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=1111779993&single=true&output=csv"
URL_STUDENTS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=1500993496&single=true&output=csv"
URL_CONFIG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=939170192&single=true&output=csv"

# מזהי השדות מה-Pre-filled link ששלחת
ENTRY_IDS = {
    "id": "entry.140138051",
    "name": "entry.1070948481",
    "stage": "entry.1153840624",
    "project": "entry.760419112",
    "content": "entry.4763804"
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


# --- פונקציות טעינת נתונים ---
def get_google_data(url):
    """פונקציה גנרית לטעינת CSV מגוגל עם מנגנון מניעת זיכרון מטמון"""
    try:
        t = int(time.time())
        final_url = f"{url}&cachebuster={t}"
        df = pd.read_csv(final_url)
        return df
    except:
        return pd.DataFrame()


def send_submission(data):
    """שולח את הנתונים לפורם"""
    payload = {ENTRY_IDS[k]: v for k, v in data.items()}
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
        sid = st.text_input("תעודת זהות:", max_chars=9)
        if st.button("התחבר כתלמיד"):
            students_df = get_google_data(URL_STUDENTS)
            if not students_df.empty and sid in students_df.iloc[:, 0].astype(str).values:
                # מושך את השם מהעמודה השנייה של רשימת התלמידים
                sname = students_df[students_df.iloc[:, 0].astype(str) == sid].iloc[0, 1]
                st.session_state.update({'logged_in': True, 'role': 'student', 'id': sid, 'name': sname})
                st.rerun()
            else:
                st.error("תעודת זהות לא נמצאה ברשימת התלמידים המאושרת")

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
    st.sidebar.title(f"שלום, {st.session_state.get('name', 'המורה')}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

    # --- ממשק מורה ---
    if st.session_state['role'] == 'teacher':
        menu = st.sidebar.radio("ניווט:", ["📊 דו\"ח הגשות כיתתי", "👥 רשימת תלמידים", "⚙️ הגדרת שלבים"])

        if menu == "📊 דו\"ח הגשות כיתתי":
            st.header("מטריצת הגשות")
            df_subs = get_google_data(URL_SUBS)
            st.dataframe(df_subs, use_container_width=True)

        elif menu == "👥 רשימת תלמידים":
            st.header("תלמידים רשומים במערכת")
            df_students = get_google_data(URL_STUDENTS)
            st.table(df_students)

        elif menu == "⚙️ הגדרת שלבים":
            st.header("שלבי פרויקט ודד-ליינים")
            df_config = get_google_data(URL_CONFIG)
            st.table(df_config)

    # --- ממשק תלמיד ---
    elif st.session_state['role'] == 'student':
        st.header(f"הגשת שלב - {st.session_state['name']}")

        # הצגת דד-ליינים מה-Config
        df_config = get_google_data(URL_CONFIG)
        if not df_config.empty:
            with st.expander("📅 צפה בלוח זמנים"):
                st.table(df_config)
            stages = df_config.iloc[:, 0].tolist()  # לוקח שמות שלבים מהעמודה הראשונה
        else:
            stages = ["שלב 1", "שלב 2"]

        # הגשה
        stage = st.selectbox("בחר שלב:", stages)
        p_name = st.text_input("שם הפרויקט:")
        link = st.text_area("קישור לתוצר או הערות:")

        if st.button("🚀 שלח הגשה", width='stretch'):
            if p_name and link:
                data = {
                    "id": st.session_state['id'],
                    "name": st.session_state['name'],
                    "stage": stage,
                    "project": p_name,
                    "content": link
                }
                if send_submission(data):
                    st.success("ההגשה נשלחה בהצלחה!")
                    st.balloons()
                else:
                    st.error("שגיאה בשליחה לפורם")
            else:
                st.error("נא למלא את כל השדות")