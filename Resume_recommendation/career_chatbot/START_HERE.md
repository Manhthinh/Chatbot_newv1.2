# 📌 Hướng Dẫn Test Chatbot - TÓM TẮT

## 🎯 Bạn Đang Ở Đây

Tôi vừa chuẩn bị cho bạn **4 file hướng dẫn** để test chatbot hệ thống đề xuất.

---

## 📖 Chọn 1 Trong 3 Cách Sau:

### 🟢 **CÁCH 1: TEST NGAY (2 Phút)** ⭐ KHUYẾN NGHỊ
```bash
cd d:/TTTN/Project/Resume_recommendation/career_chatbot
source venv/Scripts/activate
python test_chatbot_interactive.py
```
👉 Mở menu tương tác, chọn test option

**📄 File:** `test_chatbot_interactive.py`

---

### 🔵 **CÁCH 2: SCRIPT BASH (3 Phút)** - Nếu dùng Linux/Mac/WSL2
```bash
cd d:/TTTN/Project/Resume_recommendation/career_chatbot
bash quick_test.sh
```
👉 Chọn menu, hệ thống sẽ chạy auto toàn bộ test

**📄 File:** `quick_test.sh`

---

### 🟡 **CÁCH 3: BẰNG TAY (5-10 Phút)** - Nếu muốn hiểu chi tiết
```bash
cd d:/TTTN/Project/Resume_recommendation/career_chatbot
```

**Bước 1: Trích xuất CV**
```bash
python src/cv_processing/extract_cv_info.py \
  --txt "data/raw/cv_samples/cv_data_manual.txt" \
  --output "data/processed/my_test_extracted.json"
```

**Bước 2: Phân tích khoảng cách**
```bash
python src/matching/gap_analysis.py \
  --cv_json "data/processed/my_test_extracted.json" \
  --output "data/processed/my_test_gap.json"
```

**Bước 3: Test Chatbot**
```bash
python src/chatbot/chat_router.py \
  --question "CV của tôi phù hợp với vị trí nào nhất?" \
  --gap_result "data/processed/my_test_gap.json"
```

👉 Xem output kết quả

---

## 📚 CÁCH CHỌN FILE CÓ LIÊN QUAN

| Tệp | Nội Dung | Khi Nào Đọc |
|-----|---------|-----------|
| **README_TEST.md** (file này) | Tóm tắt tất cả | 🟢 **Đọc trước** |
| **TESTING_GUIDE.md** | Chi tiết 30 trang, mọi thứ | 🔵 Khi muốn hiểu sâu |
| **test_chatbot_interactive.py** | Python interactive menu | 🟢 Sử dụng để test |
| **quick_test.sh** | Bash script toàn bộ | 🟡 Sử dụng nếu dùng Linux/Mac |

---

## 🚀 CHẠY NGAY (Sao chép & Dán)

### Windows PowerShell / CMD
```cmd
cd d:\TTTN\Project\Resume_recommendation\career_chatbot
python -m venv venv (nếu chưa có)
venv\Scripts\activate
python test_chatbot_interactive.py
```

### Linux / Mac / WSL2
```bash
cd d:/TTTN/Project/Resume_recommendation/career_chatbot
source venv/bin/activate
python test_chatbot_interactive.py
```

---

## ✅ CHECKLIST ĐẦU TIÊN

Trước khi test:
- [ ] Activate venv: `source venv/Scripts/activate` (Windows) hoặc `source venv/bin/activate` (Linux)
- [ ] Trong folder: `d:/TTTN/Project/Resume_recommendation/career_chatbot`
- [ ] Packages cài: `pip list | grep requests` (phải thấy `requests`)

---

## 🎨 KỊCH BẢN TEST (Để Biết Những Gì Sẽ Xảy Ra)

### Test 1: Phân Tích CV (CV Analysis)
```
Câu hỏi: "CV của tôi phù hợp với vị trí Data Analyst không?"
↓
Kết quả:
  1. Mức độ phù hợp: Medium/High/Low
  2. Điểm mạnh: Python, SQL, ...
  3. Điểm thiếu: Machine Learning, Statistics, ...
  4. Nên học: ...
  5. Hành động: ...
```

### Test 2: Tư Vấn Sự Nghiệp (Career Advice)
```
Câu hỏi: "Nên học gì để trở thành Data Engineer?"
↓
Kết quả:
  Lộ trình 3-6 tháng: SQL → Spark → ETL → ...
```

### Test 3: Câu Hỏi Chung (General Question)
```
Câu hỏi: "Machine Learning là gì?"
↓
Kết quả:
  [Giải thích khái niệm, không cần CV data]
```

---

## 🔧 GẬP PHẢI VẤN ĐỀ?

### Lỗi: "ModuleNotFoundError: No module named 'requests'"
```bash
pip install requests pandas PyMuPDF python-docx
```

### Lỗi: "FileNotFoundError: cv_data_manual.txt"
```bash
# Kiểm tra file tồn tại
ls d:/TTTN/Project/Resume_recommendation/career_chatbot/data/raw/cv_samples/
```

### Lỗi: "Ollama not reachable"
✅ **Bình thường!** Chatbot sẽ tự dùng fallback (không AI, nhưng vẫn có kết quả)
- Nếu muốn AI: Cài Ollama từ https://ollama.ai

---

## 📊 KỲ VỌNG OUTPUT

✓ Chatbot sẽ trả lời bằng **tiếng Việt**
✓ Có **5 mục** khi phân tích CV
✓ Có **INTENT** cho biết chatbot hiểu câu hỏi loại gì
✓ Nếu không có Ollama → fallback mode (vẫn có kết quả, nhưng không super IQ)

---

## 💡 MẸO

1. **Test nhanh:** `python test_chatbot_interactive.py` → Chọn "1" → Chọn file → Chọn câu hỏi
2. **Lưu output:** `python src/chatbot/chat_router.py ... > output.txt`
3. **Xem dữ liệu:** `cat data/processed/*.json | python -m json.tool`
4. **Dùng file cũ:** `data/processed/cv_data_manual_gap.json` (đã có sẵn)

---

## 🎓 TIẾP THEO (Sau khi test)

1. **Hiểu code:** Đọc `src/chatbot/chat_router.py` để thấy logic
2. **Thêm câu hỏi:** Modify `chat_router.py` để thêm intent mới
3. **Tích hợp UI:** Thêm Streamlit/Flask frontend
4. **Deploy:** Docker, Hugging Face Spaces, v.v.

---

## 📞 HỖ TRỢ

Xem file chi tiết: **TESTING_GUIDE.md**

---

**Bây giờ hãy chạy:**
```bash
cd d:/TTTN/Project/Resume_recommendation/career_chatbot
python test_chatbot_interactive.py
```

## Chúc bạn test thành công! 🎉
