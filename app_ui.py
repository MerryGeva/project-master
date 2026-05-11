import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime

# --- 1. הגדרות RTL ועיצוב ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .status-red { color: #ff4b4b; font-weight: bold; }
    div[data-testid="stDataFrame"] { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר וחיבור נתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)


def normalize_id(v):
    if pd.isna(v) or v == "": return ""
    s = str(v).split('.')[0]
    s = ''.join(filter(str.isdigit, s))
    return s.zfill(9) if s else ""


@st.cache_data(ttl=5)
def load_all_data():
    try:
        subs = conn.read(worksheet="Form Responses 1", ttl=0).fillna("")
        studs = conn.read(worksheet="students", ttl=0).fillna("")
        conf = conn.read(worksheet="config", ttl=0).fillna("")
        for df in [subs, studs, conf]:
            df.columns = [str(c).strip() for c in df.columns]
        return subs, studs, conf, True
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False


df_subs, df_stud, df_conf, success = load_all_data()

if not success and df_subs.empty:
    st.warning("⚠️ המערכת בטעינה...")
    st.stop()

# שליפת הגדרות מעודכנות
all_stages = df_conf["שלב"].dropna().astype(str).str.strip().tolist() if not df_conf.empty else ["שלב 1"]
tech_options = df_conf["טכנולוגיות"].dropna().unique().tolist() if not df_conf.empty else ["Python"]

# --- 3. ניהול כניסה ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None, 'class': None})

if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])
    with t1:
        sid_input = st.text_input("תעודת זהות:").strip()
        if st.button("התחבר"):
            u_norm = normalize_id(sid_input)
            found_user = None
            for _, row in df_stud.iterrows():
                if normalize_id(row.iloc[0]) == u_norm and u_norm != "":
                    found_user = row;
                    break
            if found_user is not None:
                st.session_state.update({
                    'logged_in': True, 'role': 'student', 'id': u_norm,
                    'name': str(found_user.iloc[1]),
                    'class': str(found_user.iloc[2]) if len(found_user) > 2 else "כללי"
                })
                st.rerun()
            else:
                st.error("תעודת זהות לא נמצאה.")
    with t2:
        pwd = st.text_input("סיסמת מורה:", type="password")
        if st.button("כניסה"):
            if pwd == "123":
                st.session_state.update({'logged_in': True, 'role': 'teacher', 'name': 'המורה'})
                st.rerun()

# --- 4. ממשק מחובר ---
else:
    with st.sidebar:
        st.title(f"שלום, {st.session_state['name']}")
        if st.button("🚪 התנתק"):
            st.session_state.clear();
            st.rerun()

        if st.session_state['role'] == 'student':
            st.markdown("---")
            st.subheader("📍 מצב שלבים")
            my_id = normalize_id(st.session_state['id'])
            my_s = df_subs[df_subs['תעודת זהות'].apply(normalize_id) == my_id]
            for s in all_stages:
                sub_at_stage = my_s[my_s['שלב'].str.strip() == s]
                stat = sub_at_stage.iloc[-1]['סטטוס'].strip() if not sub_at_stage.empty else ""
                icon = "✅" if stat == "מאושר" else ("❌" if stat == "לתיקון" else ("⏳" if stat == "הוגש" else "⚪"))
                st.write(f"{icon} {s}")

    if st.session_state['role'] == 'teacher':
        # (ממשק מורה - נשאר זהה לקוד הקודם עם ה-Upload)
        st.header("👨‍🏫 לוח בקרה למורה")
        t_map, t_approve, t_config, t_studs = st.tabs(["🗺️ מפת כיתה", "✅ אישור הגשות", "⚙️ הגדרות", "👥 תלמידים"])

        with t_approve:
            pending = df_subs[df_subs['סטטוס'].str.strip() == 'הוגש']
            if pending.empty:
                st.info("אין הגשות חדשות.")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"🆕 {row['שם התלמיד']} - {row['שלב']}"):
                        st.write(f"**פרויקט:** {row['שם הפרויקט']}\n\n**תיאור:** {row['תוכן']}")
                        c1, c2 = st.columns(2)
                        if c1.button("אשר ✅", key=f"ok_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "מאושר";
                            conn.update(worksheet="Form Responses 1", data=df_subs);
                            st.cache_data.clear();
                            st.rerun()
                        if c2.button("לתיקון ❌", key=f"fix_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "לתיקון";
                            conn.update(worksheet="Form Responses 1", data=df_subs);
                            st.cache_data.clear();
                            st.rerun()

        with t_map:
            if not df_stud.empty:
                classes = ["הכל"] + sorted(df_stud.iloc[:, 2].unique().astype(str).tolist()) if df_stud.shape[
                                                                                                    1] > 2 else ["הכל"]
                sel_class = st.selectbox("סנן מפה לפי כיתה:", classes)
                filtered_studs = df_stud if sel_class == "הכל" else df_stud[df_stud.iloc[:, 2].astype(str) == sel_class]
                map_d = []
                for _, s_row in filtered_studs.iterrows():
                    sid = normalize_id(s_row.iloc[0])
                    row_m = {"תלמיד": s_row.iloc[1], "כיתה": s_row.iloc[2] if len(s_row) > 2 else "כללי"}
                    for s in all_stages:
                        st_subs = df_subs[
                            (df_subs['תעודת זהות'].apply(normalize_id) == sid) & (df_subs['שלב'].str.strip() == s)]
                        last_s = st_subs.iloc[-1]['סטטוס'].strip() if not st_subs.empty else "⚪"
                        row_m[s] = "✅" if last_s == "מאושר" else (
                            "⏳" if last_s == "הוגש" else ("❌" if last_s == "לתיקון" else "⚪"))
                    map_d.append(row_m)
                st.dataframe(pd.DataFrame(map_d), use_container_width=True, hide_index=True)

        with t_studs:
            uploaded_file = st.file_uploader("טעינת רשימת תלמידים (תעודת זהות, שם התלמיד, כיתה)", type=["xlsx", "csv"])
            if uploaded_file:
                new_studs = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(
                    uploaded_file)
                if st.button("🚀 עדכן רשימה"):
                    conn.update(worksheet="students", data=new_studs);
                    st.cache_data.clear();
                    st.rerun()
            e_s = st.data_editor(df_stud, num_rows="dynamic", key="ed_s")
            if st.button("💾 שמור שינויים"):
                conn.update(worksheet="students", data=e_s);
                st.cache_data.clear();
                st.rerun()

        with t_config:
            e_c = st.data_editor(df_conf, num_rows="dynamic", key="ed_c")
            if st.button("💾 שמור הגדרות"):
                conn.update(worksheet="config", data=e_c);
                st.cache_data.clear();
                st.rerun()

    else:  # ממשק תלמיד - לוגיקה משופרת למציאת שלב
        my_id = normalize_id(st.session_state['id'])
        my_subs = df_subs[df_subs['תעודת זהות'].apply(normalize_id) == my_id]

        curr_stage = None
        curr_stat = ""

        # חיפוש השלב הראשון שאינו מאושר מתוך רשימת השלבים המוגדרת ב-config
        for s in all_stages:
            sub_at_stage = my_subs[my_subs['שלב'].str.strip() == s]
            if sub_at_stage.empty:
                curr_stage = s
                curr_stat = ""
                break
            else:
                last_stat = sub_at_stage.iloc[-1]['סטטוס'].strip()
                if last_stat != "מאושר":
                    curr_stage = s
                    curr_stat = last_stat
                    break

        st.header(f"שלום {st.session_state['name']}")

        if curr_stage is None:
            st.success("🎉 כל הכבוד! סיימת את כל שלבי הפרויקט!")
            st.balloons()
        elif curr_stat == "הוגש":
            st.info(f"הגשה לשלב **{curr_stage}** ממתינה לבדיקת המורה.")
        else:
            if curr_stat == "לתיקון": st.warning(f"⚠️ נדרש תיקון לשלב: {curr_stage}")

            last_p = my_subs.iloc[-1]['שם הפרויקט'] if not my_subs.empty else ""
            with st.form("sub_f"):
                st.subheader(f"הגשה לשלב: {curr_stage}")
                p_n = st.text_input("שם פרויקט:", value=last_p) if curr_stage == all_stages[0] else last_p
                link, techs, desc = st.text_input("קישור לתוצר:"), st.multiselect("טכנולוגיות:",
                                                                                  tech_options), st.text_area("תיאור:")
                if st.form_submit_button("🚀 שלח"):
                    if not p_n or not desc:
                        st.error("חובה למלא שם ותיאור.")
                    else:
                        new_r = {"Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                 "תעודת זהות": st.session_state['id'], "שם התלמיד": st.session_state['name'],
                                 "שלב": curr_stage, "שם הפרויקט": p_n,
                                 "תוכן": f"טכנולוגיות: {', '.join(techs)}\n{desc}", "קישור": link, "סטטוס": "הוגש"}
                        conn.update(worksheet="Form Responses 1",
                                    data=pd.concat([df_subs, pd.DataFrame([new_r])], ignore_index=True))
                        st.cache_data.clear();
                        time.sleep(1);
                        st.rerun()