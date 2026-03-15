# 🤖 Hướng Dẫn Test Chatbot Hệ Thống Đề Xuất CV

## 📋 Tổng Quan

Hệ thống gồm 3 bước chính:
1. **Bước 1**: Trích xuất thông tin từ CV (CV Processing)
2. **Bước 2**: Phân tích khoảng cách kỹ năng (Gap Analysis)
3. **Bước 3**: Gọi Chatbot để trả lời câu hỏi (Chat Router)

---

## 🛠️ Yêu Cầu Ban Đầu

### 1. Kích hoạt venv
```bash
cd d:/TTTN/Project
source venv/Scripts/activate
```

### 2. Kiểm tra các packages cần thiết
```bash
pip list | grep -E "(requests|pandas|PyMuPDF)"
```

Kết quả mong muốn:
```
pandas==3.0.1
PyMuPDF==1.27.2
requests==2.32.5
```

---

## 📝 BƯỚC 1: Trích Xuất Thông Tin CV (Extract CV Info)

### 1.1 File Python
```
src/cv_processing/extract_cv_info.py
```

### 1.2 Test với file CV mẫu

#### Cách 1: Từ file PDF
```bash
cd d:/TTTN/Project/Resume_recommendation/career_chatbot

python src/cv_processing/extract_cv_info.py \
  --pdf "data/raw/cv_samples/Resume.pdf.pdf" \
  --output "data/processed/test_resume_extracted.json"
```

#### Cách 2: Từ file TXT
```bash
python src/cv_processing/extract_cv_info.py \
  --txt "data/raw/cv_samples/cv_data_manual.txt" \
  --output "data/processed/test_cv_data_extracted.json"
```

#### Cách 3: Từ file .docx
```bash
python src/cv_processing/extract_cv_info.py \
  --docx "path/to/your/resume.docx" \
  --output "data/processed/test_resume_extracted.json"
```

### 1.3 Kiểm tra kết quả
```bash
# Xem dữ liệu extracted
cat data/processed/test_resume_extracted.json | python -m json.tool | head -50

# Hoặc sử dụng Python để xem chi tiết
python -c "
import json
with open('data/processed/test_resume_extracted.json') as f:
    data = json.load(f)
    print('CV Title:', data.get('title', 'N/A'))
    print('Skills:', data.get('skills', [])[:10])
    print('Experience:', data.get('experience', [])[:2])
"
```

---

## 📊 BƯỚC 2: Phân Tích Khoảng Cách Kỹ Năng (Gap Analysis)

### 2.1 File Python
```
src/matching/gap_analysis.py
```

### 2.2 Chạy Gap Analysis

#### Phiên bản 1: Sử dụng CV đã extracted
```bash
python src/matching/gap_analysis.py \
  --cv_json "data/processed/test_resume_extracted.json" \
  --output "data/processed/test_gap_analysis.json"
```

#### Phiên bản 2: Tạo gap analysis từ scratch (từ file CV)
```bash
python src/matching/gap_analysis.py \
  --txt "data/raw/cv_samples/cv_data_manual.txt" \
  --output "data/processed/test_gap_analysis.json"
```

### 2.3 Kiểm tra kết quả Gap Analysis
```bash
# Xem toàn bộ kết quả
cat data/processed/test_gap_analysis.json | python -m json.tool

# Xem các thông tin quan trọng
python -c "
import json
with open('data/processed/test_gap_analysis.json') as f:
    gap = json.load(f)
    print('Domain Fit:', gap.get('domain_fit'))
    print('Best Fit Roles:', gap.get('best_fit_roles'))
    print('Top Role:', gap.get('top_role_result', {}).get('role'))
    print('Matching Skills:', gap.get('top_role_result', {}).get('matched_skills', [])[:5])
    print('Missing Skills:', gap.get('missing_skills', [])[:5])
"
```

---

## 💬 BƯỚC 3: Test Chatbot - Chat Router

### 3.1 File Python
```
src/chatbot/chat_router.py
```

### 3.2 Chuẩn Bị Gap Result

Sử dụng file gap analysis từ bước 2:
```bash
GAP_RESULT="data/processed/test_gap_analysis.json"
echo "✓ Gap result file: $GAP_RESULT"
cat "$GAP_RESULT" | python -m json.tool | head -30
```

### 3.3 Test Chat Router với các loại câu hỏi

#### **Loại 1: Câu Hỏi CV Analysis (Phân Tích CV)**
```bash
python src/chatbot/chat_router.py \
  --question "Hồ sơ của tôi phù hợp với vị trí Data Analyst không?" \
  --gap_result "data/processed/test_gap_analysis.json"
```

Output mong muốn:
```
===== INTENT =====
cv_analysis

===== ANSWER =====

1. Mức độ phù hợp
   [Phân tích chi tiết mức độ phù hợp]

2. Điểm mạnh hiện tại
   - [Kỹ năng 1]
   - [Kỹ năng 2]
   ...

3. Điểm còn thiếu
   - [Kỹ năng thiếu 1]
   - [Kỹ năng thiếu 2]
   ...

4. Kỹ năng nên phát triển tiếp
   - [Kỹ năng 1]
   - [Kỹ năng 2]
   ...

5. Hành động đề xuất trong 1–3 tháng
   - [Hành động 1]
   - [Hành động 2]
   ...
```

#### **Loại 2: Câu Hỏi Career Advice (Tư Vấn Sự Nghiệp)**
```bash
python src/chatbot/chat_router.py \
  --question "Nên học gì để trở thành Data Engineer?" \
  --gap_result "data/processed/test_gap_analysis.json"
```

Output mong muốn:
```
===== INTENT =====
career_advice

===== ANSWER =====
[Lộ trình học tập chi tiết]
```

#### **Loại 3: Câu Hỏi General (Kiến Thức Chung)**
```bash
python src/chatbot/chat_router.py \
  --question "Machine Learning là gì?"
```

Output mong muốn:
```
===== INTENT =====
general_question

===== ANSWER =====
[Giải thích khái niệm ML]
```

#### **Loại 4: Câu Hỏi về Roadmap/Timeline**
```bash
python src/chatbot/chat_router.py \
  --question "Tôi phải học những gì trong 3 tháng để trở thành Data Analyst?" \
  --gap_result "data/processed/test_gap_analysis.json"
```

---

## 🎯 Các Câu Hỏi Test Khác

### Test Set 1: Phân Tích CV
```bash
# Question 1
python src/chatbot/chat_router.py \
  --question "CV của tôi có điểm mạnh gì cho vị trí Data Scientist?" \
  --gap_result "data/processed/test_gap_analysis.json"

# Question 2
python src/chatbot/chat_router.py \
  --question "Phù hợp nghề nào dựa trên hồ sơ?" \
  --gap_result "data/processed/test_gap_analysis.json"

# Question 3
python src/chatbot/chat_router.py \
  --question "Tôi thiếu kỹ năng gì để ứng tuyển vị trí này?" \
  --gap_result "data/processed/test_gap_analysis.json"
```

### Test Set 2: Lộ Trình Phát Triển
```bash
# Question 1
python src/chatbot/chat_router.py \
  --question "Roadmap để trở thành AI Engineer là gì?" \
  --gap_result "data/processed/test_gap_analysis.json"

# Question 2
python src/chatbot/chat_router.py \
  --question "Nên làm project gì để cải thiện kỹ năng?" \
  --gap_result "data/processed/test_gap_analysis.json"

# Question 3
python src/chatbot/chat_router.py \
  --question "Trong 6 tháng tôi nên học gì?" \
  --gap_result "data/processed/test_gap_analysis.json"
```

### Test Set 3: Câu Hỏi Chung
```bash
python src/chatbot/chat_router.py \
  --question "SQL là ngôn ngữ lập trình hay gì?"

python src/chatbot/chat_router.py \
  --question "PostgreSQL khác gì so với MySQL?"

python src/chatbot/chat_router.py \
  --question "Deep Learning khác gì Machine Learning?"
```

---

## ⚙️ Triển Khai Full Pipeline (Toàn Bộ Quy Trình)

Chạy toàn bộ pipeline từ file CV → Phân tích → Chatbot:

```bash
#!/bin/bash
set -e

CD_PATH="d:/TTTN/Project/Resume_recommendation/career_chatbot"
cd "$CD_PATH"

# Bước 1: Extract CV
echo "=== Bước 1: Trích xuất CV ==="
python src/cv_processing/extract_cv_info.py \
  --txt "data/raw/cv_samples/cv_data_manual.txt" \
  --output "data/processed/full_pipeline_extracted.json"
echo "✓ Extracted: full_pipeline_extracted.json"

# Bước 2: Gap Analysis
echo -e "\n=== Bước 2: Phân tích khoảng cách ==="
python src/matching/gap_analysis.py \
  --cv_json "data/processed/full_pipeline_extracted.json" \
  --output "data/processed/full_pipeline_gap.json"
echo "✓ Gap Analysis: full_pipeline_gap.json"

# Bước 3: Chatbot Query
echo -e "\n=== Bước 3: Test Chatbot ==="
python src/chatbot/chat_router.py \
  --question "CV của tôi phù hợp với vị trí nào nhất?" \
  --gap_result "data/processed/full_pipeline_gap.json"

echo -e "\n✓ Pipeline hoàn thành!"
```

Lưu script trên vào file `test_full_pipeline.sh` và chạy:
```bash
bash test_full_pipeline.sh
```

---

## 🔍 Debugging & Troubleshooting

### Lỗi 1: File không tìm thấy
```bash
# Kiểm tra các file config
ls -la data/role_profiles/
ls -la data/processed/
```

### Lỗi 2: Llama/Ollama không chạy
```bash
# Kiểm tra Ollama
curl http://localhost:11434/api/tags

# Nếu không có, chatbot sẽ tự động dùng chế độ fallback (không AI)
```

### Lỗi 3: Xem chi tiết JSON
```bash
# Formatted view
cat data/processed/test_gap_analysis.json | python -m json.tool

# Với Less (để scroll)
cat data/processed/test_gap_analysis.json | python -m json.tool | less
```

### Lỗi 4: Kiểm tra import
```bash
python -c "
from src.cv_processing.extract_cv_info import extract_cv_from_text
from src.matching.gap_analysis import run_gap_analysis
from src.chatbot.chat_router import classify_question
print('✓ Tất cả imports OK')
"
```

---

## 📚 Cấu Trúc File Quan Trọng

```
Resume_recommendation/career_chatbot/
├── src/
│   ├── cv_processing/
│   │   └── extract_cv_info.py        # Trích xuất thông tin CV
│   ├── matching/
│   │   └── gap_analysis.py           # Phân tích khoảng cách
│   ├── data_processing/
│   │   ├── build_role_profiles.py    # Xây dựng profile role
│   │   └── merge_jobs.py             # Merge data công việc
│   └── chatbot/
│       ├── chat_router.py            # Router & Chatbot main
│       └── chatbot_advisor.py        # Advisor (cách khác)
├── data/
│   ├── raw/
│   │   └── cv_samples/               # Sample CV để test
│   ├── processed/                    # Output files
│   ├── role_profiles.json            # Profile các role
│   └── skill_catalog.json            # Catalog kỹ năng
└── scripts/
    └── setup_llama_cpp.py            # Setup llama.cpp model
```

---

## 🚀 Mẹo Nhanh

### Chạy nhanh test (1 lệnh)
```bash
cd d:/TTTN/Project/Resume_recommendation/career_chatbot && \
python src/matching/gap_analysis.py --txt "data/raw/cv_samples/cv_data_manual.txt" --output "data/processed/quick_test_gap.json" && \
python src/chatbot/chat_router.py --question "Role phù hợp nhất cho tôi là gì?" --gap_result "data/processed/quick_test_gap.json"
```

### Lưu output vào file
```bash
python src/chatbot/chat_router.py \
  --question "CV của tôi phù hợp không?" \
  --gap_result "data/processed/test_gap_analysis.json" \
  > chatbot_response.txt 2>&1

cat chatbot_response.txt
```

### Test với dữ liệu có sẵn
```bash
# Sử dụng các file data đã có
python src/chatbot/chat_router.py \
  --question "Tôi nên học gì tiếp theo?" \
  --gap_result "data/processed/cv_data_manual_gap.json"
```

---

## ✅ Checklist Test

- [ ] Venv kích hoạt
- [ ] Extract CV thành công → file JSON
- [ ] Gap Analysis chạy → file JSON + xem best_fit_roles
- [ ] Chatbot CV Analysis question → kết quả có 5 mục
- [ ] Chatbot Career Advice question → kết quả lộ trình
- [ ] Chatbot General Question → kết quả giải thích
- [ ] Xem fallback mode ghi chú nếu Ollama không chạy
- [ ] Kiểm tra error logs (nếu có)

---

## 📞 Liên Hệ/Hỗ Trợ

Nếu gặp lỗi, kiểm tra:
1. Requirements đã cài đủ: `pip freeze | grep -E "(requests|pandas|PyMuPDF)"`
2. Đường dẫn file đúng: `ls -la data/processed/`
3. Python path đúng: `python --version` (phải >= 3.8)
4. Ollama/Llama.cpp (optional): `curl http://localhost:11434/api/tags`
