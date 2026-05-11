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
    div[data-testid="stDataFrame"] { direction: rtl; }
    .stButton button[kind="secondary"] { color: red; border-color: red; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר וחיבור נתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)


def normalize_id(v):
    if pd.isna(v) or v == "": return ""
    s = str(v).split('.')[0]
    s = ''.join(filter(str.isdigit, s))
    return s.zfill(9) if s else ""


@st.cache_data(ttl=20, show_spinner=False)
def load_all_data():
    try:
        subs = conn.read(worksheet="Form Responses 1", ttl="5s").fillna("")
        studs = conn.read(worksheet="students", ttl="5s").fillna("")
        conf = conn.read(worksheet="config", ttl="5s").fillna("")

        for df in [subs, studs, conf]:
            df.columns = [str(c).strip() for c in df.columns]

        critical_cols = ["Timestamp", "תעודת זהות", "שם התלמיד", "שלב", "שם הפרויקט", "תוכן", "קישור", "סטטוס"]
        for col in critical_cols:
            if col not in subs.columns: subs[col] = ""

        subs['סטטוס'] = subs['סטטוס'].astype(str)
        subs['שלב'] = subs['שלב'].astype(str)
        subs['קישור'] = subs['קישור'].astype(str)
        return subs, studs, conf, True
    except Exception as e:
        if "429" in str(e): st.cache_data.clear()
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False


df_subs, df_stud, df_conf, success = load_all_data()


def safe_update(ws, data):
    try:
        conn.update(worksheet=ws, data=data)
        st.cache_data.clear()
        time.sleep(1)
        return True
    except:
        st.error("שגיאה בעדכון. המתינו דקה ונסו שוב.")
        return False


if not success and df_subs.empty:
    st.warning("המערכת בעומס זמני. אנא המתינו 30 שניות ורעננו.")
    st.stop()

all_stages = df_conf["שלב"].dropna().astype(
    str).str.strip().tolist() if not df_conf.empty and "שלב" in df_conf.columns else ["שלב 1"]
tech_options = df_conf[
    "טכנולוגיות"].dropna().unique().tolist() if not df_conf.empty and "טכנולוגיות" in df_conf.columns else ["Python"]

# --- 3. ניהול כניסה ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None, 'class': None})

if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])
    with t1:
        sid_input = st.text_input("תעודת זהות:", key="login_id").strip()
        if st.button("התחבר"):
            u_norm = normalize_id(sid_input)
            found_user = None
            if not df_stud.empty:
                for _, row in df_stud.iterrows():
                    if normalize_id(row.iloc[0]) == u_norm and u_norm != "":
                        found_user = row;
                        break
            if found_user is not None:
                st.session_state.update(
                    {'logged_in': True, 'role': 'student', 'id': u_norm, 'name': str(found_user.iloc[1]),
                     'class': str(found_user.iloc[2]) if len(found_user) > 2 else "כללי"})
                st.rerun()
            else:
                st.error("תעודת זהות לא נמצאה.")
    with t2:
        pwd = st.text_input("סיסמת מורה:", type="password", key="login_pw")
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
                stat = str(sub_at_stage.iloc[-1]['סטטוס']).strip() if not sub_at_stage.empty else ""
                icon = "✅" if stat == "מאושר" else ("❌" if stat == "לתיקון" else ("⏳" if stat == "הוגש" else "⚪"))
                st.write(f"{icon} {s}")

    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה למורה")
        t_map, t_approve, t_config, t_studs = st.tabs(["🗺️ מפת כיתה", "✅ אישור והיסטוריה", "⚙️ הגדרות", "👥 תלמידים"])

        with t_approve:
            st.subheader("📥 הגשות חדשות לבדיקה")
            pending = df_subs[df_subs['סטטוס'].str.strip() == 'הוגש']
            if pending.empty:
                st.info("אין הגשות חדשות הממתינות לאישור.")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"🆕 {row['שם התלמיד']} - {row['שלב']}"):
                        st.write(f"**פרויקט:** {row['שם הפרויקט']}")
                        st.write(f"**תיאור:** {row['תוכן']}")
                        # הוספת כפתור קישור בולט
                        if row['קישור'] and str(row['קישור']).strip() != "":
                            st.link_button("🔗 פתח קישור לתוצר", row['קישור'])
                        else:
                            st.write("*לא צורף קישור להגשה זו*")

                        st.markdown("---")
                        c1, c2 = st.columns(2)
                        if c1.button("אשר ✅", key=f"ok_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "מאושר"
                            if safe_update("Form Responses 1", df_subs): st.rerun()
                        if c2.button("לתיקון ❌", key=f"fix_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "לתיקון"
                            if safe_update("Form Responses 1", df_subs): st.rerun()

            st.markdown("---")
            st.subheader("📜 חיפוש וסינון בהיסטוריה")
            col_q, col_s = st.columns([2, 1])
            q = col_q.text_input("🔎 חיפוש (שם תלמיד או פרויקט):")
            s_filter = col_s.selectbox("סנן לפי סטטוס:", ["הכל", "מאושר", "לתיקון", "הוגש"])

            df_hist = df_subs.copy()
            if s_filter != "הכל":
                df_hist = df_hist[df_hist['סטטוס'].str.strip() == s_filter]
            if q:
                df_hist = df_hist[
                    df_hist['שם התלמיד'].str.contains(q, na=False, case=False) | df_hist['שם הפרויקט'].str.contains(q,
                                                                                                                    na=False,
                                                                                                                    case=False)]

            st.dataframe(df_hist.iloc[::-1], use_container_width=True, hide_index=True)

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
                        last_s = str(st_subs.iloc[-1]['סטטוס']).strip() if not st_subs.empty else "⚪"
                        row_m[s] = "✅" if last_s == "מאושר" else (
                            "⏳" if last_s == "הוגש" else ("❌" if last_s == "לתיקון" else "⚪"))
                    map_d.append(row_m)
                st.dataframe(pd.DataFrame(map_d), use_container_width=True, hide_index=True)

        with t_studs:
            st.subheader("👥 ניהול רשימת תלמידים")
            uploaded_file = st.file_uploader("טעינת קובץ למיזוג ת.ז, שם, כיתה)", type=["xlsx", "csv"])
            if uploaded_file:
                new_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(
                    uploaded_file)
                if st.button("🚀 בצע מיזוג (מניעת כפילויות)"):
                    new_df.columns = ["תעודת זהות", "שם התלמיד", "כיתה"][:len(new_df.columns)]
                    new_df["תעודת זהות"] = new_df["תעודת זהות"].apply(normalize_id)

                    current = df_stud.copy()
                    if not current.empty:
                        current.columns = ["תעודת זהות", "שם התלמיד", "כיתה"][:len(current.columns)]
                        current["תעודת זהות"] = current["תעודת זהות"].apply(normalize_id)
                        # מיזוג: החדש דורס את הישן לפי ת"ז
                        merged = pd.concat([current, new_df]).drop_duplicates(subset=["תעודת זהות"], keep='last')
                    else:
                        merged = new_df

                    if safe_update("students", merged):
                        st.success("המיזוג הושלם בהצלחה!")
                        st.rerun()

            st.data_editor(df_stud, num_rows="dynamic", key="ed_s_editor")

        with t_config:
            st.subheader("⚙️ הגדרות פרויקט")
            st.data_editor(df_conf, num_rows="dynamic", key="ed_c_editor")
            if st.button("💾 שמור שלבים וטכנולוגיות"):
                if safe_update("config", st.session_state.ed_c_editor): st.rerun()

            st.markdown("---")
            st.subheader("🚨 אזור מסוכן")
            confirm = st.checkbox("אני מאשר Reset מוחלט (מחיקת תלמידים והגשות)")
            if confirm and st.button("🔥 בצע Reset עכשיו", type="secondary"):
                empty_subs = pd.DataFrame(
                    columns=["Timestamp", "תעודת זהות", "שם התלמיד", "שלב", "שם הפרויקט", "תוכן", "קישור", "סטטוס"])
                empty_studs = pd.DataFrame(columns=["תעודת זהות", "שם התלמיד", "כיתה"])
                conn.update(worksheet="Form Responses 1", data=empty_subs)
                conn.update(worksheet="students", data=empty_studs)
                st.cache_data.clear();
                st.rerun()

    else:  # ממשק תלמיד
        my_id = normalize_id(st.session_state['id'])
        my_subs = df_subs[df_subs['תעודת זהות'].apply(normalize_id) == my_id]
        curr_stage, curr_stat = None, ""
        for s in all_stages:
            sub_at_stage = my_subs[my_subs['שלב'].str.strip() == s]
            if sub_at_stage.empty:
                curr_stage, curr_stat = s, ""; break
            else:
                last_s = str(sub_at_stage.iloc[-1]['סטטוס']).strip()
                if last_s != "מאושר": curr_stage, curr_stat = s, last_s; break

        st.header(f"שלום {st.session_state['name']}")
        if curr_stage is None:
            st.success("🎉 כל הכבוד! סיימת את כל שלבי הפרויקט!")
            st.balloons()
        elif curr_stat == "הוגש":
            st.subheader(f"⏳ שלב נוכחי: {curr_stage}")
            st.info(f"הגשת כבר את השלב הזה. המורה בודק/ת את העבודה שלך.")
        else:
            if curr_stat == "לתיקון":
                st.subheader(f"❌ נדרש תיקון בשלב: {curr_stage}")
                st.warning("המורה ביקש/ה לבצע תיקונים בהגשה האחרונה.")
            else:
                st.subheader(f"🚀 השלב הבא שלך: {curr_stage}")

            with st.form("sub_form"):
                last_p = my_subs.iloc[-1]['שם הפרויקט'] if not my_subs.empty else ""
                p_n = st.text_input("שם פרויקט:", value=last_p) if curr_stage == all_stages[0] else last_p
                link, techs, desc = st.text_input("קישור לתוצר (URL):"), st.multiselect("טכנולוגיות:",
                                                                                        tech_options), st.text_area(
                    "תיאור קצר של מה שביצעת:")
                if st.form_submit_button("🚀 שלח הגשה"):
                    if not p_n or not desc:
                        st.error("נא למלא שם פרויקט ותיאור.")
                    else:
                        new_r = {"Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                 "תעודת זהות": st.session_state['id'], "שם התלמיד": st.session_state['name'],
                                 "שלב": curr_stage, "שם הפרויקט": p_n, "תוכן": f"{', '.join(techs)}\n{desc}",
                                 "קישור": link, "סטטוס": "הוגש"}
                        conn.update(worksheet="Form Responses 1",
                                    data=pd.concat([df_subs, pd.DataFrame([new_r])], ignore_index=True))
                        st.balloons();
                        st.success("הוגש בהצלחה!");
                        st.cache_data.clear()
                        time.sleep(1);
                        st.rerun()