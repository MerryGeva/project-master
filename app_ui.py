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
    .link-box { 
        background-color: #e1f5fe; padding: 15px; border-radius: 5px; 
        border-right: 5px solid #03a9f4; margin: 10px 0;
    }
    .fix-notice {
        background-color: #ffebee; padding: 15px; border-radius: 10px; 
        border: 1px solid #ffb74d; margin-bottom: 20px;
    }
    .pending-notice {
        background-color: #e3f2fd; padding: 15px; border-radius: 10px; 
        border: 1px solid #2196f3; margin-bottom: 20px;
    }
    div[data-testid="stDataFrame"] { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר וחיבור נתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)


def clean_id(v):
    """מנקה תעודת זהות לרצף ספרות בלבד ללא אפסים מובילים"""
    s = ''.join(filter(str.isdigit, str(v)))
    return s.lstrip('0')


@st.cache_data(ttl=5)
def load_all_data():
    """טעינת נתונים עם מנגנון Retry למניעת קריסות עומס"""
    for attempt in range(3):
        try:
            subs = conn.read(worksheet="Form Responses 1", ttl=0).fillna("")
            studs = conn.read(worksheet="students", ttl=0).fillna("")
            conf = conn.read(worksheet="config", ttl=0).fillna("")

            # ניקוי כותרות
            subs.columns = [str(c).strip() for c in subs.columns]
            studs.columns = [str(c).strip() for c in studs.columns]
            conf.columns = [str(c).strip() for c in conf.columns]

            # וידוא עמודות בסיסיות בטבלת הגשות
            critical = ["Timestamp", "תעודת זהות", "שם התלמיד", "שלב", "שם הפרויקט", "תוכן", "קישור", "סטטוס"]
            for col in critical:
                if col not in subs.columns: subs[col] = ""

            return subs, studs, conf, True
        except Exception:
            time.sleep(2)
            continue
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False


# טעינה ראשונית
df_subs, df_stud, df_conf, success = load_all_data()

if not success:
    st.error("⚠️ יש כרגע עומס בתקשורת עם גוגל. אנא המתינו 10 שניות ורעננו את הדף.")
    st.stop()

# --- 3. הגדרות מערכת מה-Config ---
if not df_conf.empty and "שלב" in df_conf.columns:
    all_stages = df_conf["שלב"].dropna().astype(str).tolist()
    deadlines = df_conf["דד-ליין"].astype(str).tolist() if "דד-ליין" in df_conf.columns else []
    tech_options = df_conf["טכנולוגיות"].dropna().unique().tolist() if "טכנולוגיות" in df_conf.columns else ["Python"]
else:
    all_stages, deadlines, tech_options = ["שלב 1"], [], ["Python"]

# --- 4. ניהול כניסה למערכת ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])
    with t1:
        sid_input = st.text_input("תעודת זהות:").strip()
        if st.button("התחבר כתלמיד"):
            user_id_clean = clean_id(sid_input)
            found_user = None
            for _, row in df_stud.iterrows():
                if clean_id(row.iloc[0]) == user_id_clean:
                    found_user = row
                    break
            if found_user is not None:
                st.session_state.update(
                    {'logged_in': True, 'role': 'student', 'id': sid_input, 'name': found_user.iloc[1]})
                st.rerun()
            else:
                st.error("תעודת זהות לא נמצאה ברשימת התלמידים.")
    with t2:
        pwd = st.text_input("סיסמת מורה:", type="password")
        if st.button("כניסת צוות"):
            if pwd == "123":
                st.session_state.update({'logged_in': True, 'role': 'teacher', 'name': 'המורה'})
                st.rerun()

# --- 5. ממשק לאחר התחברות ---
else:
    with st.sidebar:
        st.title(f"שלום, {st.session_state['name']}")
        if st.button("🚪 התנתק"):
            st.session_state.clear()
            st.rerun()

        if st.session_state['role'] == 'student':
            st.markdown("---")
            st.subheader("📍 מצב התקדמות")
            my_id_c = clean_id(st.session_state['id'])
            my_subs = df_subs[df_subs['תעודת זהות'].apply(clean_id) == my_id_c]
            today = datetime.now()
            for i, stage in enumerate(all_stages):
                s_sub = my_subs[my_subs['שלב'] == stage]
                stat = s_sub.iloc[-1]['סטטוס'] if not s_sub.empty else ""
                dl = deadlines[i] if i < len(deadlines) else ""
                icon = "✅" if stat == "מאושר" else ("❌" if stat == "לתיקון" else ("⏳" if stat == "הוגש" else "⚪"))
                st.write(f"{icon} {stage} {'(' + dl + ')' if dl else ''}")

    # --- ממשק מורה ---
    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה למורה")
        t_map, t_approve, t_config, t_studs = st.tabs(["🗺️ מפת כיתה", "✅ אישור הגשות", "⚙️ הגדרות", "👥 תלמידים"])

        with t_approve:
            st.subheader("📥 הגשות חדשות לבדיקה")
            pending = df_subs[df_subs['סטטוס'] == 'הוגש']
            if pending.empty:
                st.info("אין הגשות חדשות כרגע.")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"🆕 {row['שם התלמיד']} - {row['שלב']}"):
                        st.write(f"**פרויקט:** {row['שם הפרויקט']}")
                        st.write(f"**תיאור:** {row['תוכן']}")
                        if str(row['קישור']).strip():
                            st.markdown(
                                f"<div class='link-box'>🔗 <a href='{row['קישור']}' target='_blank'>לחץ לצפייה בתוצר</a></div>",
                                unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        if c1.button("אשר ✅", key=f"ok_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "מאושר"
                            conn.update(worksheet="Form Responses 1", data=df_subs)
                            st.cache_data.clear();
                            st.rerun()
                        if c2.button("לתיקון ❌", key=f"fix_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "לתיקון"
                            conn.update(worksheet="Form Responses 1", data=df_subs)
                            st.cache_data.clear();
                            st.rerun()
            st.markdown("---")
            st.subheader("📜 היסטוריית כל ההגשות")
            st.dataframe(df_subs.iloc[::-1], use_container_width=True, hide_index=True)

        with t_map:
            st.subheader("🗺️ מפת התקדמות כיתתית")
            if not df_stud.empty:
                map_data = []
                for _, s_row in df_stud.iterrows():
                    s_id_c = clean_id(s_row.iloc[0])
                    row_map = {"תלמיד": s_row.iloc[1]}
                    for stage in all_stages:
                        s_stage_subs = df_subs[
                            (df_subs['תעודת זהות'].apply(clean_id) == s_id_c) & (df_subs['שלב'] == stage)]
                        if not s_stage_subs.empty:
                            last_s = s_stage_subs.iloc[-1]['סטטוס']
                            row_map[stage] = "✅" if last_s == "מאושר" else ("⏳" if last_s == "הוגש" else "❌")
                        else:
                            row_map[stage] = "⚪"
                    map_data.append(row_map)
                st.dataframe(pd.DataFrame(map_data), use_container_width=True, hide_index=True)

        with t_studs:
            st.subheader("👥 ניהול תלמידים")
            e_studs = st.data_editor(df_stud, num_rows="dynamic", key="editor_studs")
            if st.button("שמור תלמידים"):
                conn.update(worksheet="students", data=e_studs);
                st.cache_data.clear();
                st.rerun()

        with t_config:
            st.subheader("⚙️ הגדרות שלבים וטכנולוגיות")
            e_conf = st.data_editor(df_conf, num_rows="dynamic", key="editor_conf")
            if st.button("שמור הגדרות"):
                conn.update(worksheet="config", data=e_conf);
                st.cache_data.clear();
                st.rerun()

    # --- ממשק תלמיד ---
    elif st.session_state['role'] == 'student':
        my_id_c = clean_id(st.session_state['id'])
        my_subs = df_subs[df_subs['תעודת זהות'].apply(clean_id) == my_id_c]

        # זיהוי שלב נוכחי
        current_stage, current_status = all_stages[0], ""
        for s in all_stages:
            s_sub = my_subs[my_subs['שלב'] == s]
            stat = s_sub.iloc[-1]['סטטוס'] if not s_sub.empty else ""
            if stat == "לתיקון":
                current_stage, current_status = s, stat; break
            elif stat != "מאושר":
                current_stage, current_status = s, stat; break

        st.header(f"שלום {st.session_state['name']}")

        if current_status == "הוגש":
            st.markdown(f"<div class='pending-notice'>⏳ שלב <b>{current_stage}</b> נשלח וממתין לבדיקה.</div>",
                        unsafe_allow_html=True)
        else:
            if current_status == "לתיקון":
                st.markdown(f"<div class='fix-notice'>⚠️ המורה ביקש/ה תיקונים לשלב <b>{current_stage}</b>.</div>",
                            unsafe_allow_html=True)

            last_sub = my_subs.iloc[-1] if not my_subs.empty else None
            last_p_name = last_sub['שם הפרויקט'] if last_sub is not None else ""

            with st.form("student_submission"):
                st.subheader(f"הגשה לשלב: {current_stage}")
                p_name = st.text_input("שם הפרויקט:", value=last_p_name) if current_stage == all_stages[
                    0] else last_p_name
                if current_stage != all_stages[0]: st.info(f"פרויקט: {last_p_name}")

                link = st.text_input("קישור לתוצר (GitHub/Drive/Figma):")
                techs = st.multiselect("טכנולוגיות בשימוש:", tech_options)
                desc = st.text_area("תיאור הביצוע לשלב זה:")

                if st.form_submit_button("🚀 שלח הגשה"):
                    if not p_name or not desc:
                        st.error("יש למלא שם פרויקט ותיאור.")
                    elif current_stage != all_stages[0] and not link:
                        st.error("חובה לצרף קישור משלב 2 והלאה.")
                    else:
                        new_data = {
                            "Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "תעודת זהות": st.session_state['id'],
                            "שם התלמיד": st.session_state['name'],
                            "שלב": current_stage,
                            "שם הפרויקט": p_name,
                            "תוכן": f"טכנולוגיות: {', '.join(techs)}\n{desc}",
                            "קישור": link,
                            "סטטוס": "הוגש"
                        }
                        conn.update(worksheet="Form Responses 1",
                                    data=pd.concat([df_subs, pd.DataFrame([new_data])], ignore_index=True))
                        st.balloons();
                        st.cache_data.clear();
                        time.sleep(1);
                        st.rerun()