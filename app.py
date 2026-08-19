import streamlit as st
import sqlite3
import json
import urllib.parse
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(page_title="Linguistic Indexer - KSGAAL", layout="wide")

# --- 🎨 CSS Styling: Clean Top Radio & Matching 13.5px Font ---
st.markdown("""
    <style>
    /* تطبيق خط Calibri على كل العناصر */
    html, body, [class*="css"], button, input, textarea, div, span, p, h1, h2, h3, h4, h5, h6, label {
        font-family: 'Calibri', 'Segoe UI', sans-serif !important;
        font-weight: normal !important;
    }

    .stApp {
        background-color: #01DFD7;
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

    /* 1️⃣ تصغير أزرار Streamlit العادية إلى 13.5px */
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

    /* 2️⃣ تصغير زر المعنى (الرابط الخارجي) إلى 13.5px */
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

    /* 3️⃣ تصغير نص الخيارات العلوية (البحث / المراجعة) إلى 13.5px وزيادة المسافة بين الخيارين */
    div[data-testid="stRadio"] label p {
        font-size: 13.5px !important;
        font-family: 'Calibri', sans-serif !important;
        font-weight: normal !important;
        color: #000000 !important;
    }

    /* إضافة مسافة أفقية بين خيارات الـ Radio */
    div[data-testid="stRadio"] > div {
        gap: 30px !important;
    }

    /* كارت أنكي */
    .anki-card {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        font-family: 'Calibri', sans-serif !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 🗄️ تهيئة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('ksgafal_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            snippet TEXT,
            video_id TEXT,
            start_time INTEGER,
            interval_minutes INTEGER DEFAULT 1,
            next_review DATETIME
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Custom function to extract snippet
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

# Helper function to search inside SQLite database
def search_word_in_db(query):
    conn = sqlite3.connect('ksgafal_data.db')
    cursor = conn.cursor()
    query_clean = query.strip()

    cursor.execute(
        "SELECT video_id, title, channel, full_transcript, timestamps_json FROM videos WHERE full_transcript LIKE ?", 
        (f"%{query_clean}%",)
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
            
        matched_timestamps = [item.get('start', 0) for item in timestamps if query_clean.lower() in item.get('word', '').lower()]
        
        if matched_timestamps:
            snippet = get_snippet(full_transcript, query_clean)
            results.append({
                'video_id': video_id,
                'title': title,
                'channel': channel,
                'first_start': matched_timestamps[0],
                'snippet': snippet
            })
    return results

# --- 📇 وظائف إدارة بطاقات أنكي ---
def save_to_flashcards(word, snippet, video_id, start_time):
    conn = sqlite3.connect('ksgafal_data.db')
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute(
            "INSERT INTO flashcards (word, snippet, video_id, start_time, interval_minutes, next_review) VALUES (?, ?, ?, ?, 1, ?)",
            (word, snippet, video_id, start_time, now_str)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_due_flashcards():
    conn = sqlite3.connect('ksgafal_data.db')
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT id, word, snippet, video_id, start_time, interval_minutes FROM flashcards WHERE next_review <= ?", (now_str,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_flashcard_review(card_id, current_interval, rating):
    if rating == 'hard':
        new_interval = 1       # بعد دقيقة واحدة
    elif rating == 'good':
        new_interval = 5       # بعد 5 دقائق
    else: # easy
        new_interval = 10      # بعد 10 دقائق

    next_review = (datetime.now() + timedelta(minutes=new_interval)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect('ksgafal_data.db')
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE flashcards SET interval_minutes = ?, next_review = ? WHERE id = ?",
        (new_interval, next_review, card_id)
    )
    conn.commit()
    conn.close()

# --- 🧠 Session State ---
if 'last_query' not in st.session_state:
    st.session_state.last_query = ""
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'show_answer' not in st.session_state:
    st.session_state.show_answer = False

# --- 🔘 شريط التنقل العلوي بين الوضعين ---
menu_col1, menu_col2, menu_col3 = st.columns([1, 2, 1])
with menu_col2:
    mode = st.radio("", ["البحث", "المراجعة"], horizontal=True, label_visibility="collapsed")

st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

# ================= ================= =================
# 1️⃣ وضع البحث
# ================= ================= =================
if mode == "البحث":
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        query = st.text_input(label="", label_visibility="collapsed", placeholder="أدخل الكلمة للبحث...")
        btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 2])
        with btn_col2:
            search_clicked = st.button("بحث", use_container_width=True)

    st.markdown("<div style='margin-bottom: 65px;'></div>", unsafe_allow_html=True)

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
                nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                with nav_col1:
                    if st.button("السابق", use_container_width=True, disabled=(curr_idx == 0)):
                        st.session_state.current_index -= 1
                        st.rerun()

                with nav_col2:
                    st.markdown(f"<h4 style='text-align: center; color: #333333; font-family: Calibri; font-weight: normal; margin-top: 5px;'>مقطع {curr_idx + 1} من {total_results}</h4>", unsafe_allow_html=True)

                with nav_col3:
                    if st.button("التالي", use_container_width=True, disabled=(curr_idx == total_results - 1)):
                        st.session_state.current_index += 1
                        st.rerun()
                
                start_seconds = int(res['first_start'])
                youtube_url = f"https://www.youtube.com/watch?v={res['video_id']}&t={start_seconds}s"
                
                st.video(youtube_url, start_time=start_seconds)
                
                highlighted_snippet = res['snippet'].replace(current_query, f"<mark>{current_query}</mark>")
                st.markdown(f"<p style='font-size: 19px; color: #000000; text-align: right; font-family: Calibri; font-weight: normal; margin-top: 10px;'>{highlighted_snippet}</p>", unsafe_allow_html=True)
                
                # --- أزرار الإجراءات ---
                encoded_query = urllib.parse.quote(current_query.strip())
                dict_url = f"https://dictionary.ksaa.gov.sa/result/{encoded_query}"
                
                btn_left, btn_right = st.columns([1, 1])
                with btn_right:
                    st.markdown(f"<a href='{dict_url}' target='_blank' class='dict-btn'>معنى ({current_query}) في معجم الرياض</a>", unsafe_allow_html=True)
                
                with btn_left:
                    if st.button(f"حفظ ({current_query}) في بطاقات أنكي", use_container_width=True):
                        added = save_to_flashcards(current_query, res['snippet'], res['video_id'], start_seconds)
                        if added:
                            st.success(f"تمت إضافة الكلمة {current_query} إلى بطاقات المراجعة")
                        else:
                            st.info(f"الكلمة {current_query} موجودة بالفعل في قائمة البطاقات")
        else:
            st.warning(f"لم يتم العثور على الكلمة '{current_query}' في قاعدة البيانات الحالية.")

# ================= ================= =================
# 2️⃣ وضع المراجعة
# ================= ================= =================
else:
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        due_cards = get_due_flashcards()
        
        if st.button("تحديث حالة البطاقات", use_container_width=True):
            st.rerun()
            
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

        if not due_cards:
            st.info("لا توجد بطاقات مستحقة للمراجعة الآن. يمكنك الانتظار ثم الضغط على زر تحديث حالة البطاقات")
        else:
            card_id, word, snippet, video_id, start_time, interval_minutes = due_cards[0]
            
            st.markdown(f"<h3 style='text-align: center; color: #333; font-family: Calibri;'>البطاقات المستحقة الآن: {len(due_cards)}</h3>", unsafe_allow_html=True)
            
            # --- وجه البطاقة (Front) ---
            st.markdown(f"""
                <div class='anki-card'>
                    <h2 style='color: #000; margin: 0; font-family: Calibri;'>{word}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            if not st.session_state.show_answer:
                if st.button("إظهار الإجابة والمقطع", use_container_width=True):
                    st.session_state.show_answer = True
                    st.rerun()
            else:
                # --- ظهر البطاقة (Back) ---
                youtube_url = f"https://www.youtube.com/watch?v={video_id}&t={start_time}s"
                st.video(youtube_url, start_time=start_time)
                
                highlighted_snippet = snippet.replace(word, f"<mark>{word}</mark>")
                st.markdown(f"<p style='font-size: 19px; color: #000; text-align: right; font-family: Calibri;'>{highlighted_snippet}</p>", unsafe_allow_html=True)
                
                st.markdown("<h5 style='text-align: center; color: #333; margin-top: 20px; font-family: Calibri;'>حدد وقت المراجعة القادم</h5>", unsafe_allow_html=True)
                
                r_col1, r_col2, r_col3 = st.columns(3)
                
                with r_col1:
                    if st.button("صعب (بعد دقيقة واحدة)", use_container_width=True):
                        update_flashcard_review(card_id, interval_minutes, 'hard')
                        st.session_state.show_answer = False
                        st.rerun()
                        
                with r_col2:
                    if st.button("جيد (بعد 5 دقائق)", use_container_width=True):
                        update_flashcard_review(card_id, interval_minutes, 'good')
                        st.session_state.show_answer = False
                        st.rerun()
                        
                with r_col3:
                    if st.button("سهل (بعد 10 دقائق)", use_container_width=True):
                        update_flashcard_review(card_id, interval_minutes, 'easy')
                        st.session_state.show_answer = False
                        st.rerun()