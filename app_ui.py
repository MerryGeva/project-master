import streamlit as st
import pandas as pd
import requests
import time

# --- הגדרות לינקים (נשארים כפי שהיו) ---
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSf3vGFIikpAHVhZuSTPO04GdsP7BwxejG8lo-Voo0sKIXBdoA/formResponse"
URL_SUBS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=1111779993&single=true&output=csv"
URL_STUDENTS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=1500993496&single=true&output=csv"
URL_CONFIG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=939170192&single=true&output=csv"
SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1jM5RGj_V2dxOfduViARSSKsYGO9LFslQydB5ympgjXA/edit"

ENTRY_IDS = {
    "id": "entry.140138051",
    "name": "entry.1070948481",
    "stage": "entry.1153840624",
    "project": "entry.760419112",
    "content": "entry.4763804"
}


def get_safe_data(url):
    try:
        t = int(time.time())
        # מוסיפים אימות שהקובץ אכן מכיל נתונים
        df = pd.read_csv(f"{url}&cachebuster={t}", dtype=str).fillna("")
        return df
    except:
        return pd.DataFrame()


st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("<style>.stApp { direction: rtl; text-align: right; }</style>", unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

# --- כניסה ---
if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 תלמיד", "👨‍🏫 מורה"])

    with t1:
        sid = st.text_input("הקלד תעודת זהות:").strip()
        if st.button("כניסה"):
            students_df = get_safe_data(URL_STUDENTS)
            if not students_df.empty and len(students_df.columns) >= 2:
                # בדיקה חסינה: הופכים את כל העמודה הראשונה לטקסט נקי
                id_list = students_df.iloc[:, 0].astype(str).str.strip().tolist()
                if sid in id_list:
                    idx = id_list.index(sid)
                    sname = students_df.iloc[idx, 1]
                    st.session_state.update({'logged_in': True, 'role': 'student', 'id': sid, 'name': sname})
                    st.rerun()
                else:
                    st.error("תעודת זהות לא נמצאה ברשימה.")
            else:
                st.error("רשימת התלמידים ריקה או לא תקינה בגוגל שייטס.")

    with t2:
        pwd = st.text_input("סיסמה:", type="password")
        if st.button("כניסה כמורה"):
            if pwd == "123":
                st.session_state.update({'logged_in': True, 'role': 'teacher'})
                st.rerun()

# --- ממשק משתמש מחובר ---
else:
    st.sidebar.title(f"שלום {st.session_state.get('name', 'המורה')}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 ממשק ניהול מורה")
        st.link_button("📝 עריכת נתונים בגוגל (תלמידים/שלבים)", SHEET_EDIT_URL)

        t_subs, t_stud, t_conf = st.tabs(["📊 הגשות", "👥 תלמידים", "📅 לוח זמנים"])

        with t_subs:
            df = get_safe_data(URL_SUBS)
            st.dataframe(df, use_container_width=True)

        with t_stud:
            df_s = get_safe_data(URL_STUDENTS)
            if not df_s.empty:
                st.write("**רשימת תלמידים מאושרים:**")
                st.table(df_s)
            else:
                st.info("אין תלמידים רשומים כרגע.")

        with t_conf:
            df_c = get_safe_data(URL_CONFIG)
            if not df_c.empty:
                st.write("**לוח זמנים ושלבים:**")
                st.table(df_c)
            else:
                st.info("לא הוגדרו שלבים.")

    elif st.session_state['role'] == 'student':
        st.header(f"שלום {st.session_state['name']}")
        df_c = get_safe_data(URL_CONFIG)

        # בניית רשימת שלבים מהקובץ
        if not df_c.empty and len(df_c.columns) > 0:
            stages = df_c.iloc[:, 0].tolist()
            st.sidebar.subheader("📅 דד-ליינים:")
            st.sidebar.table(df_c)
        else:
            stages = ["בחירת נושא (ברירת מחדל)"]

        with st.form("f"):
            stage = st.selectbox("בחר שלב:", stages)
            p_name = st.text_input("שם פרויקט:")
            link = st.text_input("לינק לתוצר:")
            if st.form_submit_button("שלח הגשה"):
                if p_name and link:
                    data = {"id": st.session_state['id'], "name": st.session_state['name'],
                            "stage": stage, "project": p_name, "content": link}
                    requests.post(FORM_URL, data={ENTRY_IDS[k]: v for k, v in data.items()})
                    st.success("ההגשה נשלחה!")
                    st.balloons()
                else:
                    st.error("נא למלא את כל השדות")