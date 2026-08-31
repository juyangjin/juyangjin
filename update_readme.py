```python
import json
import requests
from datetime import datetime, timedelta, timezone

# ============================================================
# 설정
# ============================================================

LOG_FILE = "study_logs.json"

GITHUB_USERNAME = "juyangjin"
GITHUB_TOKEN = "your_github_personal_access_token"

# 커밋이 하나뿐인 날 → 기본 인정 시간
FIRST_COMMIT_MINUTES = 30

# 커밋 사이의 최대 인정 시간
MAX_GAP_MINUTES = 60

# 하루 최대 인정 공부시간
MAX_DAILY_MINUTES = 8 * 60


# ============================================================
# GitHub API
# ============================================================

def fetch_repositories(username):
    """
    GitHub 사용자의 모든 public repository 가져오기
    """

    url = f"https://api.github.com/users/{username}/repos"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    params = {
        "per_page": 100,
        "page": 1
    }

    repositories = []

    while True:
        response = requests.get(
            url,
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            print(
                f"Failed to fetch repositories: "
                f"{response.status_code}"
            )
            print(response.text)
            return repositories

        data = response.json()

        if not data:
            break

        repositories.extend(
            repo["name"]
            for repo in data
        )

        params["page"] += 1

    return repositories


def fetch_commits(username, repo_name, since, until):
    """
    특정 repository의 특정 기간 커밋 가져오기
    """

    url = (
        f"https://api.github.com/repos/"
        f"{username}/{repo_name}/commits"
    )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    params = {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "per_page": 100,
        "page": 1
    }

    commits = []

    while True:

        response = requests.get(
            url,
            headers=headers,
            params=params
        )

        if response.status_code == 409:
            # 빈 repository
            return []

        if response.status_code != 200:
            print(
                f"[{repo_name}] "
                f"Failed to fetch commits: "
                f"{response.status_code}"
            )
            return commits

        data = response.json()

        if not data:
            break

        commits.extend(data)

        if len(data) < 100:
            break

        params["page"] += 1

    return commits


# ============================================================
# 커밋 시간 처리
# ============================================================

def get_commit_times(commits):
    """
    GitHub commit timestamp를 datetime으로 변환
    """

    times = []

    for commit in commits:

        date_string = (
            commit
            .get("commit", {})
            .get("author", {})
            .get("date")
        )

        if not date_string:
            continue

        try:
            commit_time = datetime.fromisoformat(
                date_string.replace("Z", "+00:00")
            )

            times.append(commit_time)

        except ValueError:
            continue

    return sorted(times)


def calculate_daily_minutes(commit_times):
    """
    커밋 시간 간격을 이용해 공부시간 계산

    규칙:
    - 커밋이 하나뿐이면 30분
    - 커밋 사이 간격은 최대 60분만 인정
    - 하루 최대 8시간
    """

    daily_minutes = {}

    # 날짜별로 커밋 분리
    commits_by_date = {}

    for commit_time in commit_times:

        # 한국 시간으로 변환
        korea_time = commit_time.astimezone(
            timezone(timedelta(hours=9))
        )

        date = korea_time.strftime("%Y-%m-%d")

        commits_by_date.setdefault(
            date,
            []
        ).append(korea_time)

    # 날짜별 계산
    for date, times in commits_by_date.items():

        times.sort()

        if len(times) == 1:

            minutes = FIRST_COMMIT_MINUTES

        else:

            minutes = 0

            for i in range(1, len(times)):

                gap = (
                    times[i] - times[i - 1]
                ).total_seconds() / 60

                # 최대 60분까지만 인정
                minutes += min(
                    gap,
                    MAX_GAP_MINUTES
                )

        # 하루 최대 8시간
        minutes = min(
            minutes,
            MAX_DAILY_MINUTES
        )

        daily_minutes[date] = round(minutes)

    return daily_minutes


# ============================================================
# Study Log
# ============================================================

def load_study_logs(file_path):

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except FileNotFoundError:

        return {}


def save_study_logs(logs, file_path):

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            logs,
            f,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# 시간 포맷
# ============================================================

def format_minutes(minutes):

    hours = minutes // 60
    mins = minutes % 60

    if hours == 0:
        return f"{mins}분"

    if mins == 0:
        return f"{hours}시간"

    return f"{hours}시간 {mins}분"


# ============================================================
# Weekly README
# ============================================================

def generate_weekly_study_chart(logs):

    today = datetime.now(
        timezone(timedelta(hours=9))
    ).date()

    dates = [
        today - timedelta(days=i)
        for i in range(6, -1, -1)
    ]

    date_strings = [
        date.strftime("%Y-%m-%d")
        for date in dates
    ]

    chart = "## 📊 최근 7일 공부 기록\n\n"

    chart += (
        "| Repository | "
        + " | ".join(
            date.strftime("%m/%d")
            for date in dates
        )
        + " | Total |\n"
    )

    chart += (
        "|---|"
        + "---:|" * 8
        + "\n"
    )

    grand_total = 0

    for repo, daily_logs in sorted(logs.items()):

        values = []

        repo_total = 0

        for date in date_strings:

            minutes = daily_logs.get(
                date,
                0
            )

            repo_total += minutes

            values.append(
                format_minutes(minutes)
                if minutes > 0
                else "-"
            )

        grand_total += repo_total

        chart += (
            f"| {repo} | "
            + " | ".join(values)
            + f" | **{format_minutes(repo_total)}** |\n"
        )

    chart += "\n"
    chart += (
        f"### ⏱️ 총 공부시간: "
        f"**{format_minutes(grand_total)}**\n\n"
    )

    chart += (
        "> 💡 GitHub 커밋 시간 기준으로 자동 계산됩니다. "
        "커밋 사이 최대 60분까지 공부시간으로 인정하며, "
        "하루 최대 8시간으로 제한합니다.\n"
    )

    return chart


# ============================================================
# README 업데이트
# ============================================================

def update_readme():

    print("📥 GitHub repository 가져오는 중...")

    repositories = fetch_repositories(
        GITHUB_USERNAME
    )

    print(
        f"✅ Repository {len(repositories)}개 발견"
    )

    logs = {}

    # 최근 7일보다 약간 넉넉하게 가져오기
    today = datetime.now(
        timezone(timedelta(hours=9))
    )

    since = today - timedelta(days=7)
    until = today + timedelta(days=1)

    for repo in repositories:

        print(
            f"🔍 [{repo}] 커밋 조회 중..."
        )

        commits = fetch_commits(
            GITHUB_USERNAME,
            repo,
            since,
            until
        )

        if not commits:
            continue

        commit_times = get_commit_times(
            commits
        )

        daily_minutes = calculate_daily_minutes(
            commit_times
        )

        if daily_minutes:

            logs[repo] = daily_minutes

            total = sum(
                daily_minutes.values()
            )

            print(
                f"   → {format_minutes(total)}"
            )

    # JSON 저장
    save_study_logs(
        logs,
        LOG_FILE
    )

    # README 고정 영역
    fixed_content = """# My GitHub Portfolio

👋 여기는 제가 공부한 내용과 프로젝트를 공유하는 공간이에요.

## 📚 코딩 테스트 레포지토리

### [백준, 프로그래머스](https://github.com/juyangjin/Coding-Test)
- 설명: 백준, 프로그래머스 알고리즘 문제 풀이를 다룹니다.

### [코드트리](https://github.com/juyangjin/Code-Tree)
- 설명: 코드트리 알고리즘 문제 풀이를 다룹니다.

## 🧠 개인 공부

### [이것이 자바다](https://github.com/juyangjin/JAVA-s-Study)
- 설명: '이것이 자바다' 도서를 기반으로 한 공부자료입니다.

## 🚀 현재 개발하고 유지 중인 서비스

### [모여볼(2026.06 ~ )](https://github.com/swyp-5th-team9/backend)
- 설명: 스포츠 펍 파인더 앱 '모여볼' 서비스

### [한일 주류 비교 웹사이트(2026.08 ~ )](https://github.com/swyp-web15-3team/backend)
- 설명: 현재 기획 단계
"""

    weekly_chart = generate_weekly_study_chart(
        logs
    )

    with open(
        "README.md",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            fixed_content
            + "\n\n"
            + weekly_chart
        )

    print("\n🎉 README 업데이트 완료!")


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    update_readme()
```
