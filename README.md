# QualsSync

**QualsSync** is a GUI tool for mapping and uploading competencies from Aerolog (currently an Excel export) to Gliding App via API. 


---

## 🚀 Features

- Load Tech Quals from Excel files (`.xlsx`), previously output from Aerolog
- Visual tree-based mapping from spreadsheet columns to API endpoints
- Save/load mapping profiles
- Upload to Gliding App


---

## 🖥️ Requirements

- Python 3.13+
- [Poetry](https://python-poetry.org/) (for dependency and packaging management)
- Windows (if building the `.exe`)

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/QualsSync.git
cd QualsSync
```

### 2. Install Dependencies

Using Poetry:

```bash
poetry install
```

Or using pip:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Create a config file from the template:

```bash
cp config.json.template config.json
```

Edit `config.json`:

```json
{
  "server": "https://your-api-server.com",
  "api_key": "your-api-key"
}
```

---

## ▶️ Running the App (Development Mode)

```bash
python gui.py
```

Or use VSCode provided launch.json config to debug.

Make sure `config.json` exists in the same folder.

---

## 🧱 Building a Standalone Executable

### For Windows users:

Run the powershell script:

```bash
build.ps1
```

This will:
- Generate `requirements.txt` using `pipreqs`
- Build an `.exe` using `pyinstaller`
- Rename the output to `QualsSync.exe` (with version number - or DEV_VERSION locally)
- Copy `config.json.template` as `config.json` into `dist/`

---
