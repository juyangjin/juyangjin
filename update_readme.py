import json
import requests
from datetime import datetime, timedelta

LOG_FILE = "study_logs.json"

GITHUB_USERNAME = "juyangjin"
GITHUB_TOKEN = "your_github_personal_access_token"


def fetch_repositories(username):
    url = f"https://api.github.com/users/{username}/repos?per_page=100"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        repos = response.json()
        return [repo["name"] for repo in repos]

    print(f"Failed to fetch repositories: {response.status_code}")
    print(response.text)
    return []


def load_study_logs(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_study_logs(logs, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4, ensure_ascii=False)


def merge_new_repositories(logs, repositories):
    for repo in repositories:
        if repo not in logs:
            logs[repo] = {}
    return logs


def update_daily_log(logs, repo, hours):
    today = datetime.now().strftime("%Y-%m-%d")

    if repo not in logs:
        logs[repo] = {}

    logs[repo][today] = logs[repo].get(today, 0) + hours


def generate_weekly_study_chart(logs):
    today = datetime.now()

    date_range = [
        (today - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(7)
    ]

    chart = ""

    for repo, log in logs.items():
        chart += f"### {repo}\n"

        total_hours = sum(
            log.get(date, 0)
            for date in date_range
        )

        chart += f"총 학습 시간: **{total_hours}시간**\n\n"

    return chart


def update_readme():
    logs = load_study_logs(LOG_FILE)

    repositories = fetch_repositories(GITHUB_USERNAME)

    logs = merge_new_repositories(logs, repositories)

    update_daily_log(logs, "project", 1)

    save_study_logs(logs, LOG_FILE)

    weekly_chart = generate_weekly_study_chart(logs)

    fixed_content = """# My GitHub Portfolio

👋 여기는 제가 공부한 내용과 프로젝트를 공유하는 공간이에요.

## 📚 코딩 테스트 레포지토리
### [백준,프로그래머스](https://github.com/juyangjin/Coding-Test)
- 설명: 백준, 프로그래머스 알고리즘 문제 풀이를 다룹니다.

### [코드트리](https://github.com/juyangjin/Code-Tree)
- 설명: 코드트리 알고리즘 문제 풀이를 다룹니다.

## 🧠 개인 공부
### [이것이 자바다](https://github.com/juyangjin/JAVA-s-Study)
- 설명 : '이것이 자바다' 도서를 기반으로 한 공부자료입니다.

## 현재 개발하고 유지 중인 서비스
### [모여볼(2026.06 ~ )](https://github.com/swyp-5th-team9/backend)
- 설명 : 스포츠 펍 파인더 앱 '모여볼' 서비스

### [한일 주류 비교 웹사이트(2026.08 ~ )](https://github.com/swyp-web15-3team/backend)
- 설명 : 현재 기획 단계
"""

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(fixed_content + "\n\n" + weekly_chart)


update_readme()
