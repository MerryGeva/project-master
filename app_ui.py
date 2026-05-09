import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# --- הגדרות עיצוב RTL ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .stDataFrame, .stTable { direction: rtl; }
    div[data-testid="stSidebarNav"] { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור לגוגל שייטס ---
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=60)  # צמצום זמן הזיכרון לדקה אחת לעדכון מהיר יותר
def load_all_data():
    try:
        subs = conn.read(worksheet="Form Responses 1", ttl=0)
        studs = conn.read(worksheet="students", ttl=0)
        conf = conn.read(worksheet="config", ttl=0)
        return subs.fillna(""), studs.fillna(""), conf.fillna("")
    except Exception as e:
        st.warning("🔄 מתחבר לנתונים...")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def clean_val(v):
    s = str(v).strip()
    if s.endswith('.0'): s = s[:-2]
    return ''.join(filter(str.isdigit, s))


# --- ניהול התחברות ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])
    with t1:
        sid_input = st.text_input("הקלד תעודת זהות:").strip()
        if st.button("התחבר"):
            _, df_stud, _ = load_all_data()
            if not df_stud.empty:
                user_id_clean = clean_val(sid_input).lstrip('0')
                found_user = None
                for _, row in df_stud.iterrows():
                    if clean_val(row.iloc[0]).lstrip('0') == user_id_clean and user_id_clean != "":
                        found_user = row;
                        break
                if found_user is not None:
                    st.session_state.update(
                        {'logged_in': True, 'role': 'student', 'id': sid_input, 'name': found_user.iloc[1]})
                    st.rerun()
                else:
                    st.error("תעודת זהות לא נמצאה.")
    with t2:
        pwd = st.text_input("סיסמת מורה:", type="password")
        if st.button("כניסה"):
            if pwd == "123":
                st.session_state.update({'logged_in': True, 'role': 'teacher'})
                st.rerun()
else:
    df_subs, df_stud, df_conf = load_all_data()

    # חילוץ הגדרות מה-Config
    all_stages = df_conf.iloc[:, 0].dropna().tolist() if not df_conf.empty else ["שלב 1"]
    tech_options = []
    if not df_conf.empty and len(df_conf.columns) >= 3:
        tech_options = [str(t).strip() for t in df_conf.iloc[:, 2].dropna().unique() if str(t).strip() != ""]
    if not tech_options: tech_options = ["Python", "JS", "React", "HTML/CSS"]

    st.sidebar.title(f"שלום {st.session_state.get('name', 'המורה')}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 ניהול כיתה")
        tab_map, tab_approve, tab_config, tab_students = st.tabs(
            ["🗺️ מפת כיתה", "✅ אישור הגשות", "⚙️ הגדרות", "👥 תלמידים"])

        with tab_map:
            if not df_stud.empty and not df_conf.empty:
                map_list = []
                for _, s_row in df_stud.iterrows():
                    row = {"תלמיד": s_row.iloc[1]}
                    for stage in all_stages:
                        s_id = clean_val(s_row.iloc[0]).lstrip('0')
                        sub = df_subs[(df_subs.iloc[:, 1].apply(lambda x: clean_val(x).lstrip('0')) == s_id) & (
                                    df_subs.iloc[:, 3] == stage)]
                        status = sub.iloc[-1].get('סטטוס', 'הוגש') if not sub.empty else "⚪"
                        row[stage] = "✅" if status == "מאושר" else (
                            "❌" if status == "לתיקון" else ("⏳" if status == "הוגש" else "⚪"))
                    map_list.append(row)
                st.table(pd.DataFrame(map_list))

        with tab_approve:
            pending = df_subs[df_subs['סטטוס'].isin(['הוגש', 'לתיקון'])]
            if pending.empty:
                st.success("אין הגשות חדשות.")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"הגשה: {row['שם התלמיד']} - {row['שלב']}"):
                        st.write(f"**פרויקט:** {row['שם הפרויקט']}")
                        st.info(f"**פרטי הגשה:**\n{row['תוכן']}")
                        c1, c2 = st.columns(2)
                        if c1.button("אשר ✅", key=f"ok_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "מאושר"
                            conn.update(worksheet="Form Responses 1", data=df_subs)
                            st.cache_data.clear()
                            st.rerun()
                        if c2.button("לתיקון ❌", key=f"fix_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "לתיקון"
                            conn.update(worksheet="Form Responses 1", data=df_subs)
                            st.cache_data.clear()
                            st.rerun()

        with tab_config:
            # הוספת num_rows="dynamic" מאפשרת להוסיף כמה שלבים שרוצים
            edited_conf = st.data_editor(df_conf, num_rows="dynamic", key="conf_edit")
            if st.button("שמור הגדרות מערכת"):
                conn.update(worksheet="config", data=edited_conf)
                st.cache_data.clear()
                st.success("הגדרות עודכנו!")
                st.rerun()

        with tab_students:
            edited_studs = st.data_editor(df_stud, num_rows="dynamic", key="stud_edit")
            if st.button("עדכן תלמידים"):
                conn.update(worksheet="students", data=edited_studs)
                st.cache_data.clear()
                st.success("רשימה עודכנה!")
                st.rerun()

    elif st.session_state['role'] == 'student':
        st.header(f"שלום, {st.session_state['name']}")
        my_id = clean_val(st.session_state['id']).lstrip('0')
        my_subs = df_subs[df_subs.iloc[:, 1].apply(lambda x: clean_val(x).lstrip('0')) == my_id]

        # חישוב שלב נוכחי
        allowed_stages = []
        found_next = False
        for s in all_stages:
            sub = my_subs[my_subs.iloc[:, 3] == s]
            stat = sub.iloc[-1].get('סטטוס', '') if not sub.empty else ""
            if stat == "מאושר":
                allowed_stages.append(s)
            elif not found_next:
                allowed_stages.append(s); found_next = True

        with st.form("submit_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                stage = st.selectbox("שלב:", allowed_stages)
                techs = st.multiselect("טכנולוגיות:", tech_options)
            with c2:
                p_name = st.text_input("שם הפרויקט:")
                link = st.text_input("לינק (אם יש):")
            desc = st.text_area("תיאור הביצוע:")
            if st.form_submit_button("🚀 שלח הגשה"):
                if p_name and desc:
                    new_data = pd.DataFrame([{"Timestamp": time.strftime("%d/%m/%Y %H:%M:%S"),
                                              "תעודת זהות": st.session_state['id'],
                                              "שם התלמיד": st.session_state['name'], "שלב": stage, "שם הפרויקט": p_name,
                                              "תוכן": f"טכנולוגיות: {', '.join(techs)}\nתיאור: {desc}\nלינק: {link}",
                                              "סטטוס": "הוגש"}])
                    conn.update(worksheet="Form Responses 1", data=pd.concat([df_subs, new_data], ignore_index=True))
                    st.balloons()
                    st.success("נשלח!")
                    st.cache_data.clear()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.warning("מלא שדות חובה.")