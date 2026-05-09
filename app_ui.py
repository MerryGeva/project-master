import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime

# --- 1. הגדרות עיצוב RTL ---
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

# --- 2. חיבור וטעינת נתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=2)
def load_all_data():
    try:
        subs = conn.read(worksheet="Form Responses 1", ttl=0).fillna("")
        studs = conn.read(worksheet="students", ttl=0).fillna("")
        conf = conn.read(worksheet="config", ttl=0).fillna("")

        # ניקוי שמות עמודות
        subs.columns = [str(c).strip() for c in subs.columns]
        studs.columns = [str(c).strip() for c in studs.columns]
        conf.columns = [str(c).strip() for c in conf.columns]

        # וידוא עמודות קריטיות
        cols = ["Timestamp", "תעודת זהות", "שם התלמיד", "שלב", "שם הפרויקט", "תוכן", "קישור", "סטטוס"]
        for col in cols:
            if col not in subs.columns: subs[col] = ""

        return subs, studs, conf
    except Exception as e:
        st.error(f"שגיאה בטעינת נתונים: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def clean_val(v):
    s = str(v).strip()
    if s.endswith('.0'): s = s[:-2]
    return ''.join(filter(str.isdigit, s))


df_subs, df_stud, df_conf = load_all_data()

# --- 3. שליפת הגדרות מה-Config ---
if not df_conf.empty:
    all_stages = df_conf["שלב"].dropna().astype(str).tolist() if "שלב" in df_conf.columns else ["שלב 1"]
    deadlines = df_conf["דד-ליין"].astype(str).tolist() if "דד-ליין" in df_conf.columns else []
    tech_options = df_conf["טכנולוגיות"].dropna().unique().tolist() if "טכנולוגיות" in df_conf.columns else ["Python",
                                                                                                             "JavaScript"]
    tech_options = [str(t).strip() for t in tech_options if str(t).strip() != ""]
else:
    all_stages, deadlines, tech_options = ["שלב 1"], [], ["Python", "JavaScript"]

# --- 4. ניהול התחברות ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])
    with t1:
        sid_input = st.text_input("תעודת זהות:").strip()
        if st.button("התחבר"):
            user_id_clean = clean_val(sid_input).lstrip('0')
            found_user = None
            if not df_stud.empty:
                for _, row in df_stud.iterrows():
                    id_val = row.get('תעודת זהות', row.iloc[0])
                    if clean_val(id_val).lstrip('0') == user_id_clean:
                        found_user = row
                        break
            if found_user is not None:
                name_val = found_user.get('שם התלמיד', found_user.iloc[1])
                st.session_state.update({'logged_in': True, 'role': 'student', 'id': sid_input, 'name': name_val})
                st.rerun()
            else:
                st.error("תעודת זהות לא נמצאה.")
    with t2:
        pwd = st.text_input("סיסמת מורה:", type="password")
        if st.button("כניסה"):
            if pwd == "123":
                st.session_state.update({'logged_in': True, 'role': 'teacher', 'name': 'המורה'})
                st.rerun()

# --- 5. ממשק לאחר התחברות (מורה/תלמיד) ---
else:
    # סרגל צדדי משותף
    with st.sidebar:
        st.title(f"שלום, {st.session_state['name']}")
        if st.button("🚪 התנתק"):
            st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})
            st.rerun()
        st.markdown("---")

        # הצגת התקדמות בסרגל הצדדי (רק לתלמיד)
        if st.session_state['role'] == 'student':
            st.subheader("📍 ההתקדמות שלי")
            my_id = clean_val(st.session_state['id']).lstrip('0')
            my_subs = df_subs[df_subs['תעודת זהות'].apply(lambda x: clean_val(x).lstrip('0')) == my_id]
            today = datetime.now()

            for i, stage in enumerate(all_stages):
                sub = my_subs[my_subs['שלב'] == stage]
                status = sub.iloc[-1]['סטטוס'] if not sub.empty else ""
                dl_str = deadlines[i] if i < len(deadlines) else ""

                # בדיקת איחור
                overdue = False
                if dl_str and status != "מאושר":
                    try:
                        if pd.to_datetime(dl_str, dayfirst=True) < today: overdue = True
                    except:
                        pass

                icon = "✅" if status == "מאושר" else ("❌" if status == "לתיקון" else ("⏳" if status == "הוגש" else "⚪"))
                label = f"{icon} {stage}" + (f" ({dl_str})" if dl_str else "")

                if overdue:
                    st.markdown(f"<span class='status-red'>{label}</span>", unsafe_allow_html=True)
                else:
                    st.write(label)

    # --- ממשק מורה ---
    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה למורה")
        t_map, t_approve, t_config, t_studs = st.tabs(["🗺️ מפת כיתה", "✅ אישור הגשות", "⚙️ הגדרות", "👥 תלמידים"])

        with t_approve:
            st.subheader("📥 הגשות חדשות")
            pending = df_subs[df_subs['סטטוס'] == 'הוגש']
            if pending.empty:
                st.info("אין הגשות חדשות.")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"🆕 {row['שם התלמיד']} - {row['שלב']}"):
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown(f"**פרויקט:** {row['שם הפרויקט']}")
                            st.markdown(f"**תיאור:**\n{row['תוכן']}")
                            link_val = str(row['קישור']).strip()
                            if link_val:
                                st.markdown(
                                    f"""<div class='link-box'>🔗 <a href='{link_val}' target='_blank'>לחץ לצפייה בתוצר</a></div>""",
                                    unsafe_allow_html=True)
                        with c2:
                            if st.button("אשר ✅", key=f"ok_{idx}"):
                                df_subs.at[idx, 'סטטוס'] = "מאושר"
                                conn.update(worksheet="Form Responses 1", data=df_subs)
                                st.cache_data.clear();
                                st.success("אושר!");
                                time.sleep(1);
                                st.rerun()
                            if st.button("לתיקון ❌", key=f"fix_{idx}"):
                                df_subs.at[idx, 'סטטוס'] = "לתיקון"
                                conn.update(worksheet="Form Responses 1", data=df_subs)
                                st.cache_data.clear();
                                st.warning("הוחזר לתיקון");
                                time.sleep(1);
                                st.rerun()

            st.markdown("---")
            st.subheader("📜 היסטוריה (מאושרים/לתיקון)")
            st.dataframe(df_subs[df_subs['סטטוס'].isin(['מאושר', 'לתיקון'])].iloc[::-1], use_container_width=True,
                         hide_index=True)

        with t_map:
            if not df_stud.empty:
                map_list = []
                for _, s_row in df_stud.iterrows():
                    sid = clean_val(s_row.get('תעודת זהות', s_row.iloc[0])).lstrip('0')
                    row_map = {"תלמיד": s_row.get('שם התלמיד', s_row.iloc[1])}
                    for stage in all_stages:
                        sub = df_subs[(df_subs['תעודת זהות'].apply(lambda x: clean_val(x).lstrip('0')) == sid) & (
                                    df_subs['שלב'] == stage)]
                        status = sub.iloc[-1]['סטטוס'] if not sub.empty else "⚪"
                        row_map[stage] = "✅" if status == "מאושר" else (
                            "❌" if status == "לתיקון" else ("⏳" if status == "הוגש" else "⚪"))
                    map_list.append(row_map)
                st.table(pd.DataFrame(map_list))

        with t_studs:
            st.subheader("👥 ניהול רשימת תלמידים")
            edited_s = st.data_editor(df_stud, num_rows="dynamic", key="edit_s_final")
            if st.button("💾 שמור תלמידים"):
                conn.update(worksheet="students", data=edited_s);
                st.cache_data.clear();
                st.success("נשמר");
                st.rerun()

        with t_config:
            st.subheader("⚙️ הגדרות מערכת")
            edited_c = st.data_editor(df_conf, num_rows="dynamic", key="edit_c_final")
            if st.button("💾 שמור הגדרות"):
                conn.update(worksheet="config", data=edited_c);
                st.cache_data.clear();
                st.success("נשמר");
                st.rerun()

    # --- ממשק תלמיד ---
    elif st.session_state['role'] == 'student':
        my_id = clean_val(st.session_state['id']).lstrip('0')
        my_subs = df_subs[df_subs['תעודת זהות'].apply(lambda x: clean_val(x).lstrip('0')) == my_id]

        # מציאת השלב הנוכחי להגשה
        current_stage, current_status = all_stages[0], ""
        for s in all_stages:
            sub = my_subs[my_subs['שלב'] == s]
            stat = sub.iloc[-1]['סטטוס'] if not sub.empty else ""
            if stat == "לתיקון":
                current_stage, current_status = s, stat
                break
            elif stat != "מאושר":
                current_stage, current_status = s, stat
                break

        st.header(f"הגשת פרויקט - {st.session_state['name']}")

        if current_status == "הוגש":
            st.markdown(f"<div class='pending-notice'>⏳ שלב <b>{current_stage}</b> נשלח ובהמתנה לבדיקת מורה.</div>",
                        unsafe_allow_html=True)
        else:
            if current_status == "לתיקון":
                st.markdown(
                    f"<div class='fix-notice'>⚠️ המורה ביקש תיקונים לשלב: <b>{current_stage}</b>. אנא הגש שוב.</div>",
                    unsafe_allow_html=True)

            last_sub = my_subs.iloc[-1] if not my_subs.empty else None
            last_p_name = last_sub['שם הפרויקט'] if last_sub is not None else ""

            with st.form("submit_form_final"):
                st.subheader(f"מגיש כעת: {current_stage}")

                # שדה שם פרויקט (ראשון בטופס)
                if current_stage == all_stages[0]:
                    p_name = st.text_input("שם הפרויקט:", value=last_p_name)
                else:
                    st.markdown(f"**שם הפרויקט:** {last_p_name}")
                    p_name = last_p_name

                link = st.text_input("קישור לתוצר (GitHub / Drive / Figma):")
                techs = st.multiselect("טכנולוגיות ששימשו אותי בשלב זה:", tech_options)
                desc = st.text_area("תיאור קצר של מה שביצעת:")

                if st.form_submit_button("🚀 שלח הגשה"):
                    if not p_name or not desc:
                        st.warning("בבקשה מלא את שם הפרויקט ותיאור הביצוע.")
                    elif current_stage != all_stages[0] and not link:
                        st.error("חובה לצרף קישור משלב 2 והלאה.")
                    else:
                        new_row = {
                            "Timestamp": time.strftime("%d/%m/%Y %H:%M:%S"),
                            "תעודת זהות": st.session_state['id'],
                            "שם התלמיד": st.session_state['name'],
                            "שלב": current_stage,
                            "שם הפרויקט": p_name,
                            "תוכן": f"טכנולוגיות: {', '.join(techs)}\n{desc}",
                            "קישור": link,
                            "סטטוס": "הוגש"
                        }
                        conn.update(worksheet="Form Responses 1",
                                    data=pd.concat([df_subs, pd.DataFrame([new_row])], ignore_index=True))
                        st.balloons()
                        st.cache_data.clear()
                        st.success("ההגשה נשלחה בהצלחה!")
                        time.sleep(1)
                        st.rerun()