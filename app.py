from datetime import datetime
import json
import sqlite3
import urllib.parse
import streamlit as st

# 📌 إعدادات الصفحة والاتجاه إلى اليمين (RTL)
st.set_page_config(
    page_title="Linguistic Indexer - KSGAAL",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 🧠 Session State التهيئة المبدئية ---
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "show_video" not in st.session_state:
    st.session_state.show_video = False
if "nav_radio" not in st.session_state:
    st.session_state.nav_radio = "الصفحة الرئيسية"

# --- 🎨 CSS Styling: RTL & Dark Navy Sidebar ---
st.markdown(
    """
    <style>
    html, body, .stApp, [data-testid="stSidebar"], [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
    }
    
    ::-webkit-scrollbar:horizontal {
        display: none !important;
        height: 0px !important;
    }

    html, body, [class*="css"], button, input, textarea, div, span, p, h1, h2, h3, h4, h5, h6, label {
        font-family: 'Calibri', 'Segoe UI', sans-serif !important;
        font-weight: normal !important;
        direction: rtl;
        text-align: right;
    }

    .stApp {
        background-color: #01DFD7;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0A192F !important;
        right: 0 !important;
        left: auto !important;
        border-left: 1px solid #1E2D4A !important;
        width: 280px !important;
        min-width: 290px !important;
    }

    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
        text-align: right !important;
    }

    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label {
        font-size: 15px !important;
    }

    [data-testid="stSidebar"] div[data-testid="stMetricValue"] {
        color: #01DFD7 !important;
        font-weight: bold !important;
        font-size: 26px !important;
    }

    [data-testid="stSidebar"] div[data-testid="stMetricLabel"] p {
        font-size: 14px !important;
    }

    [data-testid="stSidebarCollapseButton"], 
    [data-testid="collapsedControl"],
    button[aria-label="Close sidebar"],
    button[aria-label="Open sidebar"] {
        display: none !important;
    }

    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    mark {
        background-color: #FFFF00;
        color: #000000;
        padding: 2px 5px;
        border-radius: 3px;
        font-weight: normal !important;
        font-family: 'Calibri', sans-serif !important;
    }

    div.stButton > button {
        height: 38px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(49, 51, 63, 0.2) !important;
        background-color: #ffffff !important;
    }

    div.stButton > button p {
        font-size: 13.5px !important;
        font-family: 'Calibri', sans-serif !important;
        font-weight: normal !important;
        color: #31333F !important;
    }

    .dict-btn {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 38px !important;
        background-color: #ffffff !important;
        color: #31333F !important;
        border: 1px solid rgba(49, 51, 63, 0.2) !important;
        border-radius: 8px !important;
        text-decoration: none !important;
        font-size: 13.5px !important;
        font-family: 'Calibri', sans-serif !important;
        font-weight: normal !important;
        transition: background-color 0.2s, border-color 0.2s;
        text-align: center !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    
    .dict-btn:hover, .dict-btn:focus, .dict-btn:visited {
        background-color: #f0f2f6 !important;
        border-color: #000000 !important;
        color: #000000 !important;
        text-decoration: none !important;
    }

    .anki-card {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        font-family: 'Calibri', sans-serif !important;
    }

    .anki-card h2 {
        text-align: center !important;
        color: #000000 !important;
        margin: 0 !important;
        font-family: 'Calibri', sans-serif !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

WORDS_LIST = [
    "جامعة", "وجود", "عضو", "ملك", "عامل", "جهة", "علاقة", "حال", "وصل", "أكبر",
    "مجموعة", "دراسة", "مال", "مباراة", "مستوى", "طالب", "ما", "مواطن", "نبي", "دكتور",
    "أمة", "لغة", "نتيجة", "أخير", "أمس", "عاد", "وجه", "مرة", "لاعب", "فعل",
    "اجتماعي", "مدير", "هم", "عمل", "بحث", "الآن", "فترة", "نادي", "دين", "أنا",
    "عندما", "مجال", "بلغ", "مليون", "شخص", "مكان", "وجب", "موقع", "ماء", "تعليم",
    "طفل", "اقتصادي", "باب", "قطاع", "مؤسسة", "هيئة", "آية", "نظر", "سلطة", "رغم",
    "حرب", "كلمة", "جنوب", "اتحاد", "أخذ", "مادة", "داخل", "نائب", "عين", "علم",
    "دعا", "ثالث", "المرأة", "أخ", "مرحلة", "نسبة", "بيان", "بيت", "صحيح", "جهاز",
    "نوع", "عسكري", "أمير", "اعتبر", "أب", "سوق", "بناء", "عالمي", "إذ", "مسؤول",
    "حالي", "مؤتمر", "نظر", "سيد", "زوج", "استطاع", "إجراء", "إنما", "سلام", "دعم",
    "لن", "رأي", "قلب", "مالي", "أدى", "أصل", "صلاة", "لقد", "شهد", "قيادة", "عرب",
    "تحت", "قيمة", "مشكلة"
]


# --- 🗄️ تهيئة قاعدة البيانات والتأكد من توافق الأعمدة ---
def init_db():
    conn = sqlite3.connect("ksgafal_data.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            snippet TEXT,
            video_id TEXT,
            start_time INTEGER,
            target_step INTEGER DEFAULT 0,
            current_step INTEGER DEFAULT 0
        )
    """)

    cursor.execute("PRAGMA table_info(flashcards)")
    columns = [column[1] for column in cursor.fetchall()]

    if "target_step" not in columns:
        cursor.execute("ALTER TABLE flashcards ADD COLUMN target_step INTEGER DEFAULT 0")
    if "current_step" not in columns:
        cursor.execute("ALTER TABLE flashcards ADD COLUMN current_step INTEGER DEFAULT 0")

    conn.commit()
    conn.close()


init_db()


def get_snippet(text, word, window=8):
    words = text.split()
    word_clean = word.strip().lower()

    for i, w in enumerate(words):
        if word_clean in w.lower():
            start = max(0, i - window)
            end = min(len(words), i + window + 1)
            snippet = " ".join(words[start:end])
            return f"...{snippet}..."
    return text


def search_word_in_db(query):
    conn = sqlite3.connect("ksgafal_data.db")
    cursor = conn.cursor()
    query_clean = query.strip()

    cursor.execute(
        "SELECT video_id, title, channel, full_transcript, timestamps_json FROM videos WHERE full_transcript LIKE ?",
        (f"%{query_clean}%",),
    )
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        video_id, title, channel, full_transcript, timestamps_json = row
        try:
            timestamps = json.loads(timestamps_json) if timestamps_json else []
        except json.JSONDecodeError:
            timestamps = []

        matched_timestamps = [
            item.get("start", 0)
            for item in timestamps
            if query_clean.lower() in item.get("word", "").lower()
        ]

        if matched_timestamps:
            snippet = get_snippet(full_transcript, query_clean)
            results.append({
                "video_id": video_id,
                "title": title,
                "channel": channel,
                "first_start": matched_timestamps[0],
                "snippet": snippet,
            })
    return results


def navigate_and_search(selected_word):
    st.session_state.last_query = selected_word
    st.session_state.current_index = 0
    st.session_state.search_results = search_word_in_db(selected_word)
    st.session_state.nav_radio = "الصفحة الرئيسية"


# --- 📇 إدارة البطاقات المبنية على عدد الكلمات ---
def save_to_flashcards(word, snippet, video_id, start_time):
    conn = sqlite3.connect("ksgafal_data.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO flashcards (word, snippet, video_id, start_time, target_step, current_step) VALUES (?, ?, ?, ?, 0, 0)",
            (word, snippet, video_id, start_time),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def get_due_flashcards():
    conn = sqlite3.connect("ksgafal_data.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, word, snippet, video_id, start_time, target_step, current_step FROM flashcards WHERE current_step >= target_step ORDER BY (current_step - target_step) DESC"
    )
    rows = cursor.fetchall()
    
    if not rows:
        cursor.execute(
            "SELECT id, word, snippet, video_id, start_time, target_step, current_step FROM flashcards ORDER BY current_step DESC, id ASC"
        )
        rows = cursor.fetchall()

    conn.close()
    return rows


def get_total_flashcards_count():
    conn = sqlite3.connect("ksgafal_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM flashcards")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def update_flashcard_review(card_id, choice):
    conn = sqlite3.connect("ksgafal_data.db")
    cursor = conn.cursor()

    if choice == "never":
        cursor.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
    else:
        step_delay = 5 if choice == "five" else 10

        cursor.execute("UPDATE flashcards SET current_step = current_step + 1 WHERE id != ?", (card_id,))

        cursor.execute(
            "UPDATE flashcards SET target_step = ?, current_step = 0 WHERE id = ?",
            (step_delay, card_id),
        )

    conn.commit()
    conn.close()


def format_arabic_word_count(count):
    if count == 1:
        return "كلمة واحدة"
    elif count == 2:
        return "كلمتان"
    elif 3 <= count <= 10:
        numbers_map = {
            3: "ثلاث",
            4: "أربع",
            5: "خمس",
            6: "ست",
            7: "سبع",
            8: "ثماني",
            9: "تسع",
            10: "عشر",
        }
        return f"{numbers_map.get(count, count)} كلمات"
    else:
        return f"{count} كلمة"


# --- 📌 القائمة الجانبية ---
with st.sidebar:
    st.markdown(
        "<h3 style='color: #FFFFFF; font-family: Calibri; font-size: 22px;'>📚 الفهرس اللغوي</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color: #A0AEC0; font-size: 13.5px;'>مجمع الملك سلمان العالمي للغة العربية</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    mode = st.radio(
        "التنقل",
        ["الصفحة الرئيسية", "المراجعة", "قائمة الكلمات"],
        key="nav_radio",
    )

    st.markdown("---")

    due_count = len(get_due_flashcards())
    total_count = get_total_flashcards_count()

    st.markdown(
        "<h5 style='color: #FFFFFF; font-family: Calibri; font-size: 17px;'>📊 إحصائيات البطاقات</h5>",
        unsafe_allow_html=True,
    )
    st.metric(label="المستحقة للمراجعة", value=due_count)
    st.metric(label="إجمالي المحفوظات", value=total_count)

    st.markdown("---")
    st.markdown(
        """
        <div style='color: #CBD5E1; font-size: 13px; line-height: 1.6;'>
            <strong>تعليمات المراجعة:</strong><br>
            • يتم تأجير الكلمة بعدد الكلمات المحفوظة بدلاً من الوقت.<br>
            • <b>عدم الظهور:</b> تُحذف الكلمة نهائياً من المراجعة.<br>
            • <b>بعد 5 مرات:</b> تظهر بعد مراجعة 5 كلمات.<br>
            • <b>بعد 10 مرات:</b> تظهر بعد مراجعة 10 كلمات (أو عند إنهاء الكلمات المتاحة).
        </div>
        """,
        unsafe_allow_html=True,
    )


# ================= 1️⃣ وضع الصفحة الرئيسية =================
if mode == "الصفحة الرئيسية":
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        query = st.text_input(
            label="",
            label_visibility="collapsed",
            placeholder="أدخل الكلمة للبحث...",
            value=st.session_state.last_query,
        )
        btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 2])
        with btn_col2:
            search_clicked = st.button("بحث", use_container_width=True)

    st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)

    if search_clicked or (query and query != st.session_state.last_query):
        if query.strip():
            st.session_state.last_query = query
            st.session_state.current_index = 0
            st.session_state.search_results = search_word_in_db(query)

    results = st.session_state.search_results
    current_query = st.session_state.last_query

    if current_query.strip():
        if results:
            total_results = len(results)
            curr_idx = st.session_state.current_index
            res = results[curr_idx]

            v_left, v_center, v_right = st.columns([1, 2, 1])

            with v_center:
                encoded_query = urllib.parse.quote(current_query.strip())
                dict_url = f"https://dictionary.ksaa.gov.sa/result/{encoded_query}"
                st.markdown(
                    f"<a href='{dict_url}' target='_blank' class='dict-btn'>معنى ({current_query}) في معجم الرياض</a>",
                    unsafe_allow_html=True,
                )

                st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

                nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                with nav_col1:
                    if st.button("السابق", use_container_width=True, disabled=(curr_idx == 0)):
                        st.session_state.current_index -= 1
                        st.rerun()

                with nav_col2:
                    st.markdown(
                        f"<h4 style='text-align: center; color: #333333; font-family: Calibri; font-weight: normal; margin-top: 5px;'>مقطع {curr_idx + 1} من {total_results}</h4>",
                        unsafe_allow_html=True,
                    )

                with nav_col3:
                    if st.button("التالي", use_container_width=True, disabled=(curr_idx == total_results - 1)):
                        st.session_state.current_index += 1
                        st.rerun()

                start_seconds = int(res["first_start"])
                youtube_url = f"https://www.youtube.com/watch?v={res['video_id']}&t={start_seconds}s"

                st.video(youtube_url, start_time=start_seconds)

                highlighted_snippet = res["snippet"].replace(
                    current_query, f"<mark>{current_query}</mark>"
                )
                st.markdown(
                    f"<p style='font-size: 19px; color: #000000; text-align: right; font-family: Calibri; font-weight: normal; margin-top: 10px;'>{highlighted_snippet}</p>",
                    unsafe_allow_html=True,
                )

                st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

                if st.button(f"حفظ ({current_query}) للمراجعة", use_container_width=True):
                    added = save_to_flashcards(
                        current_query,
                        res["snippet"],
                        res["video_id"],
                        start_seconds,
                    )
                    if added:
                        st.success(f"تمت إضافة الكلمة {current_query} إلى قائمة المراجعة")
                    else:
                        st.info(f"الكلمة {current_query} موجودة بالفعل في قائمة المراجعة")
        else:
            st.warning(f"لم يتم العثور على الكلمة '{current_query}' في قاعدة البيانات الحالية.")


# ================= 2️⃣ وضع المراجعة =================
elif mode == "المراجعة":
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        due_cards = get_due_flashcards()
        total_saved_count = get_total_flashcards_count()

        if not due_cards or total_saved_count == 0:
            st.info("🎉 لا توجد بطاقات مستحقة للمراجعة حالياً! يمكنك إضافة المزيد من الكلمات.")
        else:
            (
                card_id,
                word,
                snippet,
                video_id,
                start_time,
                target_step,
                current_step,
            ) = due_cards[0]

            count_str = format_arabic_word_count(total_saved_count)

            # 🎯 التعديل المطلوب: تعديل حرف الجر ليصبح "للمراجعة"
            st.markdown(
                f"<h5 style='text-align: center; color: #333; font-family: Calibri; margin-bottom: 15px;'>يوجد {count_str} محفوظة للمراجعة، والكلمة المستحقة الآن هي:</h5>",
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class='anki-card'>
                    <h2>{word}</h2>
                </div>
            """,
                unsafe_allow_html=True,
            )

            b_col1, b_col2 = st.columns(2)

            with b_col1:
                encoded_word = urllib.parse.quote(word.strip())
                dict_url = f"https://dictionary.ksaa.gov.sa/result/{encoded_word}"
                st.markdown(
                    f"<a href='{dict_url}' target='_blank' class='dict-btn'>معنى ({word}) في معجم الرياض</a>",
                    unsafe_allow_html=True,
                )

            with b_col2:
                if st.button("إظهار المقطع والنص", use_container_width=True):
                    st.session_state.show_video = not st.session_state.show_video
                    st.rerun()

            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

            if st.session_state.show_video:
                youtube_url = f"https://www.youtube.com/watch?v={video_id}&t={start_time}s"
                st.video(youtube_url, start_time=start_time)

                highlighted_snippet = snippet.replace(word, f"<mark>{word}</mark>")
                st.markdown(
                    f"<p style='font-size: 19px; color: #000; text-align: right; font-family: Calibri; background-color: #ffffff; padding: 15px; border-radius: 8px; margin-top: 10px;'>{highlighted_snippet}</p>",
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

            st.markdown(
                "<h5 style='text-align: center; color: #333; margin-top: 10px; font-family: Calibri;'>للانتقال للكلمة التالية، متى تريد ظهور هذه الكلمة في المرة القادمة؟</h5>",
                unsafe_allow_html=True,
            )

            r_col1, r_col2, r_col3 = st.columns(3)

            with r_col1:
                if st.button("لا أريد ظهورها مرة أخرى", use_container_width=True):
                    update_flashcard_review(card_id, "never")
                    st.session_state.show_video = False
                    st.rerun()

            with r_col2:
                if st.button("أريد ظهورها بعد خمس مرات", use_container_width=True):
                    update_flashcard_review(card_id, "five")
                    st.session_state.show_video = False
                    st.rerun()

            with r_col3:
                if st.button("أريد ظهورها بعد عشر مرات", use_container_width=True):
                    update_flashcard_review(card_id, "ten")
                    st.session_state.show_video = False
                    st.rerun()


# ================= 3️⃣ وضع قائمة الكلمات =================
else:
    st.markdown(
        "<h2 style='text-align: center; color: #0A192F; font-family: Calibri;'>📖 قائمة الكلمات الشائعة</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #333; font-size: 16px; margin-bottom: 25px;'>انقر على أي كلمة للانتقال مباشرة للبحث عنها في الفيديوهات</p>",
        unsafe_allow_html=True,
    )

    num_cols = 5
    cols = st.columns(num_cols)

    for idx, w in enumerate(WORDS_LIST):
        col_idx = idx % num_cols
        with cols[col_idx]:
            st.button(
                w,
                key=f"word_btn_{idx}_{w}",
                use_container_width=True,
                on_click=navigate_and_search,
                args=(w,),
            )
