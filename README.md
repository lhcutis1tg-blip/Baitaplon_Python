# Financial Red-Flag Detection

This project provides a Streamlit front-end and an analysis module to detect potential manipulation or anomalies in financial statements using standard techniques (Beneish M-Score, Benford's Law, CFO checks, and basic ratios).

Quick start

1. Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the Streamlit app:

```bash
streamlit run streamlit_app.py
```

3. Upload your CSV (see `sample_data.csv` for expected columns) and run analysis.

Files
- `analysis.py`: core analysis functions
- `streamlit_app.py`: UI to upload CSV and visualize results
- `sample_data.csv`: small sample dataset

Notes
- Functions are defensive to missing columns; provide common columns: `revenue`, `cogs`, `gross_profit`, `receivables`, `total_assets`, `total_liabilities`, `cfo`, `net_income`.
# Phân tích báo cáo tài chính doanh nghiệp

Đây là trang GitHub Pages đơn giản mô tả cách phân tích báo cáo tài chính trong doanh nghiệp.

## Cách dùng

- Đặt `index.html` ở thư mục gốc của repository.
- Kích hoạt GitHub Pages từ cài đặt repository, chọn branch `main` hoặc `gh-pages` và thư mục `/`.
- Truy cập trang GitHub Pages sau khi published.

## Nội dung

Trang trình bày:
- Mục tiêu phân tích báo cáo tài chính
- Các loại báo cáo chính
- Chỉ số quan trọng
- Quy trình phân tích
- Ví dụ minh họa
- Kết luận
- Phiên bản Markdown: `financial-report.md`
