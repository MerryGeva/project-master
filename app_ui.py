import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime

# --- 1. הגדרות RTL ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown(
    """<style>.stApp { direction: rtl; text-align: right; } .status-red { color: #ff4b4b; font-weight: bold; } .link-box { background-color: #e1f5fe; padding: 15px; border-radius: 5px; border-right: 5px solid #03a9f4; margin: 10px 0; } div[data-testid="stDataFrame"] { direction: rtl; }</style>""",
    unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)


# פונקציית טעינה עם "ניסיון חוזר" (Retry)
@st.cache_data(ttl=10)  # העלאת ה-TTL ל-10 שניות כדי לחסוך בבקשות לגוגל
def load_all_data():
    for attempt in range(3):  # ינסה 3 פעמים לפני שיוותר
        try:
            subs = conn.read(worksheet="Form Responses 1", ttl=0).fillna("")
            studs = conn.read(worksheet="students", ttl=0).fillna("")
            conf = conn.read(worksheet="config", ttl=0).fillna("")

            subs.columns = [str(c).strip() for c in subs.columns]
            studs.columns = [str(c).strip() for c in studs.columns]
            conf.columns = [str(c).strip() for c in conf.columns]

            critical_cols = ["Timestamp", "תעודת זהות", "שם התלמיד", "שלב", "שם הפרויקט", "תוכן", "קישור", "סטטוס"]
            for col in critical_cols:
                if col not in subs.columns: subs[col] = ""

            return subs, studs, conf, True
        except Exception:
            time.sleep(2)  # ימתין 2 שניות בין ניסיון לניסיון
            continue
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False


df_subs, df_stud, df_conf, success = load_all_data()

if not success:
    st.warning("⚠️ גוגל קצת עמוס כרגע. אנא המתינו 10 שניות ורעננו את הדף פעם אחת בלבד.")
    st.stop()

# --- המשך הקוד (התחברות וממשק) ---
# (אותו קוד מהפעם הקודמת, רק שהטעינה למעלה הרבה יותר חכמה עכשיו)

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

if not st.session_state['logged_in']:
    st.title("🎓 Project Master")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])
    with t1:
        sid_input = st.text_input("תעודת זהות:").strip()
        if st.button("התחבר"):
            user_id_clean = ''.join(filter(str.isdigit, sid_input)).lstrip('0')
            found_user = None
            if not df_stud.empty:
                for _, row in df_stud.iterrows():
                    id_val = ''.join(filter(str.isdigit, str(row.iloc[0]))).lstrip('0')
                    if id_val == user_id_clean:
                        found_user = row
                        break
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

elif st.session_state['role'] == 'teacher':
    with st.sidebar:
        st.title(f"שלום, {st.session_state['name']}")
        if st.button("🚪 התנתק"):
            st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})
            st.rerun()

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
                    st.write(f"**פרויקט:** {row['שם הפרויקט']}")
                    st.write(f"**תיאור:** {row['תוכן']}")
                    if str(row['קישור']).strip():
                        st.markdown(f"🔗 <a href='{row['קישור']}' target='_blank'>צפה בתוצר</a>", unsafe_allow_html=True)
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

    with t_map:
        if not df_stud.empty:
            all_stages = df_conf.iloc[:, 0].dropna().tolist() if not df_conf.empty else ["שלב 1"]
            map_list = []
            for _, s_row in df_stud.iterrows():
                sid = ''.join(filter(str.isdigit, str(s_row.iloc[0]))).lstrip('0')
                row_map = {"תלמיד": s_row.iloc[1]}
                for stage in all_stages:
                    sub = df_subs[(df_subs['תעודת זהות'].astype(str).str.contains(sid)) & (df_subs['שלב'] == stage)]
                    status = sub.iloc[-1]['סטטוס'] if not sub.empty else "⚪"
                    row_map[stage] = "✅" if status == "מאושר" else ("⏳" if status == "הוגש" else "⚪")
                map_list.append(row_map)
            st.table(pd.DataFrame(map_list))

    with t_studs:
        edited_s = st.data_editor(df_stud, num_rows="dynamic", key="s_edit")
        if st.button("💾 שמור תלמידים"):
            conn.update(worksheet="students", data=edited_s);
            st.cache_data.clear();
            st.rerun()

    with t_config:
        edited_c = st.data_editor(df_conf, num_rows="dynamic", key="c_edit")
        if st.button("💾 שמור הגדרות"):
            conn.update(worksheet="config", data=edited_c);
            st.cache_data.clear();
            st.rerun()