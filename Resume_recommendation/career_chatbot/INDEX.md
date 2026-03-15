# 📑 INDEX - Tất Cả File Hướng Dẫn Test Chatbot

## 🎯 VỊ TRÍ: `d:/TTTN/Project/Resume_recommendation/career_chatbot/`

Tôi vừa tạo **5 file hướng dẫn** trong folder này:

---

## 📄 DANH SÁCH FILE (Thứ Tự Khuyến Nghị)

### 1️⃣ **START_HERE.md** ⭐ **ĐỌC TRƯỚC**
- **Mục đích:** Giới thiệu nhanh, cách chọn cách test
- **Thời gian:** 2-3 phút
- **Cần làm:** Chọn 1 trong 3 cách test

### 2️⃣ **README_TEST.md** ⭐ **KHUYẾN NGHỊ**
- **Mục đích:** Hướng dẫn nhanh, từng bước, mẹo
- **Thời gian:** 5-10 phút
- **Lệnh:** Sao chép & dán lệnh từ đây

### 3️⃣ **test_chatbot_interactive.py** ✅ **PYTHON SCRIPT**
- **Mục đích:** Menu interactive tương tác
- **Cách chạy:** `python test_chatbot_interactive.py`
- **Ưu điểm:** Không cần nhớ lệnh, hướng dẫn từng bước
- **Thích hợp:** Người lầm lần

### 4️⃣ **quick_test.sh** ⌨️ **BASH SCRIPT**
- **Mục đích:** Script tự động chạy toàn bộ
- **Cách chạy:** `bash quick_test.sh`
- **Ưu điểm:** Nhanh, có menu màu sắc
- **Thích hợp:** Linux/Mac/WSL2

### 5️⃣ **TESTING_GUIDE.md** 📖 **CHI TIẾT (30 TRANG)**
- **Mục đích:** Hướng dẫn **đầy đủ nhất**, mọi tình huống
- **Thời gian:** 30-45 phút đọc
- **Nội dung:**
  - ✅ Yêu cầu ban đầu
  - ✅ Bước 1-3 chi tiết
  - ✅ Các câu hỏi test
  - ✅ Full pipeline script
  - ✅ Debugging hết cả
- **Khi nào:** Khi muốn hiểu sâu hoặc gặp lỗi

---

## 🚀 BƯỚC ĐẦU TIÊN (60 GIÂY)

### 1. Mở terminal
```bash
# Windows PowerShell
cd d:\TTTN\Project\Resume_recommendation\career_chatbot
```

### 2. Activate venv
```bash
source venv/Scripts/activate
```

### 3. Chạy interactive menu
```bash
python test_chatbot_interactive.py
```

### 4. Chọn option "1" → "1" → Trả lời các câu hỏi

**✓ DONE!** Sẽ thấy kết quả chatbot trong 2-3 phút.

---

## 🎯 CÁCH CHỌN DỰA VÀO MỤC ĐÍCH

| Mục Đích | Đọc File | Chạy Lệnh |
|----------|---------|----------|
| Muốn test ngay | START_HERE.md | `python test_chatbot_interactive.py` |
| Muốn hiểu từng bước | README_TEST.md | Copy lệnh từ file + chạy |
| Muốn toàn bộ auto | quick_test.sh | `bash quick_test.sh` |
| Gặp lỗi, cần giải pháp | TESTING_GUIDE.md | Xem mục "Troubleshooting" |
| Muốn code từng bước | TESTING_GUIDE.md | Xem mục "BƯỚC 1/2/3" |

---

## 📊 KIẾN TRÚC HỆ THỐNG (3 BƯỚC)

```
┌─────────────────────────────────────────────────────────────┐
│                    CHATBOT SYSTEM                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  BƯỚC 1: Extract CV              BƯỚC 2: Gap Analysis       │
│  ┌──────────────────────────┐    ┌─────────────────────┐    │
│  │ extract_cv_info.py       │ ──>│ gap_analysis.py     │    │
│  │                          │    │                     │    │
│  │ Input: CV file           │    │ Input: Extracted    │    │
│  │ (.pdf/.txt/.docx)        │    │ CV JSON             │    │
│  │                          │    │                     │    │
│  │ Output:                  │    │ Output:             │    │
│  │ • Skills                 │    │ • Best fit roles    │    │
│  │ • Experience             │    │ • Domain fit score  │    │
│  │ • Languages              │    │ • Skills gap        │    │
│  └──────────────────────────┘    │ • Recommendations   │    │
│                                  └─────────────────────┘    │
│                                           │                 │
│                                           ↓                 │
│                          BƯỚC 3: Chatbot Router             │
│                          ┌──────────────────────────┐       │
│                          │ chat_router.py           │       │
│                          │                          │       │
│                          │ Input:                   │       │
│                          │ • User question          │       │
│                          │ • Gap analysis result    │       │
│                          │                          │       │
│                          │ Output:                  │       │
│                          │ • AI Response            │       │
│                          │ (5 mục: fit, strengths, │       │
│                          │  gaps, skills, actions)  │       │
│                          └──────────────────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 CẤU TRÚC FOLDER

```
Resume_recommendation/career_chatbot/
│
├── 📝 HƯỚNG DẪN (File tôi vừa tạo)
│   ├── START_HERE.md                    ⭐ Bắt đầu ở đây
│   ├── README_TEST.md                   ⭐ Khuyến nghị
│   ├── TESTING_GUIDE.md                 📖 Chi tiết
│   ├── INDEX.md                         (File này)
│   │
│   ├── test_chatbot_interactive.py      ✅ Python script
│   └── quick_test.sh                    ⌨️ Bash script
│
├── 📂 src/ (Code chính)
│   ├── cv_processing/
│   │   └── extract_cv_info.py           (Bước 1️⃣)
│   ├── matching/
│   │   └── gap_analysis.py              (Bước 2️⃣)
│   └── chatbot/
│       └── chat_router.py               (Bước 3️⃣)
│
├── 📂 data/
│   ├── raw/cv_samples/                  (Sample CVs)
│   │   ├── cv_data_manual.txt
│   │   ├── cv_semi_data_manual.txt
│   │   └── Resume.pdf.pdf
│   ├── processed/                       (Output files)
│   │   ├── cv_data_manual_extracted.json
│   │   ├── cv_data_manual_gap.json
│   │   └── ...
│   ├── role_profiles.json               (Role definitions)
│   └── skill_catalog.json               (Skill list)
│
├── requirements.txt                     (Python packages)
└── ...
```

---

## ✅ ĐIỀU KIỆN CẦN

### Kiểm tra trước khi test
```bash
# 1. Python version >= 3.8
python --version

# 2. Packages cài đủ
pip list | grep -E "(requests|pandas|PyMuPDF)"

# 3. Files tồn tại
ls data/raw/cv_samples/
ls data/processed/
```

### Fix nếu thiếu
```bash
# Cài lại packages
pip install -r requirements.txt

# Hoặc cài từng package
pip install requests pandas PyMuPDF python-docx
```

---

## 🎨 CÁC LOẠI CÂU HỎI ĐỂ TEST

### CV Analysis (Phân Tích CV)
```bash
"CV của tôi phù hợp với vị trí nào nhất?"
"Hồ sơ của tôi có thế nào?"
"Tôi thiếu kỹ năng gì?"
```

### Career Advice (Lộ Trình)
```bash
"Nên học gì để trở thành Data Engineer?"
"Roadmap 3 tháng là gì?"
"Tôi nên làm gì tiếp theo?"
```

### General (Kiến Thức Chung)
```bash
"Machine Learning là gì?"
"SQL dùng để làm gì?"
"Apache Spark và Hadoop khác gì?"
```

---

## 🔍 EXPECTED OUTPUT

### Khi test thành công
```
===== INTENT =====
cv_analysis

===== ANSWER =====

1. Mức độ phù hợp
   CV của bạn hiện phù hợp ở mức [High/Medium/Low] với vị trí [Role]...

2. Điểm mạnh hiện tại
   - Python
   - SQL
   - ...

3. Điểm còn thiếu
   - Machine Learning
   - Statistics
   - ...

4. Kỹ năng nên phát triển tiếp
   - Học Python nâng cao
   - ...

5. Hành động đề xuất trong 1–3 tháng
   - Làm 2 project về data analysis
   - ...
```

---

## 🚨 COMMON ERRORS & FIX

### "Module not found: requests"
```bash
pip install requests pandas PyMuPDF python-docx
```

### "File not found: cv_data_manual.txt"
```bash
# Kiểm tra path
ls -la d:/TTTN/Project/Resume_recommendation/career_chatbot/data/raw/cv_samples/
```

### "Ollama not reachable"
✅ **Bình thường!** Không cần fix, chatbot sẽ dùng fallback mode.

### "Permission denied" (Linux/Mac)
```bash
chmod +x quick_test.sh
bash quick_test.sh
```

---

## 🎓 TIẾP THEO SAU KHI TEST

1. **Hiểu logic:** Đọc `src/chatbot/chat_router.py`, `src/matching/gap_analysis.py`
2. **Thêm tính năng:** Modify code để thêm intent mới
3. **Tích hợp UI:** Streamlit, Flask, FastAPI
4. **Deploy:** Docker, AWS, Heroku

---

## 📞 QUICK LINKS

| Tên | Link | Mục Đích |
|-----|------|---------|
| START_HERE.md | File | Bắt đầu nhanh |
| README_TEST.md | File | Hướng dẫn tường tận |
| TESTING_GUIDE.md | File | Chi tiết đầy đủ |
| test_chatbot_interactive.py | File | Chạy interactive menu |
| Chat Router Code | src/chatbot/chat_router.py | Xem logic chatbot |
| Gap Analysis Code | src/matching/gap_analysis.py | Xem logic analysis |

---

## 🟢 READY TO START?

1. **Cách 1 (Nhanh nhất):**
   - Đọc: `START_HERE.md`
   - Chạy: `python test_chatbot_interactive.py`

2. **Cách 2 (Chi tiết):**
   - Đọc: `README_TEST.md`
   - Sao chép lệnh từ file

3. **Cách 3 (Tìm hiểu):**
   - Đọc: `TESTING_GUIDE.md`
   - Làm từng bước

---

## ✨ Điểm Highlights

✅ **Easy to use** - Menu interactive, không cần nhớ lệnh
✅ **Complete** - 3 bước: Extract → Analysis → Chat
✅ **Sample data** - Có file CV sample sẵn để test
✅ **Fallback mode** - Không cần Ollama, vẫn chạy được
✅ **Vietnamese** - Chatbot trả lời tiếng Việt

---

**BẮT ĐẦU NGAY:**
```bash
python test_chatbot_interactive.py
```

**Hoặc đọc:**
```bash
cat START_HERE.md
```

---

**Chúc bạn test thành công! 🎉🚀**
