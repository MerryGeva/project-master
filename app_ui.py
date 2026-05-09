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

# --- 2. חיבור וטעינת נתונים עם הגנה משגיאות מכסה ---
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=5)  # העלאת ה-TTL ל-5 שניות להורדת עומס
def load_all_data():
    try:
        subs = conn.read(worksheet="Form Responses 1", ttl=0).fillna("")
        studs = conn.read(worksheet="students", ttl=0).fillna("")
        conf = conn.read(worksheet="config", ttl=0).fillna("")

        # ניקוי שמות עמודות
        subs.columns = [str(c).strip() for c in subs.columns]
        studs.columns = [str(c).strip() for c in studs.columns]
        conf.columns = [str(c).strip() for c in conf.columns]

        # וידוא עמודות קריטיות - אם הן חסרות, ניצור אותן כדי למנוע KeyError
        critical_cols = ["Timestamp", "תעודת זהות", "שם התלמיד", "שלב", "שם הפרויקט", "תוכן", "קישור", "סטטוס"]
        for col in critical_cols:
            if col not in subs.columns:
                subs[col] = ""

        return subs, studs, conf, True
    except Exception as e:
        # אם יש שגיאת Quota (429), נחזיר דאטה ריק וסימון שהטעינה נכשלה
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False


def clean_val(v):
    s = str(v).strip()
    if s.endswith('.0'): s = s[:-2]
    return ''.join(filter(str.isdigit, s))


# ניסיון טעינה
df_subs, df_stud, df_conf, success = load_all_data()

# אם הטעינה נכשלה בגלל Quota
if not success:
    st.error("⚠️ עומס על שרתי גוגל. המערכת תתאושש אוטומטית תוך דקה. נא לא לרענן את העמוד בטירוף...")
    st.stop()

# --- 3. שליפת הגדרות מה-Config ---
if not df_conf.empty and "שלב" in df_conf.columns:
    all_stages = df_conf["שלב"].dropna().astype(str).tolist()
    deadlines = df_conf["דד-ליין"].astype(str).tolist() if "דד-ליין" in df_conf.columns else []
    tech_options = df_conf["טכנולוגיות"].dropna().unique().tolist() if "טכנולוגיות" in df_conf.columns else ["Python"]
    tech_options = [str(t).strip() for t in tech_options if str(t).strip() != ""]
else:
    all_stages, deadlines, tech_options = ["שלב 1"], [], ["Python"]

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

# --- 5. ממשק לאחר התחברות ---
else:
    with st.sidebar:
        st.title(f"שלום, {st.session_state['name']}")
        if st.button("🚪 התנתק"):
            st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})
            st.rerun()

        if st.session_state['role'] == 'student':
            st.markdown("---")
            st.subheader("📍 ההתקדמות שלי")
            my_id = clean_val(st.session_state['id']).lstrip('0')
            my_subs = df_subs[df_subs['תעודת זהות'].apply(lambda x: clean_val(x).lstrip('0')) == my_id]
            today = datetime.now()
            for i, stage in enumerate(all_stages):
                sub = my_subs[my_subs['שלב'] == stage]
                status = sub.iloc[-1]['סטטוס'] if not sub.empty else ""
                dl_str = deadlines[i] if i < len(deadlines) else ""
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

    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה למורה")
        t_map, t_approve, t_config, t_studs = st.tabs(["🗺️ מפת כיתה", "✅ אישור הגשות", "⚙️ הגדרות", "👥 תלמידים"])

        with t_approve:
            st.subheader("📥 הגשות חדשות")
            # כאן הוספתי הגנה נוספת למקרה שהעמודה 'סטטוס' נעלמה בטעות
            if 'סטטוס' in df_subs.columns:
                pending = df_subs[df_subs['סטטוס'] == 'הוגש']
                if pending.empty:
                    st.info("אין הגשות חדשות כרגע.")
                else:
                    for idx, row in pending.iterrows():
                        with st.expander(f"🆕 {row['שם התלמיד']} - {row['שלב']}"):
                            c1, c2 = st.columns([2, 1])
                            with c1:
                                st.write(f"**פרויקט:** {row['שם הפרויקט']}")
                                st.write(f"**תיאור:** {row['תוכן']}")
                                if str(row['קישור']).strip():
                                    st.markdown(
                                        f"<div class='link-box'>🔗 <a href='{row['קישור']}' target='_blank'>צפה בתוצר</a></div>",
                                        unsafe_allow_html=True)
                            with c2:
                                if st.button("אשר ✅", key=f"ok_{idx}"):
                                    df_subs.at[idx, 'סטטוס'] = "מאושר"
                                    conn.update(worksheet="Form Responses 1", data=df_subs)
                                    st.cache_data.clear();
                                    st.rerun()
                                if st.button("לתיקון ❌", key=f"fix_{idx}"):
                                    df_subs.at[idx, 'סטטוס'] = "לתיקון"
                                    conn.update(worksheet="Form Responses 1", data=df_subs)
                                    st.cache_data.clear();
                                    st.rerun()
                st.markdown("---")
                st.subheader("📜 היסטוריה")
                st.dataframe(df_subs[df_subs['סטטוס'].isin(['מאושר', 'לתיקון'])].iloc[::-1], use_container_width=True,
                             hide_index=True)
            else:
                st.warning("עמודת 'סטטוס' לא נמצאה בגיליון.")

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
            edited_s = st.data_editor(df_stud, num_rows="dynamic", key="edit_s_v3")
            if st.button("💾 שמור תלמידים"):
                conn.update(worksheet="students", data=edited_s);
                st.cache_data.clear();
                st.rerun()

        with t_config:
            edited_c = st.data_editor(df_conf, num_rows="dynamic", key="edit_c_v3")
            if st.button("💾 שמור הגדרות"):
                conn.update(worksheet="config", data=edited_c);
                st.cache_data.clear();
                st.rerun()

    elif st.session_state['role'] == 'student':
        my_id = clean_val(st.session_state['id']).lstrip('0')
        my_subs = df_subs[df_subs['תעודת זהות'].apply(lambda x: clean_val(x).lstrip('0')) == my_id]
        current_stage, current_status = all_stages[0], ""
        for s in all_stages:
            sub = my_subs[my_subs['שלב'] == s];
            stat = sub.iloc[-1]['סטטוס'] if not sub.empty else ""
            if stat == "לתיקון":
                current_stage, current_status = s, stat; break
            elif stat != "מאושר":
                current_stage, current_status = s, stat; break

        st.header(f"שלום {st.session_state['name']}")
        if current_status == "הוגש":
            st.markdown(f"<div class='pending-notice'>⏳ שלב <b>{current_stage}</b> בבדיקה.</div>",
                        unsafe_allow_html=True)
        else:
            if current_status == "לתיקון":
                st.markdown(f"<div class='fix-notice'>⚠️ נדרש תיקון לשלב: <b>{current_stage}</b></div>",
                            unsafe_allow_html=True)
            last_sub = my_subs.iloc[-1] if not my_subs.empty else None
            last_p_name = last_sub['שם הפרויקט'] if last_sub is not None else ""
            with st.form("submit_form_v3"):
                st.subheader(f"הגשה ל{current_stage}")
                p_name = st.text_input("שם הפרויקט:", value=last_p_name) if current_stage == all_stages[
                    0] else last_p_name
                if current_stage != all_stages[0]: st.markdown(f"**פרויקט:** {last_p_name}")
                link = st.text_input("קישור לתוצר:")
                techs = st.multiselect("טכנולוגיות:", tech_options)
                desc = st.text_area("תיאור:")
                if st.form_submit_button("🚀 שלח"):
                    if not p_name or not desc:
                        st.warning("מלא שדות חובה.")
                    else:
                        new_row = {"Timestamp": time.strftime("%d/%m/%Y %H:%M:%S"),
                                   "תעודת זהות": st.session_state['id'], "שם התלמיד": st.session_state['name'],
                                   "שלב": current_stage, "שם הפרויקט": p_name,
                                   "תוכן": f"טכנולוגיות: {', '.join(techs)}\n{desc}", "קישור": link, "סטטוס": "הוגש"}
                        conn.update(worksheet="Form Responses 1",
                                    data=pd.concat([df_subs, pd.DataFrame([new_row])], ignore_index=True))
                        st.balloons();
                        st.cache_data.clear();
                        time.sleep(1);
                        st.rerun()