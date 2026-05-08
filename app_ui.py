import streamlit as st
import pandas as pd
import requests
import time

# --- הגדרות לינקים (כפי שהיו) ---
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
        sid = st.text_input("תעודת זהות:").strip()
        if st.button("כניסה"):
            df_s = get_safe_data(URL_STUDENTS)
            if not df_s.empty:
                df_s.iloc[:, 0] = df_s.iloc[:, 0].astype(str).str.strip()
                if sid in df_s.iloc[:, 0].values:
                    sname = df_s[df_s.iloc[:, 0] == sid].iloc[0, 1]
                    st.session_state.update({'logged_in': True, 'role': 'student', 'id': sid, 'name': sname})
                    st.rerun()
            st.error("תעודת זהות לא נמצאה.")
    with t2:
        pwd = st.text_input("סיסמה:", type="password")
        if st.button("כניסה כמורה"):
            if pwd == "123":
                st.session_state.update({'logged_in': True, 'role': 'teacher'})
                st.rerun()

# --- ממשק משתמש ---
else:
    st.sidebar.title(f"שלום {st.session_state.get('name', 'המורה')}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 ממשק ניהול מורה")
        st.link_button("📝 עריכת נתונים בגוגל", SHEET_EDIT_URL)
        t_subs, t_stud, t_conf = st.tabs(["📊 הגשות", "👥 תלמידים", "📅 לוח זמנים"])
        with t_subs:
            st.dataframe(get_safe_data(URL_SUBS))
        with t_stud:
            st.table(get_safe_data(URL_STUDENTS))
        with t_conf:
            st.table(get_safe_data(URL_CONFIG))

    elif st.session_state['role'] == 'student':
        st.header(f"שלום {st.session_state['name']}")

        # 1. טעינת נתונים
        df_conf = get_safe_data(URL_CONFIG)
        df_subs = get_safe_data(URL_SUBS)

        all_stages = df_conf.iloc[:, 0].tolist() if not df_conf.empty else ["שלב 1"]

        # 2. מציאת השלבים שהתלמיד כבר הגיש
        # אנחנו מניחים שהעמודה השנייה (אינדקס 1) בגיליון התגובות היא הת"ז
        # והעמודה הרביעית (אינדקס 3) היא השלב (תלוי במבנה הפורם שלך)
        submitted_stages = []
        if not df_subs.empty:
            # סינון הגשות של התלמיד הנוכחי
            my_subs = df_subs[df_subs.iloc[:, 1].astype(str).str.strip() == st.session_state['id']]
            submitted_stages = my_subs.iloc[:, 3].unique().tolist()  # עמודת השלב בפורם

        # 3. לוגיקת סטטוסים בצד
        st.sidebar.subheader("📍 מצב התקדמות:")
        allowed_stages = []
        found_next = False

        for s in all_stages:
            if s in submitted_stages:
                st.sidebar.write(f"✅ {s}")
                allowed_stages.append(s)  # תמיד אפשר להגיש שוב שלב שכבר עשית
            elif not found_next:
                st.sidebar.write(f"⏳ **{s} (לביצוע)**")
                allowed_stages.append(s)
                found_next = True  # השלב הראשון שלא הוגש הוא השלב הבא
            else:
                st.sidebar.write(f"🔒 {s}")

        # 4. טופס הגשה מוגבל
        with st.form("submission"):
            stage = st.selectbox("בחר שלב להגשה (רק שלבים פתוחים):", allowed_stages)
            p_name = st.text_input("שם פרויקט:")
            link = st.text_input("לינק לתוצר:")

            if st.form_submit_button("🚀 שלח הגשה"):
                if p_name and link:
                    data = {"id": st.session_state['id'], "name": st.session_state['name'],
                            "stage": stage, "project": p_name, "content": link}
                    requests.post(FORM_URL, data={ENTRY_IDS[k]: v for k, v in data.items()})
                    st.success(f"שלב {stage} הוגש בהצלחה!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("נא למלא את כל השדות.")