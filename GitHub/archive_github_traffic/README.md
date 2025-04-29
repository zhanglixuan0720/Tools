# GitHub Traffic Archiver

**GitHub Traffic Archiver** is an automation tool designed to periodically fetch and archive GitHub repository traffic data (specifically clone statistics). It stores the data locally as JSON files and synchronizes it with a NocoDB online database.

> **only support clones now**
---

## Features

- Supports traffic data collection for multiple GitHub repositories  
- Local JSON file storage  
- Synchronization with NocoDB online database  
- Configurable archiving interval  
- Full logging support  

---

## System Requirements

- Python 3.7+  
- `pip` package manager  

---

## Installation

1. Clone or download this project locally.

2. Install the required packages:

```bash
pip install requests PyYAML
```

3. Create the configuration file `config.yaml`:

```yaml
# GitHub Repository Configuration
repo_metadata:
  - username: "your-github-username"
    repository: "your-repo-name"
    token: "your-github-token"
  # Add more repositories as needed

# NocoDB Remote Database Configuration
remote_database_metadata:
  url: "your-nocodb-url"
  table_id: "your-table-id"
  token: "your-nocodb-token"

# Local Storage Configuration
local_database_metadata:
  path: "traffic_data"

# Archiving Interval (in days)
archiver_period: 7
```

---

## Configuration Details

### How to Get a GitHub Token

1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens → Fine-grained Personal Access Tokens  
2. Click **"Generate new token"**  
3. Enable `Repository administration` and `Metadata` with **read access**  
4. Generate and copy the token  

### NocoDB Configuration

1. Create a table in NocoDB with the following columns:
   - `Repository` (Text)
   - `Username` (Text)
   - `Link` (Text)
   - `Date` (Date)
   - `Count` (Number)
   - `Uniques` (Number)

2. Obtain the NocoDB API token and the target table ID  


---

## Run

Start the archiver using:

```bash
python github_traffic_archiver.py
```

---

## Logging

- Logs are saved under `logs/github_traffic_archiver.log`
- Includes runtime status and error messages

---

## Data Storage

- Data is stored locally in the `traffic_data` directory (can be changed in config)
- Stored as JSON files, organized by repository
- Also uploaded to NocoDB for online access

---

## Notes

- The free plan for NocoDB tables supports **up to 10,000 records**; exceeding this will cause upload errors
- NocoDB rate limits API requests to **5 requests per second**
- By default, the NocoDB table starts empty; whether a record is uploaded is tracked by the `log2online_db` field in the local file
- Re-uploading already-synced records will create **duplicates** (not overwrite existing records)
- The necessary folder structure will be created automatically on first run

