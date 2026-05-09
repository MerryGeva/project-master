import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime

# --- הגדרות עיצוב RTL ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .status-red { color: #ff4b4b; font-weight: bold; }
    .fix-notice {
        background-color: #ffebee; padding: 15px;
        border-radius: 10px; border: 1px solid #ffb74d; margin-bottom: 20px;
    }
    .pending-notice {
        background-color: #e3f2fd; padding: 15px;
        border-radius: 10px; border: 1px solid #2196f3; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור וטעינה ---
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=5)  # רענון מהיר מאוד
def load_all_data():
    try:
        subs = conn.read(worksheet="Form Responses 1", ttl=0)
        studs = conn.read(worksheet="students", ttl=0)
        conf = conn.read(worksheet="config", ttl=0)
        return subs.fillna(""), studs.fillna(""), conf.fillna("")
    except:
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
        sid_input = st.text_input("תעודת זהות:").strip()
        if st.button("התחבר"):
            _, df_stud, _ = load_all_data()
            user_id_clean = clean_val(sid_input).lstrip('0')
            found_user = next(
                (row for _, row in df_stud.iterrows() if clean_val(row.iloc[0]).lstrip('0') == user_id_clean), None)
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
                st.session_state.update({'logged_in': True, 'role': 'teacher', 'name': 'המורה'})
                st.rerun()
else:
    df_subs, df_stud, df_conf = load_all_data()
    all_stages = df_conf.iloc[:, 0].dropna().tolist() if not df_conf.empty else ["שלב 1"]
    deadlines = df_conf.iloc[:, 1].tolist() if not df_conf.empty and len(df_conf.columns) > 1 else []
    tech_options = [str(t).strip() for t in df_conf.iloc[:, 2].dropna().unique()] if not df_conf.empty and len(
        df_conf.columns) >= 3 else ["Python", "JS"]

    display_name = st.session_state.get('name', 'המורה')
    st.sidebar.title(f"שלום {display_name}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear();
        st.rerun()

    # --- ממשק מורה --- (נשאר אותו דבר, כולל התיקונים הקודמים)
    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 ניהול כיתה")
        # ... (כאן מגיע הקוד של טאב אישור הגשות והיסטוריה שכבר עשינו)
        # נדלג לצורך הקיצור לממשק התלמיד שבו חלו השינויים הקריטיים:

        # --- (קוד המורה להלן לצורך שלמות המערכת) ---
        tab_map, tab_approve, tab_config, tab_students = st.tabs(
            ["🗺️ מפת כיתה", "✅ אישור הגשות", "⚙️ הגדרות", "👥 תלמידים"])
        with tab_approve:
            pending = df_subs[df_subs['סטטוס'] == 'הוגש']
            if pending.empty:
                st.info("אין הגשות חדשות.")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"🆕 {row['שם התלמיד']} - {row['שלב']}"):
                        st.write(f"**פרויקט:** {row['שם הפרויקט']}")
                        st.markdown(row['תוכן'])
                        c1, c2 = st.columns(2)
                        if c1.button("אשר ✅", key=f"ok_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "מאושר";
                            conn.update(worksheet="Form Responses 1", data=df_subs)
                            st.cache_data.clear();
                            st.rerun()
                        if c2.button("לתיקון ❌", key=f"fix_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "לתיקון";
                            conn.update(worksheet="Form Responses 1", data=df_subs)
                            st.cache_data.clear();
                            st.rerun()
        with tab_config:
            edited_conf = st.data_editor(df_conf, num_rows="dynamic", key="conf_edit")
            if st.button("שמור הגדרות"):
                conn.update(worksheet="config", data=edited_conf);
                st.cache_data.clear();
                st.rerun()
        with tab_students:
            edited_studs = st.data_editor(df_stud, num_rows="dynamic", key="stud_edit")
            if st.button("עדכן תלמידים"):
                conn.update(worksheet="students", data=edited_studs.astype(str));
                st.cache_data.clear();
                st.rerun()

    # --- ממשק תלמיד (מתוקן) ---
    elif st.session_state['role'] == 'student':
        my_id = clean_val(st.session_state['id']).lstrip('0')
        my_subs = df_subs[df_subs.iloc[:, 1].apply(lambda x: clean_val(x).lstrip('0')) == my_id]

        # חישוב שלב נוכחי וסטטוס
        current_stage = all_stages[0]
        current_status = ""
        for s in all_stages:
            sub = my_subs[my_subs['שלב'] == s]
            stat = sub.iloc[-1]['סטטוס'] if not sub.empty else ""
            if stat == "לתיקון":
                current_stage = s;
                current_status = "לתיקון";
                break
            elif stat != "מאושר":
                current_stage = s;
                current_status = stat;
                break

        # הצגת תאריכים בסיידבר עם צבע אדום
        st.sidebar.subheader("📍 מצב התקדמות:")
        today = datetime.now()
        for i, s in enumerate(all_stages):
            sub = my_subs[my_subs['שלב'] == s]
            stat = sub.iloc[-1]['סטטוס'] if not sub.empty else ""
            dl_str = deadlines[i] if i < len(deadlines) else ""

            # בדיקת איחור
            overdue = False
            if dl_str and stat != "מאושר":
                try:
                    dl_dt = pd.to_datetime(dl_str, dayfirst=True)
                    if dl_dt < today: overdue = True
                except:
                    pass

            dl_text = f" ({dl_str})" if dl_str else ""
            if stat == "מאושר":
                icon = "✅"
            elif stat == "לתיקון":
                icon = "❌"
            elif stat == "הוגש":
                icon = "⏳"
            else:
                icon = "⚪"

            if overdue:
                st.sidebar.markdown(f"{icon} <span class='status-red'>{s}{dl_text}</span>", unsafe_allow_html=True)
            else:
                st.sidebar.write(f"{icon} {s}{dl_text}")

        st.header(f"שלב נוכחי: {current_stage}")

        # מניעת הגשה כפולה:
        if current_status == "הוגש":
            st.markdown(
                f"""<div class='pending-notice'>⏳ <b>ההגשה שלך לשלב {current_stage} בבדיקה.</b><br>המורה יעדכן את הסטטוס בקרוב. לא ניתן להגיש שוב כרגע.</div>""",
                unsafe_allow_html=True)
        else:
            if current_status == "לתיקון":
                st.markdown(
                    f"""<div class='fix-notice'>⚠️ <b>נדרש תיקון בשלב {current_stage}.</b> נא לעדכן את הפרטים ולהגיש שוב.</div>""",
                    unsafe_allow_html=True)

            last_p_name = my_subs.iloc[-1]['שם הפרויקט'] if not my_subs.empty else ""

            with st.form("submit_form"):
                c1, c2 = st.columns(2)
                with c1:
                    st.info(f"מגיש שלב: {current_stage}")
                    techs = st.multiselect("טכנולוגיות:", tech_options)
                with c2:
                    if current_stage == all_stages[0]:
                        p_name = st.text_input("שם הפרויקט:", value=last_p_name)
                    else:
                        st.write(f"**שם הפרויקט:** {last_p_name}")
                        p_name = last_p_name
                    link = st.text_input("קישור לתוצר:")

                desc = st.text_area("תיאור הביצוע:")

                if st.form_submit_button("🚀 שלח הגשה"):
                    if not p_name or not desc:
                        st.warning("מלא שדות חובה.")
                    elif current_stage != all_stages[0] and not link:
                        st.error("חובה לצרף קישור.")
                    else:
                        new_data = pd.DataFrame([{
                            "Timestamp": time.strftime("%d/%m/%Y %H:%M:%S"),
                            "תעודת זהות": st.session_state['id'], "שם התלמיד": st.session_state['name'],
                            "שלב": current_stage, "שם הפרויקט": p_name,
                            "תוכן": f"טכנולוגיות: {', '.join(techs)}\n{desc}\nלינק: {link}",
                            "סטטוס": "הוגש"
                        }])
                        conn.update(worksheet="Form Responses 1",
                                    data=pd.concat([df_subs, new_data], ignore_index=True))
                        st.balloons();
                        st.success("נשלח!");
                        st.cache_data.clear();
                        time.sleep(2);
                        st.rerun()