import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime

# --- 1. הגדרות RTL ועיצוב גורף ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    h1, h2, h3, h4, h5, h6, p, span, label {
        text-align: right !important;
        direction: rtl !important;
    }
    div[data-testid="stDataFrame"] { direction: rtl; }
    .stButton button[kind="secondary"] { color: red; border-color: red; }
    button[data-baseweb="tab"] { direction: rtl; }
    /* עיצוב התראה אדומה */
    .overdue-text { color: #ff4b4b; font-weight: bold; }
    .overdue-box { 
        color: white; background-color: #ff4b4b; padding: 15px; 
        border-radius: 8px; font-weight: bold; text-align: center; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר וחיבור נתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)


def normalize_id(v):
    if pd.isna(v) or v == "": return ""
    s = str(v).split('.')[0]
    s = ''.join(filter(str.isdigit, s))
    return s.zfill(9) if s else ""


@st.cache_data(ttl=5, show_spinner=False)
def load_all_data():
    try:
        subs = conn.read(worksheet="Form Responses 1", ttl="2s").fillna("")
        studs = conn.read(worksheet="students", ttl="2s").fillna("")
        conf = conn.read(worksheet="config", ttl="2s").fillna("")
        for df in [subs, studs, conf]:
            df.columns = [str(c).strip() for c in df.columns]
        if "תאריך יעד" not in conf.columns: conf["תאריך יעד"] = ""
        return subs, studs, conf, True
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False


df_subs, df_stud, df_conf, success = load_all_data()


def safe_update(ws, data):
    try:
        # ניקוי עמודות "רפאים" לפני השמירה
        data = data.loc[:, ~data.columns.str.contains('^Unnamed')]
        conn.update(worksheet=ws, data=data)
        st.cache_data.clear()
        time.sleep(1)
        return True
    except Exception as e:
        st.error(f"שגיאה בעדכון: {e}")
        return False


if not success and df_subs.empty:
    st.warning("טוען נתונים מהגליון... נא להמתין.")
    st.stop()

all_stages = df_conf["שלב"].dropna().astype(str).str.strip().tolist() if not df_conf.empty else ["שלב 1"]
tech_options = df_conf["טכנולוגיות"].dropna().unique().tolist() if not df_conf.empty else ["Python"]

# --- 3. ניהול כניסה ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])
    with t1:
        sid_input = st.text_input("תעודת זהות (9 ספרות):").strip()
        if st.button("התחבר כתלמיד"):
            u_norm = normalize_id(sid_input)
            found = df_stud[df_stud.iloc[:, 0].apply(normalize_id) == u_norm] if not df_stud.empty else None
            if found is not None and not found.empty:
                st.session_state.update(
                    {'logged_in': True, 'role': 'student', 'id': u_norm, 'name': str(found.iloc[0, 1])})
                st.rerun()
            else:
                st.error("תעודת הזהות לא נמצאה ברשימת התלמידים.")
    with t2:
        pwd = st.text_input("סיסמת מורה:", type="password")
        if st.button("כניסה למערכת ניהול"):
            if pwd == "123":
                st.session_state.update({'logged_in': True, 'role': 'teacher', 'name': 'המורה'})
                st.rerun()

# --- 4. ממשק מחובר ---
else:
    with st.sidebar:
        st.title(f"שלום, {st.session_state['name']}")
        if st.button("🚪 התנתק מהמערכת"):
            st.session_state.clear();
            st.rerun()

        if st.session_state['role'] == 'student':
            st.markdown("---")
            st.subheader("📍 מצב שלבים")
            my_id = normalize_id(st.session_state['id'])
            my_s = df_subs[df_subs['תעודת זהות'].apply(normalize_id) == my_id]

            for s in all_stages:
                sub_at_stage = my_s[my_s['שלב'].str.strip() == s]
                stat = str(sub_at_stage.iloc[-1]['סטטוס']).strip() if not sub_at_stage.empty else ""

                is_overdue = False
                row_c = df_conf[df_conf['שלב'].str.strip() == s]
                due_s = str(row_c['תאריך יעד'].iloc[0]) if not row_c.empty else ""
                if due_s and due_s != "nan" and stat != "מאושר" and stat != "הוגש":
                    try:
                        if datetime.now() > pd.to_datetime(due_s, dayfirst=True):
                            is_overdue = True
                    except:
                        pass

                icon = "✅" if stat == "מאושר" else ("❌" if stat == "לתיקון" else ("⏳" if stat == "הוגש" else "⚪"))
                if is_overdue:
                    st.markdown(f'<span class="overdue-text">⏰ {s} (באיחור!)</span>', unsafe_allow_html=True)
                else:
                    st.write(f"{icon} {s}")

    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה למורה")
        t_map, t_approve, t_config, t_studs = st.tabs(["🗺️ מפת כיתה", "✅ אישור והיסטוריה", "⚙️ הגדרות", "👥 תלמידים"])

        with t_config:
            st.subheader("⚙️ עריכת שלבים ותאריכי יעד")
            edited_conf = st.data_editor(df_conf, num_rows="dynamic", key="teacher_conf_editor")
            if st.button("💾 שמור הגדרות לגוגל שיטס"):
                if safe_update("config", edited_conf):
                    st.success("ההגדרות נשמרו בהצלחה!")
                    st.rerun()

        with t_approve:
            st.subheader("📥 הגשות הממתינות לבדיקה")
            pending = df_subs[df_subs['סטטוס'].str.strip() == 'הוגש']
            if pending.empty:
                st.info("אין הגשות חדשות כרגע.")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"🆕 {row['שם התלמיד']} - {row['שלב']}"):
                        st.write(f"**תיאור:** {row['תוכן']}")
                        if row['קישור']: st.link_button("🔗 פתח קישור לתוצר", row['קישור'])
                        c1, c2 = st.columns(2)
                        if c1.button("אשר ✅", key=f"app_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "מאושר"
                            if safe_update("Form Responses 1", df_subs): st.rerun()
                        if c2.button("לתיקון ❌", key=f"rej_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "לתיקון"
                            if safe_update("Form Responses 1", df_subs): st.rerun()

        with t_map:
            st.subheader("🗺️ תמונת מצב כיתתית")
            if not df_stud.empty:
                map_data = []
                for _, sr in df_stud.iterrows():
                    sid = normalize_id(sr.iloc[0])
                    rd = {"תלמיד": sr.iloc[1], "כיתה": sr.iloc[2] if len(sr) > 2 else "כללי"}
                    for s in all_stages:
                        st_s = df_subs[
                            (df_subs['תעודת זהות'].apply(normalize_id) == sid) & (df_subs['שלב'].str.strip() == s)]
                        ls = str(st_s.iloc[-1]['סטטוס']).strip() if not st_s.empty else "⚪"
                        rd[s] = "✅" if ls == "מאושר" else ("⏳" if ls == "הוגש" else ("❌" if ls == "לתיקון" else "⚪"))
                    map_data.append(rd)
                st.dataframe(pd.DataFrame(map_data), use_container_width=True, hide_index=True)

        with t_studs:
            st.subheader("👥 ניהול רשימת תלמידים")
            up_f = st.file_uploader("מיזוג קובץ אקסל/CSV", type=["xlsx", "csv"])
            if up_f:
                new_d = pd.read_excel(up_f) if up_f.name.endswith('.xlsx') else pd.read_csv(up_f)
                if st.button("🚀 בצע מיזוג רשימות"):
                    new_d.columns = ["תעודת זהות", "שם התלמיד", "כיתה"][:len(new_d.columns)]
                    new_d["תעודת זהות"] = new_d["תעודת זהות"].apply(normalize_id)
                    merged = pd.concat([df_stud, new_d]).drop_duplicates(subset=["תעודת זהות"], keep='last')
                    if safe_update("students", merged): st.rerun()

            edited_studs = st.data_editor(df_stud, num_rows="dynamic", key="teacher_stud_editor")
            if st.button("💾 שמור שינויים ידניים ברשימה"):
                if safe_update("students", edited_studs): st.rerun()

    else:  # --- ממשק תלמיד ---
        my_id = normalize_id(st.session_state['id'])
        my_subs = df_subs[df_subs['תעודת זהות'].apply(normalize_id) == my_id]

        curr_stage, curr_stat = None, ""
        for s in all_stages:
            sub_s = my_subs[my_subs['שלב'].str.strip() == s]
            ls = str(sub_s.iloc[-1]['סטטוס']).strip() if not sub_s.empty else ""
            if ls != "מאושר":
                curr_stage, curr_stat = s, ls;
                break

        st.title(f"שלום {st.session_state['name']}")

        if curr_stage:
            row_c = df_conf[df_conf['שלב'].str.strip() == curr_stage]
            due_s = str(row_c['תאריך יעד'].iloc[0]) if not row_c.empty else ""
            if due_s and due_s != "nan" and curr_stat != "הוגש":
                try:
                    if datetime.now() > pd.to_datetime(due_s, dayfirst=True):
                        st.markdown(
                            f'<div class="overdue-box">⚠️ שים לב: עברת את תאריך היעד להגשת שלב זה ({due_s})!</div>',
                            unsafe_allow_html=True)
                except:
                    pass

            if curr_stat == "לתיקון":
                st.error(f"❌ המורה ביקש/ה תיקון בשלב: {curr_stage}")
            elif curr_stat == "הוגש":
                st.info(f"⏳ שלב {curr_stage} נשלח בהצלחה וממתין לבדיקת המורה.")
            else:
                st.subheader(f"🚀 השלב הבא שלך: {curr_stage}")
                with st.form("student_sub_form"):
                    p_name = st.text_input("שם הפרויקט שלך:")
                    link = st.text_input("קישור לתוצר (Google Drive, GitHub וכו'):")
                    desc = st.text_area("תאר מה ביצעת בשלב זה:")
                    if st.form_submit_button("🚀 שלח הגשה"):
                        is_first = (curr_stage == all_stages[0])
                        if not p_name or not desc:
                            st.error("נא למלא את שם הפרויקט ותיאור הביצוע.")
                        elif not is_first and not link:
                            st.error("חובה לצרף קישור לתוצר החל משלב זה!")
                        else:
                            new_r = {"Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "תעודת זהות": my_id,
                                     "שם התלמיד": st.session_state['name'], "שלב": curr_stage, "שם הפרויקט": p_name,
                                     "תוכן": desc, "קישור": link, "סטטוס": "הוגש"}
                            if safe_update("Form Responses 1", pd.concat([df_subs, pd.DataFrame([new_r])])):
                                st.success("הגשתך התקבלה!");
                                time.sleep(1);
                                st.rerun()
        else:
            st.success("כל הכבוד! סיימת את כל שלבי הפרויקט בהצלחה! 🎉")
            st.balloons()