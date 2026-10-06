# Petition Studio

A focused Flask web app for students to draft, save, and download a multi-page petition to Parliament as a PDF.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

Open http://127.0.0.1:5000 in a browser.

The app includes local title suggestions, Student Parliament metadata, multi-select audiences, optional supporter numbers, logo upload, and multi-page PDF export. Petitions are stored locally in `petitions.db`. The title assistant does not send student content to an external AI service. Before public deployment, add authentication, encrypted storage, consent/privacy copy, moderation, and an organisation review workflow.
