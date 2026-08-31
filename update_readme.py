import json
import os
import requests
from datetime import datetime, timedelta, timezone


# ============================================================
# 설정
# ============================================================

LOG_FILE = "study_logs.json"

GITHUB_USERNAME = "juyangjin"

# GitHub Actions에서 자동으로 제공되는 토큰 사용
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN 환경변수가 없습니다.")


# ============================================================
# 시간 설정
# ============================================================

FIRST_COMMIT_MINUTES = 30
MAX_GAP_MINUTES = 60
SESSION_GAP_MINUTES = 120
MAX_DAILY_MINUTES = 8 * 60

KST = timezone(timedelta(hours=9))


# ============================================================
# GitHub API
# ============================================================

def get_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }


# ============================================================
# Repository 조회
# ============================================================

def fetch_repositories(username):
    """
    GitHub 사용자의 모든 public repository 조회
    """

    url = f"https://api.github.com/users/{username}/repos"

    repositories = []
    page = 1

    while True:

        params = {
            "per_page": 100,
            "page": page,
            "sort": "updated",
            "direction": "desc"
        }

        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            print(
                f"Repository 조회 실패: "
                f"{response.status_code}"
            )
            print(response.text)
            break

        data = response.json()

        if not data:
            break

        repositories.extend(
            repo["name"]
            for repo in data
        )

        if len(data) < 100:
            break

        page += 1

    return repositories


# ============================================================
# Commit 조회
# ============================================================

def fetch_commits(
    username,
    repo_name,
    since,
    until
):
    """
    특정 Repository의 특정 기간 Commit 조회
    """

    url = (
        f"https://api.github.com/repos/"
        f"{username}/{repo_name}/commits"
    )

    commits = []
    page = 1

    while True:

        params = {
            "since": since.isoformat(),
            "until": until.isoformat(),
            "per_page": 100,
            "page": page
        }

        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=30
        )

        # 빈 Repository
        if response.status_code == 409:
            return []

        if response.status_code != 200:
            print(
                f"[{repo_name}] "
                f"Commit 조회 실패: "
                f"{response.status_code}"
            )
            print(response.text)
            break

        data = response.json()

        if not data:
            break

        commits.extend(data)

        if len(data) < 100:
            break

        page += 1

    return commits


# ============================================================
# Commit 시간 추출
# ============================================================

def get_commit_times(commits):
    """
    GitHub Commit의 작성 시간을 추출하고
    한국 시간(KST)으로 변환
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
                date_string.replace(
                    "Z",
                    "+00:00"
                )
            )

            commit_time = commit_time.astimezone(
                KST
            )

            times.append(commit_time)

        except ValueError:
            continue

    return sorted(times)


# ============================================================
# 날짜별 Commit 그룹화
# ============================================================

def group_commits_by_date(commit_times):

    commits_by_date = {}

    for commit_time in commit_times:

        date = commit_time.strftime(
            "%Y-%m-%d"
        )

        commits_by_date.setdefault(
            date,
            []
        ).append(commit_time)

    return commits_by_date


# ============================================================
# Repository별 공부시간 계산
# ============================================================

def calculate_repository_study_time(
    commit_times
):
    """
    Repository 하나의 공부시간 계산

    - Commit 1개 → 30분
    - Commit 간격 → 최대 60분
    - 2시간 이상 간격 → 새로운 세션
    - 하루 최대 8시간
    """

    daily_minutes = {}

    commits_by_date = group_commits_by_date(
        commit_times
    )

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

                if gap >= SESSION_GAP_MINUTES:

                    minutes += FIRST_COMMIT_MINUTES

                else:

                    minutes += min(
                        gap,
                        MAX_GAP_MINUTES
                    )

        minutes = min(
            round(minutes),
            MAX_DAILY_MINUTES
        )

        daily_minutes[date] = minutes

    return daily_minutes


# ============================================================
# 전체 공부시간 계산
# ============================================================

def calculate_total_study_time(
    all_commit_times
):
    """
    모든 Repository의 Commit 시간을 합쳐서
    전체 공부시간을 계산한다.

    Repository가 달라도 같은 시간대에
    작업한 경우 중복 계산하지 않는다.
    """

    if not all_commit_times:
        return {}

    all_commit_times.sort()

    commits_by_date = group_commits_by_date(
        all_commit_times
    )

    daily_minutes = {}

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

                if gap >= SESSION_GAP_MINUTES:

                    minutes += FIRST_COMMIT_MINUTES

                else:

                    minutes += min(
                        gap,
                        MAX_GAP_MINUTES
                    )

        minutes = min(
            round(minutes),
            MAX_DAILY_MINUTES
        )

        daily_minutes[date] = minutes

    return daily_minutes


# ============================================================
# JSON 저장
# ============================================================

def save_study_logs(
    logs,
    file_path
):

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

    if minutes <= 0:
        return "-"

    hours = minutes // 60
    mins = minutes % 60

    if hours == 0:
        return f"{mins}분"

    if mins == 0:
        return f"{hours}시간"

    return f"{hours}시간 {mins}분"


# ============================================================
# README 공부 기록 생성
# ============================================================

def generate_weekly_study_chart(
    repository_logs,
    total_logs
):

    today = datetime.now(KST).date()

    dates = [
        today - timedelta(days=i)
        for i in range(6, -1, -1)
    ]

    date_strings = [
        date.strftime("%Y-%m-%d")
        for date in dates
    ]

    chart = "## 📊 최근 7일 공부 기록\n\n"

    # --------------------------------------------------------
    # 전체 공부시간
    # --------------------------------------------------------

    total_week_minutes = sum(
        total_logs.get(date, 0)
        for date in date_strings
    )

    chart += (
        f"### ⏱️ 총 공부시간 "
        f"**{format_minutes(total_week_minutes)}**\n\n"
    )

    # --------------------------------------------------------
    # 전체 공부시간 표
    # --------------------------------------------------------

    chart += (
        "| 구분 | "
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

    total_values = [
        format_minutes(
            total_logs.get(date, 0)
        )
        for date in date_strings
    ]

    chart += (
        "| **전체** | "
        + " | ".join(total_values)
        + f" | **{format_minutes(total_week_minutes)}** |\n"
    )

    chart += "\n"

    # --------------------------------------------------------
    # Repository별 공부시간
    # --------------------------------------------------------

    chart += "### 📚 Repository별 기록\n\n"

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

    for repo, daily_logs in sorted(
        repository_logs.items()
    ):

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
            )

        chart += (
            f"| {repo} | "
            + " | ".join(values)
            + f" | **{format_minutes(repo_total)}** |\n"
        )

    chart += "\n"

    chart += (
        "> 💡 GitHub Commit 시간을 기준으로 자동 계산됩니다. "
        "Commit 1개는 30분, Commit 간격은 최대 60분까지 "
        "인정합니다. 2시간 이상 공백은 새로운 세션으로 "
        "계산하며 하루 최대 8시간으로 제한합니다. "
        "전체 공부시간은 Repository 간 중복 시간을 제거합니다.\n"
    )

    return chart


# ============================================================
# README 업데이트
# ============================================================

def update_readme():

    print("📥 GitHub Repository 조회 중...")

    repositories = fetch_repositories(
        GITHUB_USERNAME
    )

    print(
        f"✅ Repository {len(repositories)}개 발견"
    )

    # --------------------------------------------------------
    # 최근 7일 조회
    # --------------------------------------------------------

    today = datetime.now(KST)

    since = (
        today - timedelta(days=7)
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    until = today + timedelta(days=1)

    repository_logs = {}

    all_commit_times = []

    # --------------------------------------------------------
    # Repository별 처리
    # --------------------------------------------------------

    for repo in repositories:

        print(
            f"🔍 [{repo}] Commit 조회 중..."
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

        if not commit_times:
            continue

        # Repository별 공부시간
        daily_minutes = (
            calculate_repository_study_time(
                commit_times
            )
        )

        if daily_minutes:

            repository_logs[
                repo
            ] = daily_minutes

        # 전체 계산용 Commit
        all_commit_times.extend(
            commit_times
        )

        repo_total = sum(
            daily_minutes.values()
        )

        print(
            f"   → {format_minutes(repo_total)}"
        )

    # --------------------------------------------------------
    # 전체 공부시간
    # --------------------------------------------------------

    total_logs = calculate_total_study_time(
        all_commit_times
    )

    total_minutes = sum(
        total_logs.values()
    )

    print(
        "\n⏱️ 전체 공부시간: "
        f"{format_minutes(total_minutes)}"
    )

    # --------------------------------------------------------
    # JSON 저장
    # --------------------------------------------------------

    logs = {
        "repositories": repository_logs,
        "total": total_logs
    }

    save_study_logs(
        logs,
        LOG_FILE
    )

    # --------------------------------------------------------
    # README 고정 영역
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Weekly chart
    # --------------------------------------------------------

    weekly_chart = generate_weekly_study_chart(
        repository_logs,
        total_logs
    )

    # --------------------------------------------------------
    # README 저장
    # --------------------------------------------------------

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

    print(
        "\n🎉 README 업데이트 완료!"
    )


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    update_readme()
