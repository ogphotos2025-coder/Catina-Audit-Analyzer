# Cantina Audit-to-Alpha Engine — Setup Guide

## Prerequisites
- Python 3.11+
- An Anthropic API key (console.anthropic.com)

---

## 1. Clone / create the project folder

```bash
mkdir cantina-engine && cd cantina-engine
# copy app.py and requirements.txt here
```

## 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
# .venv\Scripts\activate         # Windows
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

PyMuPDF (imported as `fitz`) handles PDF parsing.
`anthropic` is the official SDK — no LangChain overhead needed.

## 4. Set your API key

**Option A — Environment variable (recommended for CI/local)**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."       # Mac/Linux
set ANTHROPIC_API_KEY=sk-ant-...            # Windows CMD
$env:ANTHROPIC_API_KEY="sk-ant-..."         # PowerShell
```

**Option B — .env file**
```bash
echo 'ANTHROPIC_API_KEY="sk-ant-..."' > .env
```
Then install python-dotenv and add `from dotenv import load_dotenv; load_dotenv()` 
to the top of app.py.

**Option C — Sidebar input**
Paste the key directly in the app's sidebar. Nothing is stored.

## 5. Run the app

```bash
streamlit run app.py
```

Opens at http://localhost:8501

---

## Deployment (optional)

### Streamlit Community Cloud (free)
1. Push to a public GitHub repo
2. Go to share.streamlit.io
3. Add ANTHROPIC_API_KEY in the Secrets manager (TOML format):
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t cantina-engine .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=sk-ant-... cantina-engine
```

---

## PDF Format Compatibility

| Audit Platform | Compatibility | Notes |
|----------------|--------------|-------|
| Cantina        | ✅ Excellent  | Standard H-01/C-01 format |
| Code4rena      | ✅ Excellent  | Structured finding sections |
| Sherlock       | ✅ Good       | Some variation in headers |
| Custom audits  | ⚠️ Variable  | Works if severity labels present |
| Scanned PDFs   | ❌ No         | Requires OCR preprocessing |

---

## Troubleshooting

**"No findings detected"** — The PDF uses non-standard section headers. 
Try: `strings yourfile.pdf | grep -i "critical\|high\|medium"` to check if text is extractable.

**JSON parse error** — Rare; Claude occasionally adds preamble. 
The app strips markdown fences automatically. If it persists, regenerate.

**Token limit** — Very large PDFs (100+ pages) with many findings: 
reduce "Max findings to use" slider to 2-3 in the sidebar.
