import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import re

# --- 1. הגדרות RTL ועיצוב ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    h1, h2, h3, h4, h5, h6, p, span, label { text-align: right !important; direction: rtl !important; }
    .overdue-text { color: #FF0000 !important; font-weight: bold; background-color: #ffe6e6; padding: 2px 5px; border-radius: 4px; }
    .overdue-box { color: white; background-color: #ff4b4b; padding: 15px; border-radius: 8px; font-weight: bold; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר ---
conn = st.connection("gsheets", type=GSheetsConnection)


def normalize_id(v):
    if pd.isna(v) or v == "": return ""
    s = ''.join(filter(str.isdigit, str(v).split('.')[0]))
    return s.zfill(9) if s else ""


def clean_and_parse_date(d):
    """מנקה תאריכים משיבושי פורמט של גוגל שיטס"""
    if pd.isna(d) or d == "": return None
    try:
        # אם זה כבר אובייקט תאריך
        if isinstance(d, (datetime, pd.Timestamp)): return d.to_pydatetime().replace(tzinfo=None)
        # ניקוי תווים שהם לא מספרים או סלאש
        d_clean = re.sub(r'[^0-9/.-]', '', str(d)).strip()
        # ניסיון המרה ידני
        for fmt in ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"]:
            try:
                return datetime.strptime(d_clean, fmt)
            except:
                continue
    except:
        pass
    return None


def load_all_data():
    try:
        # טעינה ללא Cache אגרסיבי כדי למנוע תקיעה
        subs = conn.read(worksheet="Form Responses 1", ttl="1s").fillna("")
        studs = conn.read(worksheet="students", ttl="1s").fillna("")
        conf = conn.read(worksheet="config", ttl="1s").fillna("")

        for df in [subs, studs, conf]:
            df.columns = [str(c).strip() for c in df.columns]

        if "תאריך יעד" not in conf.columns: conf["תאריך יעד"] = ""
        return subs, studs, conf, True
    except Exception as e:
        st.error(f"שגיאה בחיבור לנתונים: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False


df_subs, df_stud, df_conf, success = load_all_data()


def safe_update(ws, data):
    try:
        data = data.loc[:, ~data.columns.str.contains('^Unnamed')]
        conn.update(worksheet=ws, data=data)
        st.cache_data.clear()
        time.sleep(1)
        return True
    except Exception as e:
        st.error(f"שגיאה בעדכון: {e}")
        return False


# --- 3. לוגיקת כניסה ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])
    with t1:
        sid_input = st.text_input("תעודת זהות:")
        if st.button("התחבר"):
            u_norm = normalize_id(sid_input)
            found = df_stud[df_stud.iloc[:, 0].apply(normalize_id) == u_norm] if not df_stud.empty else None
            if found is not None and not found.empty:
                st.session_state.update(
                    {'logged_in': True, 'role': 'student', 'id': u_norm, 'name': str(found.iloc[0, 1])})
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
    all_stages = df_conf["שלב"].dropna().astype(str).str.strip().tolist() if not df_conf.empty else ["שלב 1"]

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

            now = datetime.now()
            for s in all_stages:
                sub_at_stage = my_s[my_s['שלב'].str.strip() == s]
                stat = str(sub_at_stage.iloc[-1]['סטטוס']).strip() if not sub_at_stage.empty else ""

                # לוגיקת צביעה
                is_overdue = False
                row_c = df_conf[df_conf['שלב'].str.strip() == s]
                due_dt = clean_and_parse_date(row_c['תאריך יעד'].iloc[0]) if not row_c.empty else None

                if due_dt and now > due_dt and stat not in ["מאושר", "הוגש"]:
                    is_overdue = True

                icon = "✅" if stat == "מאושר" else ("❌" if stat == "לתיקון" else ("⏳" if stat == "הוגש" else "⚪"))
                if is_overdue:
                    st.markdown(f'<p class="overdue-text">⏰ {s} (איחור!)</p>', unsafe_allow_html=True)
                else:
                    st.write(f"{icon} {s}")

    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה")
        t_map, t_approve, t_config, t_studs = st.tabs(["🗺️ מפה", "✅ אישור והיסטוריה", "⚙️ הגדרות", "👥 תלמידים"])

        with t_approve:
            pending = df_subs[df_subs['סטטוס'].str.strip() == 'הוגש']
            if not pending.empty:
                for idx, row in pending.iterrows():
                    with st.expander(f"🆕 {row['שם התלמיד']} - {row['שלב']}"):
                        st.write(f"פרויקט: {row['שם הפרויקט']}\nתוכן: {row['תוכן']}")
                        if row['קישור']: st.link_button("קישור", row['קישור'])
                        c1, c2 = st.columns(2)
                        if c1.button("אשר ✅", key=f"a_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "מאושר"
                            if safe_update("Form Responses 1", df_subs):
                                st.balloons()
                                st.rerun()
                        if c2.button("לתיקון ❌", key=f"r_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "לתיקון"
                            if safe_update("Form Responses 1", df_subs): st.rerun()

            st.markdown("---")
            st.subheader("📜 היסטוריה")
            search = st.text_input("🔎 חיפוש:")
            hist = df_subs.copy()
            if search:
                hist = hist[hist['שם התלמיד'].str.contains(search, na=False) | hist['שם הפרויקט'].str.contains(search,
                                                                                                               na=False)]
            st.dataframe(hist.iloc[::-1], use_container_width=True, hide_index=True)

        with t_config:
            edited_conf = st.data_editor(df_conf, num_rows="dynamic", key="conf_ed")
            if st.button("💾 שמור הגדרות"):
                if safe_update("config", edited_conf): st.rerun()

        with t_map:
            if not df_stud.empty:
                map_d = []
                for _, sr in df_stud.iterrows():
                    sid = normalize_id(sr.iloc[0])
                    rd = {"תלמיד": sr.iloc[1]}
                    for s in all_stages:
                        st_s = df_subs[
                            (df_subs['תעודת זהות'].apply(normalize_id) == sid) & (df_subs['שלב'].str.strip() == s)]
                        ls = str(st_s.iloc[-1]['סטטוס']).strip() if not st_s.empty else "⚪"
                        rd[s] = "✅" if ls == "מאושר" else ("⏳" if ls == "הוגש" else ("❌" if ls == "לתיקון" else "⚪"))
                    map_d.append(rd)
                st.dataframe(pd.DataFrame(map_d), use_container_width=True)

    else:  # --- תלמיד ---
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
            proj_name = my_subs['שם הפרויקט'].iloc[0] if not my_subs.empty and my_subs['שם הפרויקט'].iloc[
                0] != "" else ""

            row_c = df_conf[df_conf['שלב'].str.strip() == curr_stage]
            due_dt = clean_and_parse_date(row_c['תאריך יעד'].iloc[0]) if not row_c.empty else None
            if due_dt and datetime.now() > due_dt and curr_stat != "הוגש":
                st.markdown(f'<div class="overdue-box">⚠️ איחור! תאריך היעד ({due_dt.strftime("%d/%m/%Y")}) עבר.</div>',
                            unsafe_allow_html=True)

            with st.form("sub"):
                if curr_stage == all_stages[0] and proj_name == "":
                    p_input = st.text_input("שם הפרויקט:")
                else:
                    st.write(f"**פרויקט:** {proj_name}")
                    p_input = proj_name

                link = st.text_input("קישור:")
                desc = st.text_area("תיאור:")
                if st.form_submit_button("שלח"):
                    if not p_input or not desc:
                        st.error("מלא שדות חובה")
                    else:
                        new_r = {"Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "תעודת זהות": my_id,
                                 "שם התלמיד": st.session_state['name'], "שלב": curr_stage, "שם הפרויקט": p_input,
                                 "תוכן": desc, "קישור": link, "סטטוס": "הוגש"}
                        if safe_update("Form Responses 1", pd.concat([df_subs, pd.DataFrame([new_r])])):
                            st.balloons()
                            st.rerun()
        else:
            st.success("סיימת הכל! 🎉")
            st.balloons()