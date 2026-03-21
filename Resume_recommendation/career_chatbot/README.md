# Career Chatbot

Huong dan nhanh de chay luong:

`CV PDF -> trich xuat thong tin -> match voi job tu parquet NLP -> chatbot goi y -> hoi dap tiep`

## 1. Du lieu dang su dung

Pipeline hien tai dang doc tu cac nguon sau:

- `Resume_recommendation/career_chatbot/data/raw/cv_samples/Resume.pdf`
- `Resume_recommendation/career_chatbot/data/raw/resume_data.csv`
- `outputs_preprocessing_v2/artifacts/jobs_chatbot_ready_v2.parquet`
- `outputs_preprocessing_v2/artifacts/jobs_chatbot_sections_v2.parquet`

Luu y:

- Thu muc `cv_samples` hien co the chua nhieu file PDF. Pipeline se tu resolve file CV hop le gan nhat.
- Chatbot khong con phu thuoc vao bo `data` cu cua chatbot de goi y job.

## 2. Cai moi truong

Tu thu muc repo:

```powershell
cd C:\Users\home\Documents\GitHub\Chatbot_newv1.2
python -m pip install -r Resume_recommendation/career_chatbot/req.txt
```

Neu muon chatbot goi LLM qua Ollama:

```powershell
ollama list
setx OLLAMA_MODEL "llama3.2:1b"
```

Co the thay bang:

- `gemma3:1b` neu uu tien toc do
- `llama3.1:8b` neu uu tien chat luong hon

## 3. Chay luong tu CV vao den gap result

Lenh smoke test end-to-end:

```powershell
python Resume_recommendation/career_chatbot/src/evaluation/evaluate_cases.py
```

Lenh nay se:

1. Doc CV PDF
2. Trich xuat email, phone, skills, target role
3. Match truc tiep voi jobs trong 2 file parquet
4. Tao ket qua gap analysis

File output mac dinh:

- `Resume_recommendation/career_chatbot/data/processed/resume_pdf_smoke_gap.json`

## 4. Chay chatbot tu ket qua CV da xu ly

Chuyen vao thu muc chatbot:

```powershell
cd C:\Users\home\Documents\GitHub\Chatbot_newv1.2\Resume_recommendation\career_chatbot
```

### Cac cau hoi nen test dau tien

```powershell
python src/chatbot/chat_router.py --question "CV của tôi phù hợp với vị trí nào nhất?" --gap_result "data/processed/resume_pdf_smoke_gap.json"
python src/chatbot/chat_router.py --question "CV của tôi nên học thêm kỹ năng gì?" --gap_result "data/processed/resume_pdf_smoke_gap.json"
python src/chatbot/chat_router.py --question "Tôi cần học gì trong Excel để theo Data Analyst?" --gap_result "data/processed/resume_pdf_smoke_gap.json"
python src/chatbot/chat_router.py --question "CV này nên apply job nào trước?" --gap_result "data/processed/resume_pdf_smoke_gap.json"
```

### Chay chat nhieu luot trong cung mot session

```powershell
python src/chatbot/chat_router.py --interactive --question "CV của tôi phù hợp với vị trí nào nhất?" --gap_result "data/processed/resume_pdf_smoke_gap.json"
```

Sau do co the hoi tiep ngay trong cung session:

- `Tôi nên học thêm kỹ năng gì?`
- `SQL cần tới mức nào để apply Data Analyst?`
- `CV này nên apply job nào trước?`
- `So sánh với Chuyên Viên Power BI,Tableau`

## 5. Cac mode chat

`chat_router.py` hien ho tro:

- `--mode auto`
- `--mode fast`
- `--mode thinking`

Goi y:

- Dung `fast` khi demo hoac muon phan hoi nhanh
- Dung `thinking` khi can cau tra loi ky hon
- Dung `auto` neu muon router tu chon

Vi du:

```powershell
python src/chatbot/chat_router.py --mode fast --question "CV của tôi nên học thêm kỹ năng gì?" --gap_result "data/processed/resume_pdf_smoke_gap.json"
```

## 6. Hanh vi chatbot hien tai

Chatbot duoc toi uu theo huong:

- uu tien tra loi dua tren `gap_result` va du lieu job that
- chi goi LLM khi can dien dat tu nhien hon
- mac dinh tra loi vua du
- chi di sau hon neu nguoi dung hoi tiep

Mot so nhom cau hoi da ho tro tot:

- role fit: `CV của tôi phù hợp với vị trí nào nhất?`
- skill gap: `Tôi nên học thêm kỹ năng gì?`
- skill deep-dive: `SQL cần tới mức nào để apply Data Analyst?`
- job fit: `CV này nên apply job nào trước?`
- HR screening/shortlist

## 7. Neu Ollama cham hoac loi

Neu thay timeout khi goi Ollama:

- thu `--mode fast`
- doi sang model nhe hon, vi du `llama3.2:1b` hoac `gemma3:1b`
- hoi ngan hon, tranh nhieu context trong mot cau

Neu khong goi duoc LLM, chatbot van co the fallback theo `gap_result`.

## 8. Tep chinh

- Core chat: `Resume_recommendation/career_chatbot/src/chatbot/chat_router.py`
- Trich xuat CV: `Resume_recommendation/career_chatbot/src/cv_processing/extract_cv_info.py`
- Match job/gap: `Resume_recommendation/career_chatbot/src/matching/gap_analysis.py`
- Smoke test: `Resume_recommendation/career_chatbot/src/evaluation/evaluate_cases.py`

## 9. Flow de dua len UX

Flow goi y:

1. User tai CV len
2. He thong chay `evaluate_cases.py` hoac pipeline tuong duong
3. Tao `gap_result`
4. Mo khung chat
5. Goi y cac cau hoi dau tien, vi du:
   - `CV của tôi phù hợp với vị trí nào nhất?`
   - `Tôi nên học thêm kỹ năng gì?`
   - `CV này nên apply job nào trước?`
6. Khi user hoi tiep, chatbot tiep tuc dua tren cung CV va cung ket qua match do
