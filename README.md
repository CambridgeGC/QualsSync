# QualsSync

**QualsSync** is a GUI tool for mapping and uploading Excel-based pilot account data to a structured API. It’s designed for gliding clubs or similar organizations that need to manage and sync member data from spreadsheets into an online system.

---

## 🚀 Features

- Load Tech Quals from Excel files (`.xlsx`), previously output from Aerolog
- Visual tree-based mapping from spreadsheet columns to API endpoints
- Filter and validate rows based on membership numbers and types
- Upload to the "Accounts" API endpoint
- Save/load mapping profiles
- Build into a standalone `.exe` for Windows

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

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

MIT License
