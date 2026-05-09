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

@st.cache_data(ttl=300)
def load_all_data():
    try:
        subs = conn.read(worksheet="Form Responses 1")
        studs = conn.read(worksheet="students")
        conf = conn.read(worksheet="config")
        return subs.fillna(""), studs.fillna(""), conf.fillna("")
    except Exception as e:
        st.warning("⚠️ גוגל זקוקה למנוחה קצרה (Quota)... הנתונים יתרעננו בעוד רגע.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# פונקציית עזר לניקוי ת"ז
def clean_val(v):
    s = str(v).strip()
    if s.endswith('.0'): s = s[:-2]
    return ''.join(filter(str.isdigit, s))

# --- ניהול התחברות ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

# --- דף כניסה ---
if not st.session_state['logged_in']:
    st.title("🎓 Project Master - מערכת ניהול פרויקטים")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])

    with t1:
        sid_input = st.text_input("הקלד תעודת זהות:").strip()
        if st.button("התחבר"):
            _, df_stud, _ = load_all_data()
            if not df_stud.empty:
                user_id_clean = clean_val(sid_input).lstrip('0')
                found_user = None
                for index, row in df_stud.iterrows():
                    db_id_clean = clean_val(row.iloc[0]).lstrip('0')
                    if user_id_clean == db_id_clean and user_id_clean != "":
                        found_user = row
                        break
                if found_user is not None:
                    st.session_state.update({'logged_in': True, 'role': 'student', 'id': sid_input, 'name': found_user.iloc[1]})
                    st.success(f"שלום {found_user.iloc[1]}!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"תעודת זהות '{sid_input}' לא נמצאה.")
            else:
                st.error("לא הצלחתי לקרוא נתונים מגיליון students.")

    with t2:
        pwd = st.text_input("סיסמת מורה:", type="password")
        if st.button("כניסה למערכת הניהול"):
            if pwd == "123":
                st.session_state.update({'logged_in': True, 'role': 'teacher'})
                st.rerun()

# --- ממשק לאחר התחברות ---
else:
    # טעינת נתונים ראשונית
    df_subs, df_stud, df_conf = load_all_data()

    # הגדרת tech_options כאן כדי שיהיה זמין לכולם
    if not df_conf.empty and len(df_conf.columns) >= 3:
        tech_options = [str(t).strip() for t in df_conf.iloc[:, 2].dropna().unique() if str(t).strip() != ""]
    else:
        tech_options = ["Python", "JS", "React", "HTML/CSS"]

    st.sidebar.title(f"שלום {st.session_state.get('name', 'המורה')}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

    # --- ממשק מורה ---
    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה וניהול כיתה")
        tab_map, tab_approve, tab_config, tab_students = st.tabs(["🗺️ מפת כיתה", "✅ אישור הגשות", "⚙️ הגדרות שלבים", "👥 ניהול תלמידים"])

        with tab_map:
            if not df_stud.empty and not df_conf.empty:
                stages = df_conf.iloc[:, 0].tolist()
                map_list = []
                for _, s_row in df_stud.iterrows():
                    row = {"תלמיד": s_row.iloc[1]}
                    for stage in stages:
                        s_id = clean_val(s_row.iloc[0]).lstrip('0')
                        sub = df_subs[(df_subs.iloc[:, 1].apply(lambda x: clean_val(x).lstrip('0')) == s_id) & (df_subs.iloc[:, 3] == stage)]
                        if not sub.empty:
                            status = sub.iloc[-1].get('סטטוס', 'הוגש')
                            row[stage] = "✅" if status == "מאושר" else ("❌" if status == "לתיקון" else "⏳")
                        else: row[stage] = "⚪"
                    map_list.append(row)
                st.table(pd.DataFrame(map_list))

        with tab_approve:
            pending = df_subs[df_subs.get('סטטוס', '') != 'מאושר']
            if pending.empty: st.success("אין הגשות חדשות.")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"הגשה של {row.iloc[2]} - {row.iloc[3]}"):
                        st.write(f"**תוכן:** {row.iloc[5]}")
                        c1, c2 = st.columns(2)
                        if c1.button("אשר ✅", key=f"ok_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "מאושר"
                            conn.update(worksheet="Form Responses 1", data=df_subs)
                            st.cache_data.clear()
                            st.success("אושר!")
                            st.rerun()
                        if c2.button("תיקון ❌", key=f"fix_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "לתיקון"
                            conn.update(worksheet="Form Responses 1", data=df_subs)
                            st.cache_data.clear()
                            st.warning("נשלח לתיקון")
                            st.rerun()

        with tab_config:
            edited_conf = st.data_editor(df_conf, num_rows="dynamic", key="conf_editor")
            if st.button("שמור הגדרות"):
                conn.update(worksheet="config", data=edited_conf)
                st.cache_data.clear()
                st.success("הגדרות נשמרו!")
                st.rerun()

        with tab_students:
            edited_studs = st.data_editor(df_stud, num_rows="dynamic", key="stud_editor")
            if st.button("עדכן רשימה"):
                conn.update(worksheet="students", data=edited_studs)
                st.cache_data.clear()
                st.success("רשימה עודכנה!")
                st.rerun()

    # --- ממשק תלמיד ---
    elif st.session_state['role'] == 'student':
        st.header(f"הגשת פרויקט - {st.session_state['name']}")
        all_stages = df_conf.iloc[:, 0].tolist() if not df_conf.empty else ["שלב 1"]
        my_id = clean_val(st.session_state['id']).lstrip