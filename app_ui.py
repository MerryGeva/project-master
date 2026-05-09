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
    .stDataFrame, .stTable { direction: rtl; }
    .status-red { color: #ff4b4b; font-weight: bold; }
    .link-box { 
        background-color: #e1f5fe; 
        padding: 10px; 
        border-radius: 5px; 
        border-right: 5px solid #03a9f4;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור וטעינה ---
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=60)
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
                st.session_state.update({'logged_in': True, 'role': 'teacher'})
                st.rerun()
else:
    df_subs, df_stud, df_conf = load_all_data()

    # --- הגדרות מה-Config ---
    # עמודה A: שלב, עמודה B: דד-ליין, עמודה C: טכנולוגיות
    all_stages = df_conf.iloc[:, 0].dropna().tolist() if not df_conf.empty else ["שלב 1"]
    deadlines = df_conf.iloc[:, 1].tolist() if not df_conf.empty and len(df_conf.columns) > 1 else []
    tech_options = []
    if not df_conf.empty and len(df_conf.columns) >= 3:
        tech_options = [str(t).strip() for t in df_conf.iloc[:, 2].dropna().unique() if str(t).strip() != ""]

    st.sidebar.title(f"שלום {st.session_state.get('name', 'המורה')}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

    # --- ממשק מורה ---
    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 ניהול כיתה")
        tab_map, tab_approve, tab_config, tab_students = st.tabs(
            ["🗺️ מפת כיתה", "✅ אישור הגשות", "⚙️ הגדרות", "👥 תלמידים"])

        with tab_approve:
            pending = df_subs[df_subs['סטטוס'].isin(['הוגש', 'לתיקון'])]
            if pending.empty:
                st.success("אין הגשות חדשות.")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"📌 {row['שם התלמיד']} - {row['שלב']}"):
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown(f"### פרויקט: {row['שם הפרויקט']}")
                            # חילוץ הלינק מהתוכן להבלטה
                            content_parts = row['תוכן'].split("לינק: ")
                            desc_part = content_parts[0]
                            link_url = content_parts[1] if len(content_parts) > 1 else ""

                            st.markdown(f"**תיאור וטכנולוגיות:**\n{desc_part}")
                            if link_url and link_url.strip():
                                st.markdown(
                                    f"""<div class='link-box'>🔗 <b>קישור לתוצר:</b> <a href='{link_url}' target='_blank'>{link_url}</a></div>""",
                                    unsafe_allow_html=True)
                            else:
                                st.warning("לא צורף קישור לשלב זה.")
                        with c2:
                            if st.button("אשר ✅", key=f"ok_{idx}", use_container_width=True):
                                df_subs.at[idx, 'סטטוס'] = "מאושר"
                                conn.update(worksheet="Form Responses 1", data=df_subs)
                                st.cache_data.clear();
                                st.rerun()
                            if st.button("לתיקון ❌", key=f"fix_{idx}", use_container_width=True):
                                df_subs.at[idx, 'סטטוס'] = "לתיקון"
                                conn.update(worksheet="Form Responses 1", data=df_subs)
                                st.cache_data.clear();
                                st.rerun()

        # (יתר הטאבים של המורה נשארים אותו דבר)
        with tab_map:
            if not df_stud.empty:
                map_list = []
                for _, s_row in df_stud.iterrows():
                    row_map = {"תלמיד": s_row.iloc[1]}
                    s_id = clean_val(s_row.iloc[0]).lstrip('0')
                    for stage in all_stages:
                        sub = df_subs[(df_subs.iloc[:, 1].apply(lambda x: clean_val(x).lstrip('0')) == s_id) & (
                                    df_subs['שלב'] == stage)]
                        status = sub.iloc[-1]['סטטוס'] if not sub.empty else "⚪"
                        row_map[stage] = "✅" if status == "מאושר" else (
                            "❌" if status == "לתיקון" else ("⏳" if status == "הוגש" else "⚪"))
                    map_list.append(row_map)
                st.table(pd.DataFrame(map_list))

        with tab_config:
            edited_conf = st.data_editor(df_conf, num_rows="dynamic", key="conf_edit")
            if st.button("שמור הגדרות"):
                conn.update(worksheet="config", data=edited_conf)
                st.cache_data.clear();
                st.rerun()

        with tab_students:
            edited_studs = st.data_editor(df_stud, num_rows="dynamic", key="stud_edit")
            if st.button("עדכן רשימה"):
                conn.update(worksheet="students", data=edited_studs)
                st.cache_data.clear();
                st.rerun()

    # --- ממשק תלמיד ---
    elif st.session_state['role'] == 'student':
        my_id = clean_val(st.session_state['id']).lstrip('0')
        my_subs = df_subs[df_subs.iloc[:, 1].apply(lambda x: clean_val(x).lstrip('0')) == my_id]

        # משיכת נתונים קודמים (שם פרויקט וטכנולוגיות)
        last_sub = my_subs.iloc[-1] if not my_subs.empty else None
        last_p_name = last_sub['שם הפרויקט'] if last_sub is not None else ""

        # חילוץ טכנולוגיות קודמות מהטקסט
        last_techs = []
        if last_sub is not None:
            try:
                tech_str = last_sub['תוכן'].split("\n")[0].replace("טכנולוגיות: ", "")
                last_techs = [t.strip() for t in tech_str.split(",") if t.strip() in tech_options]
            except:
                pass

        # סטטוסים ודד-ליינים בסיידבר
        st.sidebar.subheader("📍 מצב התקדמות:")
        allowed_stages = []
        found_next = False
        today = datetime.now()

        for i, s in enumerate(all_stages):
            sub = my_subs[my_subs['שלב'] == s]
            stat = sub.iloc[-1]['סטטוס'] if not sub.empty else "לא הוגש"

            # בדיקת דד-ליין
            dl_str = deadlines[i] if i < len(deadlines) else ""
            is_overdue = False
            if dl_str:
                try:
                    dl_dt = pd.to_datetime(dl_str, dayfirst=True)
                    if dl_dt < today and stat != "מאושר": is_overdue = True
                except:
                    pass

            dl_display = f" ({dl_str})" if dl_str else ""
            color_class = "status-red" if is_overdue else ""

            if stat == "מאושר":
                st.sidebar.write(f"✅ {s}{dl_display}")
                allowed_stages.append(s)
            elif not found_next:
                icon = "⏳" if stat == "הוגש" else "⚪"
                if is_overdue:
                    st.sidebar.markdown(f"{icon} <span class='status-red'>**{s}**</span>{dl_display}",
                                        unsafe_allow_html=True)
                else:
                    st.sidebar.write(f"{icon} **{s}**{dl_display}")
                allowed_stages.append(s)
                found_next = True
            else:
                st.sidebar.write(f"🔒 {s}{dl_display}")

        st.header(f"שלום, {st.session_state['name']}")

        with st.form("submit_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                stage = st.selectbox("בחר שלב להגשה:", allowed_stages)
                techs = st.multiselect("טכנולוגיות (נשמרות משלב קודם):", tech_options, default=last_techs)
            with c2:
                p_name = st.text_input("שם הפרויקט:", value=last_p_name)
                # חובת קישור: אם זה לא השלב הראשון (אינדקס 0), הקישור חובה
                is_first_stage = (stage == all_stages[0])
                link_label = "קישור לתוצר:" if is_first_stage else "קישור לתוצר (חובה משלב זה!):"
                link = st.text_input(link_label)

            desc = st.text_area("תיאור הביצוע לשלב זה:")

            if st.form_submit_button("🚀 שלח הגשה"):
                if not p_name or not desc:
                    st.warning("נא למלא שם פרויקט ותיאור.")
                elif not is_first_stage and not link:
                    st.error("החל מהשלב השני חובה לצרף קישור לתוצר!")
                else:
                    new_data = pd.DataFrame([{
                        "Timestamp": time.strftime("%d/%m/%Y %H:%M:%S"),
                        "תעודת זהות": st.session_state['id'],
                        "שם התלמיד": st.session_state['name'],
                        "שלב": stage,
                        "שם הפרויקט": p_name,
                        "תוכן": f"טכנולוגיות: {', '.join(techs)}\nתיאור: {desc}\nלינק: {link}",
                        "סטטוס": "הוגש"
                    }])
                    conn.update(worksheet="Form Responses 1", data=pd.concat([df_subs, new_data], ignore_index=True))
                    st.balloons()
                    st.success("ההגשה נשלחה בהצלחה!")
                    st.cache_data.clear()
                    time.sleep(2);
                    st.rerun()