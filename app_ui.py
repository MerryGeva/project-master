import streamlit as st
import pandas as pd
import requests
import time

# --- הגדרות לינקים (כבר מעודכנים לפי מה ששלחת) ---
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSf3vGFIikpAHVhZuSTPO04GdsP7BwxejG8lo-Voo0sKIXBdoA/formResponse"
URL_SUBS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=1111779993&single=true&output=csv"
URL_STUDENTS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=1500993496&single=true&output=csv"
URL_CONFIG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=939170192&single=true&output=csv"

# לינק ישיר לגיליון גוגל (לצורך עריכה של המורה)
SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1jM5RGj_V2dxOfduViARSSKsYGO9LFslQydB5ympgjXA/edit"

ENTRY_IDS = {
    "id": "entry.140138051",
    "name": "entry.1070948481",
    "stage": "entry.1153840624",
    "project": "entry.760419112",
    "content": "entry.4763804"
}


# --- פונקציות טעינה ---
def get_google_data(url):
    try:
        t = int(time.time())
        return pd.read_csv(f"{url}&cache={t}")
    except:
        return pd.DataFrame()


# --- עיצוב הממשק ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("<style>.stApp { direction: rtl; text-align: right; } .stDataFrame { direction: rtl; }</style>",
            unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

# --- מסך כניסה ---
if not st.session_state['logged_in']:
    st.title("🎓 Project Master - ניהול פרויקטים")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])

    with t1:
        sid = st.text_input("הקלד תעודת זהות:")
        if st.button("התחבר"):
            students_df = get_google_data(URL_STUDENTS)
            # ניקוי רווחים והפיכה לסטרינג לצורך השוואה
            students_df.columns = ["ID", "Name"]  # כותרות זמניות לחיפוש
            if not students_df.empty and sid in students_df["ID"].astype(str).values:
                sname = students_df[students_df["ID"].astype(str) == sid]["Name"].values[0]
                st.session_state.update({'logged_in': True, 'role': 'student', 'id': sid, 'name': sname})
                st.rerun()
            else:
                st.error("תעודת זהות לא קיימת במערכת. פנה למורה.")

    with t2:
        pwd = st.text_input("סיסמת מורה:", type="password")
        if st.button("כניסה למערכת"):
            if pwd == "123":
                st.session_state.update({'logged_in': True, 'role': 'teacher'})
                st.rerun()

# --- תוכן המערכת ---
else:
    st.sidebar.title(f"שלום {st.session_state.get('name', 'המורה')}")
    if st.sidebar.button("התנתק"):
        st.session_state.clear()
        st.rerun()

    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה למורה")

        # כפתור עריכה בולט
        st.info("💡 כדי להוסיף תלמידים, לשנות תאריכים או לערוך שלבים - לחצי על הכפתור למטה:")
        st.link_button("📝 פתח גיליון נתונים לעריכה (Google Sheets)", SHEET_EDIT_URL)

        menu = st.tabs(["📊 מעקב הגשות", "👥 רשימת תלמידים", "📅 לוח זמנים"])

        with menu[0]:
            st.subheader("כל ההגשות שבוצעו")
            df_subs = get_google_data(URL_SUBS)
            st.dataframe(df_subs, use_container_width=True)

        with menu[1]:
            st.subheader("תלמידים המורשים להשתמש במערכת")
            df_students = get_google_data(URL_STUDENTS)
            if not df_students.empty:
                df_students.columns = ["תעודת זהות", "שם מלא"]
                st.table(df_students)

        with menu[2]:
            st.subheader("שלבי הפרויקט ותאריכי יעד")
            df_config = get_google_data(URL_CONFIG)
            if not df_config.empty:
                df_config.columns = ["שם השלב", "תאריך יעד אחרון"]
                st.table(df_config)

    elif st.session_state['role'] == 'student':
        st.header(f"הגשת פרויקט - {st.session_state['name']}")

        # הצגת דד-ליינים
        df_config = get_google_data(URL_CONFIG)
        if not df_config.empty:
            df_config.columns = ["שלב", "דד-ליין"]
            st.sidebar.subheader("📅 תאריכי יעד:")
            for index, row in df_config.iterrows():
                st.sidebar.write(f"**{row['שלב']}:** {row['דד-ליין']}")
            stages = df_config["שלב"].tolist()
        else:
            stages = ["בחירת נושא"]

        # טופס הגשה
        with st.form("sub_form"):
            stage = st.selectbox("בחר שלב להגשה:", stages)
            p_name = st.text_input("שם הפרויקט:")
            link = st.text_input("קישור לתוצר (Drive/GitHub):")
            notes = st.text_area("הערות למורה:")

            if st.form_submit_button("🚀 שלח הגשה"):
                if p_name and link:
                    data = {"id": st.session_state['id'], "name": st.session_state['name'],
                            "stage": stage, "project": p_name, "content": f"{link} | {notes}"}
                    payload = {ENTRY_IDS[k]: v for k, v in data.items()}
                    if requests.post(FORM_URL, data=payload).status_code == 200:
                        st.success("ההגשה עברה בהצלחה!")
                        st.balloons()
                    else:
                        st.error("תקלה בשליחה.")
                else:
                    st.error("נא למלא את כל השדות.")