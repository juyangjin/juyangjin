```yaml
name: Update README

on:
  schedule:
    # 매일 한국시간 00:00
    # GitHub Actions는 UTC 기준
    - cron: "0 15 * * *"

  workflow_dispatch:

jobs:
  update-readme:
    runs-on: ubuntu-latest

    permissions:
      contents: write

    steps:

      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Run update script
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python update_readme.py

      - name: Commit and push changes
        run: |
          git config --global user.name "GitHub Actions Bot"
          git config --global user.email "actions@github.com"

          git add study_logs.json README.md

          if git diff --cached --quiet; then
            echo "변경사항이 없습니다."
          else
            git commit -m "Update weekly study chart and logs"
            git push
          fi
```
