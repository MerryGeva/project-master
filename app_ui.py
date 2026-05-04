import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import io
from datetime import datetime
import time

# --- הגדרות קבצים ---
DB_FILE = "submissions.csv"
STUDENTS_FILE = "students_list.csv"
CONFIG_FILE = "system_config.csv"
TEACHER_PASSWORD = "123"

# --- הגדרות דף ---
st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown("<style>.stApp { direction: rtl; text-align: right; } div[st-decorator='sidebar'] { direction: rtl; }</style>", unsafe_allow_html=True)

# --- חיבור ל-Google Sheets ---
# החלפת שורת החיבור
conn = st.connection("gsheets", type=GSheetsConnection)

# הוספת כפתור "ריענון כוחני" מתחת ל-DEBUG
if st.sidebar.button("סינכרון מחדש מול גוגל"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()
    # זה ידפיס לך באפליקציה לאיזה גיליון היא מחוברת
if st.sidebar.checkbox("הצג מזהה גיליון (Debug)"):
    st.sidebar.write(f"מחובר לגיליון: {st.secrets['connections']['gsheets']['spreadsheet']}")
# זה ידפיס לך באפליקציה את השם של הקובץ שהיא מזהה
try:
    metadata = conn.inspect()
    st.write(f"DEBUG: שם הקובץ המזוהה: {metadata.get('title')}")
except:
    st.write("DEBUG: לא מצליח לקרוא מטא-דאטה")

def get_data(worksheet_name, expected_cols):
    try:
        # ttl=0 מוודא שאנחנו תמיד קוראים נתונים טריים ולא מהזיכרון
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=expected_cols)
        return df.astype(str)
    except:
        return pd.DataFrame(columns=expected_cols)


def update_sheets(df, worksheet_name):
    try:
        # ניקוי זיכרון כדי לראות נתונים טריים
        st.cache_data.clear()

        # המרה לטקסט ועדכון
        df_to_save = pd.DataFrame(df).astype(str)
        conn.update(worksheet=worksheet_name, data=df_to_save)

        st.success(f"✅ הצלחתי לעדכן את לשונית {worksheet_name}!")
        st.balloons()  # זה ייתן סימן ויזואלי חזק שהפקודה עברה
    except Exception as e:
        st.error(f"❌ אופס! השמירה נכשלה. הסיבה: {e}")

# --- טעינת נתונים (מגוגל במקום מ-CSV) ---
config_df = get_data("config", ["שלב", "תאריך יעד"])
if config_df.empty:
    config_df = pd.DataFrame([
        {"שלב": "1. בחירת נושא", "תאריך יעד": "2026-03-01"},
        {"שלב": "2. אפיון", "תאריך יעד": "2026-03-15"}
    ])
all_stages = config_df['שלב'].tolist()

subs_df = get_data("submissions", ["זמן הגשה", 'ת"ז', "סיסמה", "שם התלמיד", "שלב", "שם הפרויקט", "תיאור/לינק", "סטטוס", "הערות מורה", "סטטוס זמן"])
students_df = get_data("students", ["ת\"ז", "שם מלא"])
# --- פונקציות נתונים ---
def load_data(file, default_cols):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file, dtype={'ת"ז': str}).fillna("")
            return df
        except:
            return pd.DataFrame(columns=default_cols)
    return pd.DataFrame(columns=default_cols)


def save_data(df, file):
    # שומר לקובץ המקומי (גיבוי)
    df.to_csv(file, index=False, encoding='utf-8-sig')

    # שומר לגוגל שייטס - זה החלק שחסר לך!
    if file == STUDENTS_FILE:
        update_sheets(df, "students")
    elif file == DB_FILE:
        update_sheets(df, "submissions")
    elif file == CONFIG_FILE:
        update_sheets(df, "config")
def get_config():
    df = load_data(CONFIG_FILE, ["שלב", "תאריך יעד"])
    if df.empty:
        default_stages = [
            {"שלב": "1. בחירת נושא", "תאריך יעד": "2026-03-01"},
            {"שלב": "2. אפיון", "תאריך יעד": "2026-03-15"},
            {"שלב": "3. ניתוח", "תאריך יעד": "2026-04-01"},
            {"שלב": "4. עיצוב", "תאריך יעד": "2026-04-15"},
            {"שלב": "5. קידוד", "תאריך יעד": "2026-05-15"},
            {"שלב": "6. הגשת 80%", "תאריך יעד": "2026-06-01"},
            {"שלב": "7. הגשת 100%", "תאריך יעד": "2026-06-15"}
        ]
        df = pd.DataFrame(default_stages)
        save_data(df, CONFIG_FILE)
    return df


def is_stage_approved(df, student_id, stage_name, all_stages):
    try:
        current_idx = all_stages.index(stage_name)
        if current_idx == 0: return True
        prev_stage = all_stages[current_idx - 1]
        approved = df[(df['ת"ז'] == student_id) & (df['שלב'] == prev_stage) & (df['סטטוס'] == "✅ מאושר")]
        return not approved.empty
    except:
        return False


# --- הגדרות דף ---
#st.set_page_config(page_title="Project Master Pro", layout="wide")
st.markdown(
    "<style>.stApp { direction: rtl; text-align: right; } div[st-decorator='sidebar'] { direction: rtl; }</style>",
    unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'id': None, 'pwd': None})

# --- מסך כניסה ---
if not st.session_state['logged_in']:
    st.title("🎓 Project Master - כניסה")
    tab1, tab2 = st.tabs(["🔑 כניסת תלמיד", "👨‍🏫 כניסת מורה"])

    with tab1:
        sid = st.text_input("תעודת זהות (9 ספרות):", max_chars=9)
        spwd = st.text_input("סיסמה לשמירה/כניסה:", type="password")
        if st.button("התחבר כתלמיד"):
            students_list = load_data(STUDENTS_FILE, ["ת\"ז", "שם מלא"])
            if sid in students_list['ת"ז'].values:
                st.session_state.update({'logged_in': True, 'role': 'student', 'id': sid, 'pwd': spwd})
                st.rerun()
            else:
                st.error("אינך מופיע ברשימת התלמידים. פנה למורה.")

    with tab2:
        mpwd = st.text_input("סיסמת מורה:", type="password")
        if st.button("התחבר כמורה"):
            if mpwd == TEACHER_PASSWORD:
                st.session_state.update({'logged_in': True, 'role': 'teacher', 'id': 'Teacher'})
                st.rerun()
            else:
                st.error("סיסמה שגויה")

else:
    config_df = get_config()
    all_stages = config_df['שלב'].tolist()
    subs_df = load_data(DB_FILE,
                        ["זמן הגשה", 'ת"ז', "סיסמה", "שם התלמיד", "שלב", "שם הפרויקט", "תיאור/לינק", "טכנולוגיות",
                         "סטטוס", "הערות מורה", "סטטוס זמן"])
    students_df = load_data(STUDENTS_FILE, ["ת\"ז", "שם מלא"])

    # --- ממשק מורה ---
    if st.session_state['role'] == 'teacher':
        st.sidebar.title("👨‍🏫 תפריט מורה")
        menu = st.sidebar.radio("ניווט:", ["דו\"ח התקדמות כיתתי", "בדיקת הגשות", "ניהול תלמידים", "הגדרות שלבים"])

        if menu == "הגדרות שלבים":
            st.header("⚙️ הגדרות שלבי הפרויקט ותאריכי יעד")
            edited_config = st.data_editor(config_df, num_rows="dynamic", width='stretch')
            if st.button("שמור שינויים"):
                save_data(edited_config, CONFIG_FILE)
                st.success("הגדרות המערכת עודכנו!")
                st.rerun()

        elif menu == "ניהול תלמידים":
            st.header("👥 ניהול רשימת כיתה")

            # העלאת קובץ
            st.subheader("📥 עדכון מרשימה (Excel/CSV)")
            uploaded_file = st.file_uploader("העלי קובץ עם עמודות 'ת\"ז' ו-'שם מלא'", type=['csv', 'xlsx'])
            if uploaded_file:
                try:
                    new_students = pd.read_csv(uploaded_file, dtype={'ת"ז': str}) if uploaded_file.name.endswith(
                        '.csv') else pd.read_excel(uploaded_file, dtype={'ת"ז': str})
                    if 'ת"ז' in new_students.columns and 'שם מלא' in new_students.columns:
                        if st.button("✅ אשר והחלף רשימה קיימת"):
                            save_data(new_students[['ת"ז', 'שם מלא']], STUDENTS_FILE)
                            st.success("הרשימה עודכנה בהצלחה!")
                            time.sleep(1);
                            st.rerun()
                    else:
                        st.error("חסרות עמודות 'ת\"ז' או 'שם מלא'")
                except Exception as e:
                    st.error(f"שגיאה: {e}")

            st.divider()
            # עריכה ידנית
            st.subheader("📝 עריכה ידנית")
            edited_s = st.data_editor(students_df, num_rows="dynamic", width='stretch')
            if st.button("שמור שינויים ידניים"):
                save_data(edited_s, STUDENTS_FILE)
                st.success("הרשימה עודכנה!")
                st.rerun()


        elif menu == "דו\"ח התקדמות כיתתי":

            st.header("📊 מטריצת מעקב כיתתית")

            if not students_df.empty:

                report = []

                for _, s in students_df.iterrows():

                    row = {"שם": s['שם מלא'], "ת\"ז": s['ת"ז']}

                    for stg in all_stages:
                        sub = subs_df[(subs_df['ת"ז'] == s['ת"ז']) & (subs_df['שלב'] == stg)]

                        row[stg] = sub.iloc[-1]['סטטוס'] if not sub.empty else "❌ לא הוגש"

                    report.append(row)

                # יצירת ה-DataFrame

                df_report = pd.DataFrame(report)


                # פונקציית הצביעה

                def color_status(val):

                    if val == "❌ לא הוגש": return 'background-color: #ffcccc'

                    if val == "✅ מאושר": return 'background-color: #ccffcc'

                    if val == "ממתין לבדיקה": return 'background-color: #ffe6cc'

                    return ''


                # תיקון השגיאה: שימוש ב-map במקום applymap (מתאים לגרסאות חדשות)

                try:

                    styled_df = df_report.style.map(color_status)

                except:

                    styled_df = df_report.style.applymap(color_status)

                st.dataframe(styled_df, width='stretch')

            else:

                st.warning("אין תלמידים רשומים בגיליון Google Sheets.")
        elif menu == "בדיקת הגשות":
            st.header("📥 בדיקת עבודות חדשות")

            # --- התיקון כאן: סינון הגשות רק לתלמידים שקיימים ברשימה הנוכחית ---
            valid_ids = students_df['ת"ז'].tolist()
            pending = subs_df[(subs_df['סטטוס'] == "ממתין לבדיקה") & (subs_df['ת"ז'].isin(valid_ids))]

            if not pending.empty:
                sel = st.selectbox("בחר הגשה:", [f"{i}: {r['שם התלמיד']} - {r['שלב']}" for i, r in pending.iterrows()])
                idx = int(sel.split(":")[0])
                row = subs_df.loc[idx]
                st.info(f"תלמיד: {row['שם התלמיד']} | פרויקט: {row['שם הפרויקט']}")
                st.markdown(f"**תוכן ההגשה:**\n{row['תיאור/לינק']}")
                res = st.radio("החלטה:", ["✅ מאושר", "❌ נדרש תיקון"], horizontal=True)
                feedback = st.text_area("הערות ומשוב לתלמיד:")
                if st.button("שמור בדיקה"):
                    subs_df.at[idx, 'סטטוס'] = res
                    subs_df.at[idx, 'הערות מורה'] = feedback
                    save_data(subs_df, DB_FILE)
                    st.success("הבדיקה נשמרה!")
                    time.sleep(1);
                    st.rerun()
            else:
                st.success("אין הגשות הממתינות לבדיקה עבור התלמידים ברשימה הנוכחית.")

    # --- ממשק תלמיד ---
    elif st.session_state['role'] == 'student':
        s_id = st.session_state['id']
        s_name_full = students_df[students_df['ת"ז'] == s_id]['שם מלא'].iloc[0] if s_id in students_df[
            'ת"ז'].values else s_id
        student_data = subs_df[subs_df['ת"ז'] == s_id]

        st.sidebar.title(f"שלום {s_name_full}")
        st.sidebar.subheader("📍 מצב התקדמות")
        for s_name in all_stages:
            icon = "⚪"
            status_info = student_data[student_data['שלב'] == s_name]
            if not status_info.empty:
                last_s = status_info.iloc[-1]['סטטוס']
                if last_s == "✅ מאושר":
                    icon = "✅"
                elif last_s == "ממתין לבדיקה":
                    icon = "⏳"
                elif last_s == "❌ נדרש תיקון":
                    icon = "❌"
            st.sidebar.write(f"{icon} {s_name}")

        st.header("הגשת תוצרים")
        approved_stages = student_data[student_data['סטטוס'] == "✅ מאושר"]['שלב'].tolist()
        start_idx = len(approved_stages) if len(approved_stages) < len(all_stages) else len(all_stages) - 1
        stage = st.selectbox("בחר שלב להגשה:", all_stages, index=start_idx)

        current_idx = all_stages.index(stage)
        requires_link = current_idx >= 1

        deadline_val = config_df[config_df['שלב'] == stage]['תאריך יעד'].iloc[0]
        st.info(f"📅 תאריך יעד להגשה: {deadline_val}")

        current_stage_info = student_data[student_data['שלב'] == stage]
        if not current_stage_info.empty:
            last_entry = current_stage_info.iloc[-1]
            if last_entry['סטטוס'] == "❌ נדרש תיקון":
                st.error(f"⚠️ נדרש תיקון: {last_entry['הערות מורה']}")
            elif last_entry['סטטוס'] == "✅ מאושר":
                st.success("✅ השלב הזה מאושר!")

        if not is_stage_approved(subs_df, s_id, stage, all_stages):
            st.warning("עליך להמתין לאישור השלב הקודם לפני שתוכל להגיש שלב זה.")
        else:
            def_p_name = student_data.iloc[-1]['שם הפרויקט'] if not student_data.empty else ""
            prev_link, prev_info = "", ""
            if not current_stage_info.empty:
                full_text = current_stage_info.iloc[-1]['תיאור/לינק']
                if "LINK: " in full_text:
                    parts = full_text.split("\nINFO: ")
                    prev_link = parts[0].replace("LINK: ", "")
                    prev_info = parts[1] if len(parts) > 1 else ""
                else:
                    prev_info = full_text

            p_name = st.text_input("שם הפרויקט:", value=def_p_name)
            link_label = "🔗 קישור לתוצר (חובה):" if requires_link else "🔗 קישור (אופציונלי):"
            doc_link = st.text_input(link_label, value=prev_link)
            content = st.text_area("תיאור הביצוע / הערות:", value=prev_info)

            if st.button("🚀 שלח הגשה", width='stretch'):
                if not p_name.strip():
                    st.error("❌ חובה להזין את שם הפרויקט.")
                elif requires_link and (not doc_link.strip() or "http" not in doc_link):
                    st.error("❌ חובה להזין קישור תקין.")
                elif not content.strip():
                    st.error("❌ חובה להוסיף תיאור ביצוע.")
                else:
                    final_content = f"LINK: {doc_link}\nINFO: {content}"
                    now = datetime.now()
                    d_obj = datetime.strptime(deadline_val, "%Y-%m-%d")
                    t_stat = "✅ בזמן" if now <= d_obj else "⚠️ איחור"

                    new_row = {
                        "זמן הגשה": now.strftime("%Y-%m-%d %H:%M"), 'ת"ז': s_id, "סיסמה": st.session_state['pwd'],
                        "שם התלמיד": s_name_full, "שלב": stage, "שם הפרויקט": p_name,
                        "תיאור/לינק": final_content, "סטטוס": "ממתין לבדיקה", "סטטוס זמן": t_stat
                    }
                    mask = (subs_df['ת"ז'] == s_id) & (subs_df['שלב'] == stage)
                    if not subs_df[mask].empty:
                        for k, v in new_row.items(): subs_df.loc[mask, k] = v
                    else:
                        subs_df = pd.concat([subs_df, pd.DataFrame([new_row])], ignore_index=True)

                    save_data(subs_df, DB_FILE)
                    st.success(f"נשלח! ({t_stat})")
                    st.balloons();
                    time.sleep(1.5);
                    st.rerun()

    if st.sidebar.button("🚪 התנתק"):
        st.session_state.clear();
        st.rerun()