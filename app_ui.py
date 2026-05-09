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


def normalize_id(v):
    """מנקה תעודת זהות ומוסיפה אפסים מובילים לפורמט של 9 ספרות"""
    if pd.isna(v) or v == "": return ""
    s = str(v).split('.')[0]
    s = ''.join(filter(str.isdigit, s))
    if not s: return ""
    return s.zfill(9)


@st.cache_data(ttl=10)  # העלאת ה-TTL ל-10 שניות להורדת עומס
def load_all_data():
    """ניסיון טעינה עדין יותר"""
    try:
        subs = conn.read(worksheet="Form Responses 1", ttl=0).fillna("")
        studs = conn.read(worksheet="students", ttl=0).fillna("")
        conf = conn.read(worksheet="config", ttl=0).fillna("")

        # ניקוי שמות עמודות
        for df in [subs, studs, conf]:
            df.columns = [str(c).strip() for c in df.columns]

        critical = ["Timestamp", "תעודת זהות", "שם התלמיד", "שלב", "שם הפרויקט", "תוכן", "קישור", "סטטוס"]
        for col in critical:
            if col not in subs.columns: subs[col] = ""

        return subs, studs, conf, True
    except Exception as e:
        # במקום st.stop(), נחזיר דאטה ריק וסימון שגיאה
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False


# טעינה
df_subs, df_stud, df_conf, success = load_all_data()

# במקום לעצור הכל, נציג אזהרה אם הטעינה נכשלה
if not success:
    st.warning("⚠️ גוגל לא עונה לרגע. מנסה להתחבר שוב ברקע... (אפשר לנסות לרענן פעם אחת)")
    # אם אין נתונים בכלל, רק אז נעצור
    if df_subs.empty:
        st.stop()

# שליפת הגדרות
if not df_conf.empty and "שלב" in df_conf.columns:
    all_stages = df_conf["שלב"].dropna().astype(str).tolist()
    tech_options = df_conf["טכנולוגיות"].dropna().unique().tolist() if "טכנולוגיות" in df_conf.columns else ["Python"]
else:
    all_stages, tech_options = ["שלב 1"], ["Python"]

# --- 3. ניהול כניסה ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])
    with t1:
        sid_input = st.text_input("תעודת זהות:").strip()
        if st.button("התחבר"):
            u_norm = normalize_id(sid_input)
            found_user = None
            if not df_stud.empty:
                for _, row in df_stud.iterrows():
                    if normalize_id(row.iloc[0]) == u_norm and u_norm != "":
                        found_user = row
                        break
            if found_user is not None:
                st.session_state.update(
                    {'logged_in': True, 'role': 'student', 'id': u_norm, 'name': str(found_user.iloc[1])})
                st.rerun()
            else:
                st.error(f"תעודת זהות לא נמצאה. (נסה להזין שוב)")
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
            st.subheader("📍 התקדמות")
            my_id = normalize_id(st.session_state['id'])
            my_s = df_subs[df_subs['תעודת זהות'].apply(normalize_id) == my_id]
            for s in all_stages:
                stat = my_s[my_s['שלב'] == s].iloc[-1]['סטטוס'] if not my_s[my_s['שלב'] == s].empty else ""
                icon = "✅" if stat == "מאושר" else ("❌" if stat == "לתיקון" else ("⏳" if stat == "הוגש" else "⚪"))
                st.write(f"{icon} {s}")

    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה למורה")
        t_map, t_approve, t_config, t_studs = st.tabs(["🗺️ מפת כיתה", "✅ אישור הגשות", "⚙️ הגדרות", "👥 תלמידים"])

        with t_approve:
            pending = df_subs[df_subs['סטטוס'] == 'הוגש']
            if pending.empty:
                st.info("אין הגשות חדשות.")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"🆕 {row['שם התלמיד']} - {row['שלב']}"):
                        st.write(f"**פרויקט:** {row['שם הפרויקט']}\n\n**תיאור:** {row['תוכן']}")
                        if str(row['קישור']).strip():
                            st.markdown(f"🔗 <a href='{row['קישור']}' target='_blank'>צפה בתוצר</a>",
                                        unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        if c1.button("אשר ✅", key=f"ok_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "מאושר"
                            try:
                                conn.update(worksheet="Form Responses 1", data=df_subs)
                                st.cache_data.clear();
                                st.rerun()
                            except:
                                st.error("גוגל עמוס, נסה שוב בעוד 2 שניות.")
                        if c2.button("לתיקון ❌", key=f"fix_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "לתיקון"
                            try:
                                conn.update(worksheet="Form Responses 1", data=df_subs)
                                st.cache_data.clear();
                                st.rerun()
                            except:
                                st.error("גוגל עמוס, נסה שוב בעוד 2 שניות.")
            st.markdown("---")
            st.subheader("📜 כל ההגשות")
            st.dataframe(df_subs.iloc[::-1], use_container_width=True, hide_index=True)

        with t_map:
            if not df_stud.empty:
                map_d = []
                for _, s_row in df_stud.iterrows():
                    sid = normalize_id(s_row.iloc[0])
                    row_m = {"תלמיד": s_row.iloc[1]}
                    for stage in all_stages:
                        st_subs = df_subs[
                            (df_subs['תעודת זהות'].apply(normalize_id) == sid) & (df_subs['שלב'] == stage)]
                        last_s = st_subs.iloc[-1]['סטטוס'] if not st_subs.empty else "⚪"
                        row_m[stage] = "✅" if last_s == "מאושר" else (
                            "⏳" if last_s == "הוגש" else ("❌" if last_s == "לתיקון" else "⚪"))
                    map_d.append(row_m)
                st.dataframe(pd.DataFrame(map_d), use_container_width=True, hide_index=True)

        with t_studs:
            e_s = st.data_editor(df_stud, num_rows="dynamic", key="ed_s")
            if st.button("שמור תלמידים"):
                conn.update(worksheet="students", data=e_s);
                st.cache_data.clear();
                st.rerun()

        with t_config:
            e_c = st.data_editor(df_conf, num_rows="dynamic", key="ed_c")
            if st.button("שמור הגדרות"):
                conn.update(worksheet="config", data=e_c);
                st.cache_data.clear();
                st.rerun()

    else:  # ממשק תלמיד
        my_id = normalize_id(st.session_state['id'])
        my_subs = df_subs[df_subs['תעודת זהות'].apply(normalize_id) == my_id]
        curr_stage = all_stages[0]
        curr_stat = ""
        for s in all_stages:
            s_sub = my_subs[my_subs['שלב'] == s]
            stt = s_sub.iloc[-1]['סטטוס'] if not s_sub.empty else ""
            if stt in ["", "לתיקון"]: curr_stage, curr_stat = s, stt; break
            if stt == "הוגש": curr_stage, curr_stat = s, stt; break

        st.header(f"שלום {st.session_state['name']}")
        if curr_stat == "הוגש":
            st.info(f"שלב {curr_stage} נשלח וממתין לבדיקה.")
        else:
            if curr_stat == "לתיקון": st.warning(f"נדרש תיקון לשלב {curr_stage}")
            last_p = my_subs.iloc[-1]['שם הפרויקט'] if not my_subs.empty else ""
            with st.form("sub_f"):
                st.subheader(f"הגשה לשלב: {curr_stage}")
                p_n = st.text_input("שם פרויקט:", value=last_p) if curr_stage == all_stages[0] else last_p
                link = st.text_input("קישור:")
                techs = st.multiselect("טכנולוגיות:", tech_options)
                desc = st.text_area("תיאור המשימה שביצעת:")
                if st.form_submit_button("🚀 שלח"):
                    if not p_n or not desc:
                        st.error("מלא שדות חובה.")
                    else:
                        new_r = {"Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                 "תעודת זהות": st.session_state['id'], "שם התלמיד": st.session_state['name'],
                                 "שלב": curr_stage, "שם הפרויקט": p_n,
                                 "תוכן": f"טכנולוגיות: {', '.join(techs)}\n{desc}", "קישור": link, "סטטוס": "הוגש"}
                        try:
                            conn.update(worksheet="Form Responses 1",
                                        data=pd.concat([df_subs, pd.DataFrame([new_r])], ignore_index=True))
                            st.balloons();
                            st.cache_data.clear();
                            time.sleep(1);
                            st.rerun()
                        except:
                            st.error("שגיאה בשליחה לגוגל, נסה שוב בעוד רגע.")