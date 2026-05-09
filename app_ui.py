import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# --- הגדרות עיצוב RTL ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .stDataFrame, .stTable { direction: rtl; }
    div[data-testid="stSidebarNav"] { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור לגוגל שייטס ---
# החיבור משתמש ב-Secrets שהגדרת ב-Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=300) # נשמור ל-5 דקות בזיכרון כברירת מחדל
def load_all_data():
    try:
        # קריאה ללא TTL פנימי - ה-Cache העליון מנהל הכל
        subs = conn.read(worksheet="Form Responses 1")
        studs = conn.read(worksheet="students")
        conf = conn.read(worksheet="config")
        return subs.fillna(""), studs.fillna(""), conf.fillna("")
    except Exception as e:
        # במקום לעצור את האפליקציה, נחזיר ערכים ריקים ונדפיס אזהרה
        st.warning("⚠️ גוגל זקוקה למנוחה קצרה (Quota). הנתונים יוצגו מתוך הזיכרון או שיופיעו בעוד רגע...")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# --- ניהול התחברות ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'name': None})

# --- דף כניסה ---
if not st.session_state['logged_in']:
    st.title("🎓 Project Master - מערכת ניהול פרויקטים")
    t1, t2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])

    with t1:
        sid_input = st.text_input("הקלד תעודת זהות:").strip()

        if st.button("התחבר"):
            _, df_stud, _ = load_all_data()

            if not df_stud.empty:
                # פונקציה פנימית לניקוי מוחלט של מחרוזת מכל מה שאינו ספרה
                def clean_val(v):
                    return ''.join(filter(str.isdigit, str(v)))


                # ניקוי הקלט של המשתמש
                user_id_clean = clean_val(sid_input).lstrip('0')

                found_user = None
                # רשימה לדיבג (נציג אותה רק אם לא נמצא)
                all_ids_in_db = []

                for index, row in df_stud.iterrows():
                    db_id_raw = str(row.iloc[0])
                    db_id_clean = clean_val(db_id_raw).lstrip('0')
                    all_ids_in_db.append(db_id_clean)

                    if user_id_clean == db_id_clean and user_id_clean != "":
                        found_user = row
                        break

                if found_user is not None:
                    sname = found_user.iloc[1]
                    st.session_state.update({
                        'logged_in': True,
                        'role': 'student',
                        'id': sid_input,
                        'name': sname
                    })
                    st.success(f"שלום {sname}!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"תעודת זהות '{sid_input}' לא נמצאה.")
                    # זה יעזור לנו להבין מה המערכת "רואה" בגיליון שלך
                    with st.expander("בדיקת סנכרון (למורה בלבד)"):
                        st.write("מה שהקלדת (נקי):", user_id_clean)
                        st.write("מה שיש בגיליון (נקי):", all_ids_in_db)
            else:
                st.error("לא הצלחתי לקרוא נתונים מגיליון students.")
    with t2:
        pwd = st.text_input("סיסמת מורה:", type="password")
        if st.button("כניסה למערכת הניהול"):
            if pwd == "123":  # ניתן לשנות לסיסמה מורכבת יותר
                st.session_state.update({'logged_in': True, 'role': 'teacher'})
                st.rerun()

# --- ממשק לאחר התחברות ---
else:
    st.sidebar.title(f"שלום {st.session_state.get('name', 'המורה')}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

    # טעינת נתונים
    df_subs, df_stud, df_conf = load_all_data()

    # --- ממשק מורה ---
    if st.session_state['role'] == 'teacher':
        st.header("👨‍🏫 לוח בקרה וניהול כיתה")

        tab_map, tab_approve, tab_config, tab_students = st.tabs([
            "🗺️ מפת כיתה", "✅ אישור הגשות", "⚙️ הגדרות שלבים", "👥 ניהול תלמידים"
        ])

        with tab_map:
            st.subheader("מצב התקדמות כללי")
            if not df_stud.empty and not df_conf.empty:
                stages = df_conf.iloc[:, 0].tolist()
                map_list = []
                for _, s_row in df_stud.iterrows():
                    row = {"תלמיד": s_row.iloc[1]}
                    for stage in stages:
                        # חיפוש הגשה אחרונה של התלמיד לשלב זה
                        s_id = str(s_row.iloc[0])
                        sub = df_subs[(df_subs.iloc[:, 1].astype(str) == s_id) & (df_subs.iloc[:, 3] == stage)]
                        if not sub.empty:
                            status = sub.iloc[-1].get('סטטוס', 'הוגש')
                            if status == "מאושר":
                                row[stage] = "✅"
                            elif status == "לתיקון":
                                row[stage] = "❌"
                            else:
                                row[stage] = "⏳"
                        else:
                            row[stage] = "⚪"
                    map_list.append(row)
                st.table(pd.DataFrame(map_list))
                st.caption("✅ מאושר | ⏳ ממתין | ❌ לתיקון | ⚪ טרם הוגש")

        with tab_approve:
            st.subheader("הגשות הממתינות לבדיקה")
            # מציגת הגשות שאין להן סטטוס "מאושר"
            pending = df_subs[df_subs.get('סטטוס', '') != 'מאושר']
            if pending.empty:
                st.success("אין הגשות חדשות לבדיקה!")
            else:
                for idx, row in pending.iterrows():
                    with st.expander(f"הגשה של {row.iloc[2]} - {row.iloc[3]}"):
                        st.write(f"**פרויקט:** {row.iloc[4]}")
                        st.write(f"**תוכן:** {row.iloc[5]}")
                        c1, c2 = st.columns(2)
                        if c1.button("אשר הגשה ✅", key=f"ok_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "מאושר"
                            conn.update(worksheet="Form Responses 1", data=df_subs)
                            if st.button("שמור"):
                                conn.update(worksheet="...", data=...)
                                st.toast("הנתונים נשמרו בהצלחה!") # הודעה קטנה ופחות "כבדה"
                                time.sleep(2)
                                st.cache_data.clear()
                                st.rerun()
                            st.success("עודכן כמאושר!")
                            st.rerun()
                        if c2.button("בקש תיקון ❌", key=f"fix_{idx}"):
                            df_subs.at[idx, 'סטטוס'] = "לתיקון"
                            conn.update(worksheet="Form Responses 1", data=df_subs)
                            if st.button("שמור"):
                                conn.update(worksheet="...", data=...)
                                st.toast("הנתונים נשמרו בהצלחה!") # הודעה קטנה ופחות "כבדה"
                                time.sleep(2)
                                st.cache_data.clear()
                                st.rerun()
                            st.warning("עודכן כנדרש לתיקון")
                            st.rerun()

        with tab_config:
            st.subheader("ניהול שלבים וטכנולוגיות")
            # מגדירים ידנית רק את העמודות שצריכות טקסט
            edited_conf = st.data_editor(
                df_conf,
                num_rows="dynamic",
                key="conf_editor"
            )
            if st.button("שמור הגדרות"):
                conn.update(worksheet="config", data=edited_conf)
                if st.button("שמור"):
                    conn.update(worksheet="...", data=...)
                    st.toast("הנתונים נשמרו בהצלחה!")  # הודעה קטנה ופחות "כבדה"
                    time.sleep(2)
                    st.cache_data.clear()
                    st.rerun()
                st.success("הוגדר בהצלחה!")

        with tab_students:
            st.subheader("ניהול רשימת תלמידים")
            # כאן הכי חשוב שתעודת הזהות תישמר כטקסט
            edited_studs = st.data_editor(
                df_stud,
                num_rows="dynamic",
                key="stud_editor"
            )
            if st.button("עדכן רשימת תלמידים"):
                # הפיכת עמודת תעודת הזהות לטקסט לפני השמירה כדי למנוע בעיות של מספרים
                edited_studs.iloc[:, 0] = edited_studs.iloc[:, 0].astype(str)
                conn.update(worksheet="students", data=edited_studs)
                if st.button("שמור"):
                    conn.update(worksheet="...", data=...)
                    st.toast("הנתונים נשמרו בהצלחה!")  # הודעה קטנה ופחות "כבדה"
                    time.sleep(2)
                    st.cache_data.clear()
                    st.rerun()
                st.success("הרשימה עודכנה!")

    # --- ממשק תלמיד ---
    elif st.session_state['role'] == 'student':
        st.header(f"הגשת פרויקט - {st.session_state['name']}")

        # בניית רשימת טכנולוגיות מה-config
        tech_list = []
        if not df_conf.empty and len(df_conf.columns) >= 3:
            tech_list = [t for t in df_conf.iloc[:, 2].tolist() if str(t).strip() != ""]
        if not tech_list: tech_list = ["Python", "JS", "React", "HTML/CSS"]

        # לוגיקת שלבים וסטטוסים
        all_stages = df_conf.iloc[:, 0].tolist() if not df_conf.empty else ["שלב 1"]
        my_id = st.session_state['id']
        my_subs = df_subs[df_subs.iloc[:, 1].astype(str) == str(my_id)]

        status_dict = {}
        for s in all_stages:
            sub = my_subs[my_subs.iloc[:, 3] == s]
            if not sub.empty:
                status_dict[s] = sub.iloc[-1].get('סטטוס', 'הוגש')
            else:
                status_dict[s] = "לא הוגש"

        # תצוגת סטטוס בסידבר
        st.sidebar.subheader("📍 מצב התקדמות:")
        allowed_stages = []
        found_next = False
        for s in all_stages:
            stat = status_dict[s]
            if stat == "מאושר":
                st.sidebar.write(f"✅ {s}")
                allowed_stages.append(s)
            elif not found_next:
                label = "⏳" if stat == "הוגש" else "⚪"
                st.sidebar.write(f"{label} **{s}**")
                allowed_stages.append(s)
                found_next = True
            else:
                st.sidebar.write(f"🔒 {s}")

        # טופס הגשה
        with st.form("sub_form"):
            col1, col2 = st.columns(2)
            with col1:
                stage = st.selectbox("בחר שלב להגשה:", allowed_stages)
                techs = st.multiselect("טכנולוגיות בשימוש:", tech_list)
            with col2:
                p_name = st.text_input("שם הפרויקט (רק אם השתנה):")
                link = st.text_input("קישור לתוצר (Drive/GitHub):")

            desc = st.text_area("פירוט על תוכן השלב והעבודה שביצעת:", height=150)

            if st.form_submit_button("🚀 שלח הגשה"):
                if desc and p_name:
                    # הוספת שורה חדשה לגיליון ההגשות
                    new_sub = pd.DataFrame([{
                        "Timestamp": time.strftime("%d/%m/%Y %H:%M:%S"),
                        "תעודת זהות": my_id,
                        "שם התלמיד": st.session_state['name'],
                        "שלב": stage,
                        "שם הפרויקט": p_name,
                        "תוכן": f"Techs: {', '.join(techs)} | {desc} | {link}",
                        "סטטוס": "הוגש"
                    }])
                    updated_subs = pd.concat([df_subs, new_sub], ignore_index=True)
                    conn.update(worksheet="Form Responses 1", data=updated_subs)
                    if st.button("שמור"):
                        conn.update(worksheet="...", data=...)
                        st.toast("הנתונים נשמרו בהצלחה!")  # הודעה קטנה ופחות "כבדה"
                        time.sleep(2)
                        st.cache_data.clear()
                        st.rerun()
                    st.success("ההגשה נשלחה בהצלחה!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("נא למלא תיאור ושם פרויקט.")