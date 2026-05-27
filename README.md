# AI Job Application Automation

Fully automated morning job search and application system using Claude AI + Google Sheets.
Runs every day at **6:00 AM PST** via GitHub Actions — zero human intervention required.

---

## What It Does Every Morning

1. Searches LinkedIn, Indeed, Handshake, Wellfound, and company career pages for fresh AI/ML, data science, and software engineering roles
2. Scores each job against your resume (1–10)
3. Applies automatically to any job with score ≥ 5 (skips roles requiring 5+ years experience)
4. Routes jobs with uncertain questions to **Pending Review** tab
5. Logs everything to Google Sheets
6. Emails you a summary (visible in GitHub Actions logs)

---

## Setup — Do This Once (About 2 Hours Total)

### Step 1 — Fork or Clone This Repo

```bash
git clone https://github.com/YOUR_USERNAME/job-automation.git
cd job-automation
```

### Step 2 — Get Your Claude API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up → **API Keys** → **Create new key**
3. Add $10 billing credit to start
4. Copy your API key — you'll need it in Step 5

### Step 3 — Set Up Google Sheets

**3a. Create the Google Sheet:**
1. Go to [sheets.google.com](https://sheets.google.com)
2. Create a new blank spreadsheet
3. Name it **"Job Application Tracker"**
4. Copy the Spreadsheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_LONG_ID_HERE/edit
   ```

**3b. Create a Google Service Account:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project → name it `job-automation`
3. Go to **APIs & Services** → **Enable APIs**
4. Enable: **Google Sheets API** and **Google Drive API**
5. Go to **Credentials** → **Create Credentials** → **Service Account**
6. Name it `job-automation-bot` → click Create
7. Click your new service account → **Keys** tab → **Add Key** → **JSON**
8. Download the JSON file — this is your `google_creds.json`

**3c. Share your Sheet with the service account:**
1. Open the JSON file — copy the `client_email` value (looks like `job-automation-bot@project.iam.gserviceaccount.com`)
2. Open your Google Sheet → Share → paste that email → give **Editor** access

### Step 4 — Update Your Resume

Open `resume.txt` and replace the placeholder content with your actual resume.
Keep it as plain text — no special formatting needed.

### Step 5 — Add GitHub Secrets

In your GitHub repo: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add ALL of these secrets:

| Secret Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Claude API key from Step 2 |
| `GOOGLE_SHEETS_CREDS` | **Paste the entire contents** of your google_creds.json file |
| `SPREADSHEET_ID` | The long ID from your Google Sheet URL |
| `APPLICANT_NAME` | Karthik Mannem |
| `APPLICANT_DEGREE` | Master of Science in Computer Science |
| `APPLICANT_UNIVERSITY` | California State University, Northridge |
| `APPLICANT_GRADUATION` | May 2026 |
| `APPLICANT_GPA` | 3.8 |
| `APPLICANT_WORK_AUTH` | F-1 OPT |
| `APPLICANT_NEEDS_SPONSORSHIP` | No |

> ⚠️ For `GOOGLE_SHEETS_CREDS`: open your downloaded JSON file, select ALL the text (Ctrl+A), copy it, and paste it as the secret value. Do not paste the file path — paste the actual JSON content.

### Step 6 — Test It Manually

In your GitHub repo → **Actions** tab → **Morning Job Application Run** → **Run workflow**

Watch the logs. After it finishes, open your Google Sheet — you should see:
- New tabs created automatically (Applied Jobs, Pending Review, Daily Progress, etc.)
- Rows populated with today's applications

### Step 7 — It Runs Automatically From Now On

The workflow fires every day at **6:00 AM PST** (2:00 PM UTC).
You don't need to do anything. Just check your Google Sheet each morning.

---

## Google Sheet Tabs

| Tab | Contents |
|---|---|
| Applied Jobs | Every application submitted automatically |
| Pending Review | Jobs needing your one-time input (visa/salary questions) |
| Daily Progress | One summary row per day |
| Interview Tracker | Populate manually when you get responses |
| Follow-Up Tracker | Auto-populated 7 days after each application |

---

## How to Check Yesterday's Run

1. Go to your repo → **Actions** tab
2. Click the most recent **Morning Job Application Run**
3. Click **apply** job → scroll through logs for full details
4. Download **run-logs** artifact for the full log file

---

## Customizing the System

**Change the match threshold (default: 5):**
In GitHub Secrets, add `MIN_MATCH_SCORE` = `6` (or any number 1-10)

**Change the experience limit (default: 4 years max):**
In GitHub Secrets, add `MAX_EXPERIENCE_YEARS` = `3`

**Change the daily application target (default: 100):**
In GitHub Secrets, add `DAILY_APPLICATION_TARGET` = `50`

**Change run time:**
In `.github/workflows/morning_run.yml`, edit the cron line:
```yaml
- cron: '0 14 * * *'   # 14:00 UTC = 6 AM PST
- cron: '0 13 * * *'   # 13:00 UTC = 5 AM PST
- cron: '0 15 * * *'   # 15:00 UTC = 7 AM PST
```

---

## Cost Estimate

| Item | Cost |
|---|---|
| Claude API (claude-opus-4-5) | ~$2–5 per daily run |
| Google Sheets API | Free |
| GitHub Actions | Free (2,000 min/month) |
| **Monthly total** | **~$60–150/month** |

---

## Files in This Repo

```
job-automation/
├── main.py              # Master orchestrator — runs the full pipeline
├── job_searcher.py      # Finds jobs using Claude + web search
├── resume_matcher.py    # Scores jobs and generates cover letters
├── sheets_logger.py     # Reads/writes Google Sheets
├── daily_summary.py     # Generates tomorrow's recommendations
├── config.py            # All settings and target role/location lists
├── resume.txt           # YOUR RESUME — update this with your actual content
├── requirements.txt     # Python dependencies
├── .env.example         # Template for local development
├── .gitignore           # Keeps secrets out of git
└── .github/
    └── workflows/
        └── morning_run.yml   # GitHub Actions schedule
```

---

## Important Notes

- **Never commit** `.env` or `google_creds.json` to git — they're in `.gitignore`
- The system **only logs Applied and Pending Review** jobs — skipped jobs are silently discarded
- **Cover letters** are generated fresh for every application — never reused
- If a job asks about visa sponsorship, salary, or security clearance → automatically sent to Pending Review for your manual decision
- Check **Pending Review** tab once a week and fill in the User Decision column
