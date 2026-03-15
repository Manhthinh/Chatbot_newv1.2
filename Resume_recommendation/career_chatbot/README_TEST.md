# 🚀 Hướng Dẫn Test Chatbot - Quick Start

## ⚡ Cách Nhanh Nhất (2 Phút)

### 1. Kích hoạt venv
```bash
cd d:/TTTN/Project
source venv/Scripts/activate
cd Resume_recommendation/career_chatbot
```

### 2. Chạy test nhanh
```bash
# Một lệnh duy nhất
python src/matching/gap_analysis.py \
  --txt "data/raw/cv_samples/cv_data_manual.txt" \
  --output "data/processed/quick_gap.json" && \
python src/chatbot/chat_router.py \
  --question "CV của tôi phù hợp với vị trí nào?" \
  --gap_result "data/processed/quick_gap.json"
```

**Kết quả:** Sẽ thấy phân tích CV với 5 mục (Mức độ phù hợp, Điểm mạnh, Điểm thiếu, Kỹ năng phát triển, Hành động đề xuất).

---

## 📖 Hướng Dẫn Tương Tác (Khuyến Nghị)

### Cách 1: Chế độ Interactive Python
```bash
python test_chatbot_interactive.py
```

**Ưu điểm:**
- ✅ Menu tương tác dễ dùng
- ✅ Hướng dẫn từng bước
- ✅ Không cần nhớ lệnh

### Cách 2: Script Bash (Linux/Mac/WSL2)
```bash
bash quick_test.sh
```

**Ưu điểm:**
- ✅ Menu tương tác với màu sắc
- ✅ Toàn bộ logic đóng gói
- ✅ Dễ chạy lần sau

---

## 📚 Chi Tiết Từng Bước

Xem file: **TESTING_GUIDE.md**

```bash
# Mở hướng dẫn (trên Windows)
start TESTING_GUIDE.md

# Hoặc xem trực tiếp
cat TESTING_GUIDE.md
```

---

## 🎯 3 Bước Chính

```
┌─────────────────────────────────────┐
│  Bước 1: Extract CV                 │
│  extract_cv_info.py                 │
│  Input: CV file (.pdf/.txt/.docx)   │
│  Output: JSON with skills & exp     │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│  Bước 2: Gap Analysis               │
│  gap_analysis.py                    │
│  Input: Extracted CV JSON           │
│  Output: JSON with skills gaps      │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│  Bước 3: Chatbot Answer             │
│  chat_router.py                     │
│  Input: Question + Gap Analysis     │
│  Output: AI recommendation          │
└─────────────────────────────────────┘
```

---

## ✅ Các Loại Câu Hỏi Để Test

### 1️⃣ **CV Analysis Queries** (Phân tích CV)
```bash
python src/chatbot/chat_router.py \
  --question "CV của tôi phù hợp với vị trí nào nhất?" \
  --gap_result "data/processed/quick_gap.json"
```

Các từ khóa để chatbot nhận diện:
- "cv", "resume", "hồ sơ"
- "phù hợp", "thiếu gì"
- "dựa trên hồ sơ"

### 2️⃣ **Career Advice Queries** (Lộ Trình Phát Triển)
```bash
python src/chatbot/chat_router.py \
  --question "Nên học gì để trở thành Data Engineer?" \
  --gap_result "data/processed/quick_gap.json"
```

Các từ khóa để chatbot nhận diện:
- "nên học gì", "roadmap"
- "phát triển kỹ năng"
- "3 tháng", "6 tháng"

### 3️⃣ **General Questions** (Kiến Thức Chung)
```bash
python src/chatbot/chat_router.py \
  --question "Machine Learning khác gì Deep Learning?"
```

Không cần gap_result, chatbot sẽ giải thích khái niệm.

---

## 📊 Kiểm Tra Output

### Xem kết quả được tạo
```bash
# Liệt kê các file processed
ls -la data/processed/ | tail -10

# Xem chi tiết gap analysis
cat data/processed/quick_gap.json | python -m json.tool | head -50
```

### Format kết quả từ Chatbot
```
===== INTENT =====
cv_analysis                              ← Loại câu hỏi

===== ANSWER =====

1. Mức độ phù hợp
   [Phân tích...]

2. Điểm mạnh hiện tại
   - Kỹ năng 1
   - Kỹ năng 2

3. Điểm còn thiếu
   - Thiếu hụt 1
   - Thiếu hụt 2

4. Kỹ năng nên phát triển tiếp
   - [...]

5. Hành động đề xuất trong 1–3 tháng
   - [...]
```

---

## 🔍 Troubleshooting

### ❌ Lỗi: "File not found"
```bash
# Kiểm tra cấu trúc folder
tree data/processed/
tree data/raw/

# Hoặc
ls -la data/processed/
```

### ❌ Lỗi: "Module not found"
```bash
# Kiểm tra venv
pip list | grep -E "(requests|pandas|PyMuPDF)"

# Cài lại (nếu cần)
pip install -r requirements.txt
```

### ❌ Lỗi: "Ollama not reachable"
- **Bình thường** ← Chatbot sẽ tự dùng fallback mode (không AI)
- **Nếu muốn dùng AI:** Cài Ollama, chạy `ollama serve` ở terminal khác

### ❌ Lỗi: "Permission denied" (trên Linux/Mac)
```bash
chmod +x quick_test.sh
bash quick_test.sh
```

---

## 💡 Mẹo Nhanh

### Script 1 lệnh chạy full pipeline
```bash
#!/bin/bash
cd d:/TTTN/Project/Resume_recommendation/career_chatbot
python src/cv_processing/extract_cv_info.py --txt "data/raw/cv_samples/cv_data_manual.txt" --output "temp_extracted.json" && \
python src/matching/gap_analysis.py --cv_json "temp_extracted.json" --output "temp_gap.json" && \
python src/chatbot/chat_router.py --question "Tôi nên làm gì tiếp theo?" --gap_result "temp_gap.json"
```

### Lưu output vào file
```bash
python src/chatbot/chat_router.py \
  --question "Câu hỏi của tôi" \
  --gap_result "data/processed/quick_gap.json" \
  > output.txt 2>&1

cat output.txt
```

### Test nhiều câu hỏi
```bash
for question in \
  "CV của tôi phù hợp không?" \
  "Nên học SQL không?" \
  "3 tháng nên học gì?"
do
  echo "Q: $question"
  python src/chatbot/chat_router.py \
    --question "$question" \
    --gap_result "data/processed/quick_gap.json"
  echo "---"
done
```

---

## 📁 Cấu Trúc File Quan Trọng

```
Career_chatbot/
├── src/
│   ├── cv_processing/
│   │   └── extract_cv_info.py          ← Bước 1
│   ├── matching/
│   │   └── gap_analysis.py             ← Bước 2
│   └── chatbot/
│       └── chat_router.py              ← Bước 3
├── data/
│   ├── raw/cv_samples/                 ← Input CV
│   ├── processed/                      ← Output JSON
│   └── role_profiles.json              ← Định nghĩa role
│
├── TESTING_GUIDE.md                    ← Chi tiết (bạn đọc)
├── test_chatbot_interactive.py         ← Menu interactive
├── quick_test.sh                       ← Script bash
└── README.md                           ← File này
```

---

## 🚀 Bắt Đầu Ngay

### Option A: Muốn test ngay (1 phút)
```bash
cd d:/TTTN/Project/Resume_recommendation/career_chatbot
source venv/Scripts/activate  # hoặc: . venv/Scripts/activate trên Windows CMD
python test_chatbot_interactive.py
```

### Option B: Muốn làm từng bước (5 phút)
```bash
cd d:/TTTN/Project/Resume_recommendation/career_chatbot
bash quick_test.sh
```

### Option C: Muốn hiểu chi tiết (30 phút)
```bash
cd d:/TTTN/Project/Resume_recommendation/career_chatbot
cat TESTING_GUIDE.md  # Đọc hướng dẫn đầy đủ
```

---

## 📞 Liên Hệ

Gặp vấn đề? Kiểm tra:
1. ✅ Venv activated: `pip --version`
2. ✅ Packages cài đủ: `pip list | grep (requests|pandas)`
3. ✅ File CV tồn tại: `ls data/raw/cv_samples/`
4. ✅ Python version >= 3.8: `python --version`

---

**Chúc bạn test thành công! 🎉**
