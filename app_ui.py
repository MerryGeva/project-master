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

# --- חיבור וטעינה ---
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=2)
def load_all_data():
    try:
        subs = conn.read(worksheet="Form Responses 1", ttl=0)
        studs = conn.read(worksheet="students", ttl=0)
        conf = conn.read(worksheet="config", ttl=0)
        # וידוא קיום עמודת סטטוס
        if not subs.empty and 'סטטוס' not in subs.columns:
            subs['סטטוס'] = ""
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

df_subs, df_stud, df_conf = load_all_data()

if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])
    with t1:
        sid_input = st.text_input("תעודת זהות:").strip()
        if st.button("התחבר"):
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
    all_stages = df_conf.iloc[:, 0].dropna().tolist() if not df_conf.empty else ["שלב 1"]
    deadlines = df_conf.iloc[:, 1].tolist() if not df_conf.empty and len(df_conf.columns) > 1 else []
    tech_options = [str(t).strip() for t in df_conf.iloc[:, 2].dropna().unique()] if not df_conf.empty and len(
        df_conf.columns) >= 3 else ["Python", "JS"]

    display_name = st.session_state.get('name') or "המורה"
    st.sidebar.title(f"שלום {display_name}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear();
        st.rerun()

    # --- ממשק מורה ---
    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה למורה")
        tab_map, tab_approve, tab_config, tab_students = st.tabs(
            ["🗺️ מפת כיתה", "✅ אישור הגשות", "⚙️ הגדרות", "👥 תלמידים"])

        with tab_approve:
            st.subheader("📥 הגשות חדשות")
            # עבודה על עותק של הנתונים כדי לא לשבש את המקור בזמן הלחיצות
            if 'temp_subs' not in st.session_state:
                st.session_state.temp_subs = df_subs.copy()

            pending = st.session_state.temp_subs[st.session_state.temp_subs['סטטוס'] == 'הוגש']

            if pending.empty:
                st.info("אין הגשות חדשות כרגע.")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"🆕 {row['שם התלמיד']} - {row['שלב']}"):
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown(f"**פרויקט:** {row['שם הפרויקט']}")
                            parts = str(row['תוכן']).split("לינק: ")
                            main_content = parts[0]
                            link_url = parts[1].strip() if len(parts) > 1 else ""
                            st.markdown(f"**תוכן:**\n{main_content}")
                            if link_url:
                                st.markdown(
                                    f"""<div class='link-box'>🔗 <b>קישור:</b> <a href='{link_url}' target='_blank'>{link_url}</a></div>""",
                                    unsafe_allow_html=True)
                        with c2:
                            # כפתור אישור
                            if st.button("אשר ✅", key=f"ok_{idx}"):
                                try:
                                    # עדכון מקומי ב-DataFrame הקיים בזיכרון
                                    df_subs.at[idx, 'סטטוס'] = "מאושר"
                                    # שליחה אחת לגוגל שייטס
                                    conn.update(worksheet="Form Responses 1", data=df_subs)
                                    st.success("אושר בהצלחה!")
                                    # רענון הזיכרון המקומי
                                    st.cache_data.clear()
                                    time.sleep(0.5)  # השהייה קלה למניעת הצפה
                                    st.rerun()
                                except Exception as e:
                                    if "429" in str(e):
                                        st.error("גוגל חסמה את הבקשה עקב עומס. המתן 5 שניות ונסה שוב.")
                                    else:
                                        st.error(f"שגיאה: {e}")

                            # כפתור לתיקון
                            if st.button("לתיקון ❌", key=f"fix_{idx}"):
                                try:
                                    df_subs.at[idx, 'סטטוס'] = "לתיקון"
                                    conn.update(worksheet="Form Responses 1", data=df_subs)
                                    st.warning("הוחזר לתיקון")
                                    st.cache_data.clear()
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"שגיאה: {e}")
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

        with tab_students:
            edited_studs = st.data_editor(df_stud, num_rows="dynamic", key="stud_edit")
            if st.button("💾 שמור רשימה"):
                conn.update(worksheet="students", data=edited_studs.astype(str))
                st.cache_data.clear();
                st.success("נשמר!");
                st.rerun()

        with tab_config:
            edited_conf = st.data_editor(df_conf, num_rows="dynamic", key="conf_edit")
            if st.button("💾 שמור הגדרות"):
                conn.update(worksheet="config", data=edited_conf)
                st.cache_data.clear();
                st.success("נשמר!");
                st.rerun()

    # --- ממשק תלמיד ---
    elif st.session_state['role'] == 'student':
        my_id = clean_val(st.session_state['id']).lstrip('0')
        my_subs = df_subs[df_subs.iloc[:, 1].apply(lambda x: clean_val(x).lstrip('0')) == my_id]

        # חישוב שלב נוכחי
        current_stage, current_status = all_stages[0], ""
        for s in all_stages:
            sub = my_subs[my_subs['שלב'] == s]
            stat = sub.iloc[-1]['סטטוס'] if not sub.empty else ""
            if stat == "לתיקון":
                current_stage, current_status = s, stat; break
            elif stat != "מאושר":
                current_stage, current_status = s, stat; break

        # סיידבר
        st.sidebar.subheader("📍 מצב התקדמות:")
        today = datetime.now()
        for i, s in enumerate(all_stages):
            sub = my_subs[my_subs['שלב'] == s];
            stat = sub.iloc[-1]['סטטוס'] if not sub.empty else ""
            dl_str = deadlines[i] if i < len(deadlines) else ""
            overdue = False
            if dl_str and stat != "מאושר":
                try:
                    if pd.to_datetime(dl_str, dayfirst=True) < today: overdue = True
                except:
                    pass
            icon = "✅" if stat == "מאושר" else ("❌" if stat == "לתיקון" else ("⏳" if stat == "הוגש" else "⚪"))
            txt = f"{icon} {s}" + (f" ({dl_str})" if dl_str else "")
            if overdue:
                st.sidebar.markdown(f"<span class='status-red'>{txt}</span>", unsafe_allow_html=True)
            else:
                st.sidebar.write(txt)

        st.header(f"שלום {st.session_state['name']}")

        if current_status == "הוגש":
            st.markdown(
                f"<div class='pending-notice'>⏳ שלב <b>{current_stage}</b> נשלח ובבדיקה. לא ניתן להגיש שוב כרגע.</div>",
                unsafe_allow_html=True)
        else:
            if current_status == "לתיקון":
                st.markdown(f"""<div class='fix-notice'>⚠️ המורה ביקש תיקון לשלב: <b>{current_stage}</b></div>""",
                            unsafe_allow_html=True)

            last_sub = my_subs.iloc[-1] if not my_subs.empty else None
            last_p_name = last_sub['שם הפרויקט'] if last_sub is not None else ""

            with st.form("submit_form"):
                # סדר השדות המבוקש
                st.subheader(f"הגשה נוכחית: {current_stage}")

                # שם הפרויקט - ראשון
                if current_stage == all_stages[0]:
                    p_name = st.text_input("שם הפרויקט:", value=last_p_name)
                else:
                    st.markdown(f"**שם הפרויקט:** {last_p_name}")
                    p_name = last_p_name

                # יתר השדות
                c1, c2 = st.columns(2)
                with c1:
                    link = st.text_input("קישור לתוצר:")
                with c2:
                    techs = st.multiselect("טכנולוגיות בשימוש:", tech_options)

                desc = st.text_area("תיאור הביצוע לשלב זה:")

                if st.form_submit_button("🚀 שלח הגשה"):
                    if not p_name or not desc:
                        st.warning("נא למלא קישור למסמך מפורט ותיאור.")
                    elif current_stage != all_stages[0] and not link:
                        st.error("חובה להוסיף קישור!")
                    else:
                        new_data = pd.DataFrame([{
                            "Timestamp": time.strftime("%d/%m/%Y %H:%M:%S"),
                            "תעודת זהות": st.session_state['id'],
                            "שם התלמיד": st.session_state['name'],
                            "שלב": current_stage,
                            "שם הפרויקט": p_name,
                            "תוכן": f"טכנולוגיות: {', '.join(techs)}\n{desc}\nלינק: {link}",
                            "סטטוס": "הוגש"
                        }])
                        conn.update(worksheet="Form Responses 1",
                                    data=pd.concat([df_subs, new_data], ignore_index=True))
                        st.balloons();
                        st.cache_data.clear();
                        time.sleep(1);
                        st.rerun()