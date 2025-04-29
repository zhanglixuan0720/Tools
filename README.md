# Tools

This repository provides multiple tools to help improve work efficiency. 

## Contents

- [Latex](./Latex)
    - **arrange.py**: A Python script that recursively merges LaTeX files by expanding all \input{} commands into a single .tex file, preserving the original structure and ignoring commented input lines.
- [GitHub](./GitHub)
    - **archive_github_traffic**: A Python script that periodically fetches GitHub clone traffic data for multiple repositories and archives it by saving to local JSON files and syncing to a NocoDB online database. Configurations such as repositories, storage paths, and logging options are defined via a YAML file.