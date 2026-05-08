import streamlit as st
import pandas as pd
import requests
import time

# --- הגדרות לינקים (ודאי שה-SHEET_EDIT_URL הוא הלינק מהדפדפן שלך) ---
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSf3vGFIikpAHVhZuSTPO04GdsP7BwxejG8lo-Voo0sKIXBdoA/formResponse"
URL_SUBS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=1111779993&single=true&output=csv"
URL_STUDENTS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=1500993496&single=true&output=csv"
URL_CONFIG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLSrqx9zZyH8Olu8g_RJOkFjgrvnLgVAL6N2tmTjsPlzF_off6SmoOgDaUFFqBMtwkdcwubqcP7xEy/pub?gid=939170192&single=true&output=csv"

# הלינק לעריכה בדרייב (זה שמופיע לך למעלה בדפדפן כשאת בתוך השייטס)
SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1cNixCctWeF2k_HkJ7OECzVp8M0djZ3upfYKStMmp36c/edit"

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
        return pd.read_csv(f"{url}&cachebuster={t}", dtype=str).fillna("")
    except:
        return pd.DataFrame()


st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .stDataFrame, .stTable { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

# --- כניסה ---
if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])
    with t1:
        sid = st.text_input("תעודת זהות:").strip()
        if st.button("כניסה"):
            df_s = get_safe_data(URL_STUDENTS)
            if not df_s.empty and sid in df_s.iloc[:, 0].astype(str).str.strip().values:
                sname = df_s[df_s.iloc[:, 0].astype(str).str.strip() == sid].iloc[0, 1]
                st.session_state.update({'logged_in': True, 'role': 'student', 'id': sid, 'name': sname})
                st.rerun()
            st.error("תעודת זהות לא נמצאה.")
    with t2:
        pwd = st.text_input("סיסמה:", type="password")
        if st.button("כניסה כמורה"):
            if pwd == "123":
                st.session_state.update({'logged_in': True, 'role': 'teacher'})
                st.rerun()
else:
    # --- תפריט צד ---
    st.sidebar.title(f"שלום {st.session_state.get('name', 'המורה')}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

    # --- ממשק מורה ---
    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה למורה")
        st.link_button("📂 פתח גיליון Google Sheets לאישור ועריכה", SHEET_EDIT_URL)

        m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["🗺️ מפת כיתה", "⚙️ הגדרת שלבים", "📊 רשימת הגשות", "👥 רשימת תלמידים"])

        df_subs = get_safe_data(URL_SUBS)
        df_stud = get_safe_data(URL_STUDENTS)
        df_conf = get_safe_data(URL_CONFIG)

        with m_tab1:
            if not df_stud.empty and not df_conf.empty:
                stages = df_conf.iloc[:, 0].tolist()
                map_data = []
                for _, s_row in df_stud.iterrows():
                    row = {"שם התלמיד": s_row.iloc[1]}
                    for stage in stages:
                        sub = df_subs[(df_subs.iloc[:, 1] == str(s_row.iloc[0])) & (df_subs.iloc[:, 3] == stage)]
                        if not sub.empty:
                            status = sub.iloc[-1, -1] if len(sub.columns) > 5 else "הוגש"
                            if status == "מאושר":
                                row[stage] = "✅"
                            elif status == "לתיקון":
                                row[stage] = "❌"
                            else:
                                row[stage] = "⏳"
                        else:
                            row[stage] = "⚪"
                    map_data.append(row)
                st.subheader("מפת התקדמות כיתתית")
                st.table(pd.DataFrame(map_data))

        with m_tab2:
            st.subheader("הגדרת שלבים ודד-ליינים")
            st.table(df_conf)

        with m_tab3:
            st.subheader("כל ההגשות מהפורם")
            st.dataframe(df_subs)

        with m_tab4:
            st.subheader("רשימת תלמידים מאושרים")
            st.table(df_stud)

    # --- ממשק תלמיד ---
    elif st.session_state['role'] == 'student':
        st.header(f"הגשת פרויקט - {st.session_state['name']}")

        df_conf = get_safe_data(URL_CONFIG)
        df_subs = get_safe_data(URL_SUBS)

        all_stages = df_conf.iloc[:, 0].tolist() if not df_conf.empty else ["נושא"]

        # לוגיקת סטטוסים
        submitted_dict = {}
        if not df_subs.empty:
            my_subs = df_subs[df_subs.iloc[:, 1].astype(str).str.strip() == st.session_state['id']]
            for _, r in my_subs.iterrows():
                s_val = r.iloc[-1] if len(my_subs.columns) > 5 else "הוגש"
                submitted_dict[r.iloc[3]] = s_val

        allowed_stages = []
        found_next = False
        st.sidebar.subheader("📍 התקדמות:")
        for s in all_stages:
            status = submitted_dict.get(s, "לא הוגש")
            if status == "מאושר":
                st.sidebar.write(f"✅ {s}")
                allowed_stages.append(s)
            elif not found_next:
                st.sidebar.write(f"⏳ **{s}**")
                allowed_stages.append(s)
                found_next = True
            else:
                st.sidebar.write(f"🔒 {s}")

        # טופס הגשה עם שדות תוכן
        with st.form("main_form"):
            col1, col2 = st.columns(2)
            with col1:
                stage = st.selectbox("בחר שלב להגשה:", allowed_stages)
                tech = st.selectbox("טכנולוגיה מרכזית:", ["Python", "JavaScript", "React", "HTML/CSS", "C#", "אחר"])
            with col2:
                p_name = st.text_input("שם הפרויקט:")
                link = st.text_input("קישור לתוצר (GitHub/Drive):")

            project_desc = st.text_area("תיאור תוכן השלב / הסבר על הפרויקט:", height=150)

            if st.form_submit_button("🚀 שלח הגשה למורה"):
                if p_name and project_desc:
                    full_content = f"Tech: {tech} | Desc: {project_desc} | Link: {link}"
                    data = {"id": st.session_state['id'], "name": st.session_state['name'],
                            "stage": stage, "project": p_name, "content": full_content}
                    requests.post(FORM_URL, data={ENTRY_IDS[k]: v for k, v in data.items()})
                    st.success("נשלח! המורה יראה את ההגשה במפת הכיתה.")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("חובה למלא שם פרויקט ותיאור.")