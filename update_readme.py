import json
import os
import requests
from datetime import datetime, timedelta, timezone


# ============================================================
# 설정
# ============================================================

LOG_FILE = "dev_logs.json"

GITHUB_USERNAME = "juyangjin"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN 환경변수가 없습니다.")


# ============================================================
# 개발시간 계산 기준
# ============================================================

# 해당 날짜에 커밋이 1개뿐인 경우
FIRST_COMMIT_MINUTES = 30

# 커밋 사이에 인정하는 최대 시간
MAX_GAP_MINUTES = 60

# 이 시간 이상 커밋이 없으면 새로운 개발 세션으로 판단
SESSION_GAP_MINUTES = 120

# 하루 최대 개발시간
MAX_DAILY_MINUTES = 8 * 60

# 한국 시간
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
    GitHub 사용자의 public repository 전체 조회
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
    특정 repository의 특정 기간 commit 조회
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

        # 빈 repository
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
    GitHub commit 시간을 KST로 변환
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

            commit_time = commit_time.astimezone(KST)

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

        if date not in commits_by_date:
            commits_by_date[date] = []

        commits_by_date[date].append(
            commit_time
        )

    return commits_by_date


# ============================================================
# 개발시간 계산
# ============================================================

def calculate_daily_development_time(
    commit_times
):
    """
    Commit 기록을 기반으로 개발시간 계산

    규칙:

    1. 커밋이 없는 날
       → 기록하지 않음

    2. 커밋이 1개
       → 30분

    3. 커밋이 여러 개
       → 커밋 간격을 계산

    4. 커밋 간격
       → 최대 60분 인정

    5. 2시간 이상 공백
       → 새로운 개발 세션
       → 30분부터 다시 계산

    6. 하루 최대 8시간
    """

    daily_minutes = {}

    commits_by_date = group_commits_by_date(
        commit_times
    )

    for date, times in commits_by_date.items():

        if not times:
            continue

        times.sort()

        # ----------------------------------------------------
        # 커밋 하나
        # ----------------------------------------------------

        if len(times) == 1:

            minutes = FIRST_COMMIT_MINUTES

        # ----------------------------------------------------
        # 커밋 여러 개
        # ----------------------------------------------------

        else:

            minutes = FIRST_COMMIT_MINUTES

            for i in range(1, len(times)):

                gap = (
                    times[i] - times[i - 1]
                ).total_seconds() / 60

                # 2시간 이상이면 새로운 세션
                if gap >= SESSION_GAP_MINUTES:

                    minutes += FIRST_COMMIT_MINUTES

                else:

                    minutes += min(
                        gap,
                        MAX_GAP_MINUTES
                    )

        # 하루 최대 8시간
        minutes = min(
            round(minutes),
            MAX_DAILY_MINUTES
        )

        # 0분인 경우 저장하지 않음
        if minutes > 0:
            daily_minutes[date] = minutes

    return daily_minutes


# ============================================================
# 전체 개발시간 계산
# ============================================================

def calculate_total_development_time(
    all_commit_times
):
    """
    모든 Repository의 commit 시간을 합쳐
    전체 개발시간을 계산한다.

    Repository가 달라도 같은 시간대에
    작업했다면 중복 계산하지 않는다.
    """

    if not all_commit_times:
        return {}

    all_commit_times = sorted(
        all_commit_times
    )

    commits_by_date = group_commits_by_date(
        all_commit_times
    )

    daily_minutes = {}

    for date, times in commits_by_date.items():

        if not times:
            continue

        times.sort()

        if len(times) == 1:

            minutes = FIRST_COMMIT_MINUTES

        else:

            minutes = FIRST_COMMIT_MINUTES

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

        if minutes > 0:
            daily_minutes[date] = minutes

    return daily_minutes


# ============================================================
# JSON 저장
# ============================================================

def save_dev_logs(logs):

    with open(
        LOG_FILE,
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
# 시간 표시
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
# README 개발 기록 생성
# ============================================================

def generate_weekly_development_chart(
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

    chart = "## 📊 최근 7일 개발 기록\n\n"

    # ========================================================
    # 전체 개발시간
    # ========================================================

    total_week_minutes = sum(
        total_logs.get(date, 0)
        for date in date_strings
    )

    chart += (
        f"### ⏱️ 총 개발시간 "
        f"**{format_minutes(total_week_minutes)}**\n\n"
    )

    # ========================================================
    # 전체 개발시간 표
    # ========================================================

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

    total_values = []

    for date in date_strings:

        minutes = total_logs.get(
            date,
            0
        )

        total_values.append(
            format_minutes(minutes)
        )

    chart += (
        "| **전체** | "
        + " | ".join(total_values)
        + f" | **{format_minutes(total_week_minutes)}** |\n"
    )

    chart += "\n"

    # ========================================================
    # Repository별 개발시간
    # ========================================================

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
        "> 💡 GitHub Commit 시간을 기준으로 "
        "개발 활동 시간을 추정합니다. "
        "Commit 1개는 30분, Commit 간격은 최대 60분까지 "
        "인정합니다. 2시간 이상 공백은 새로운 세션으로 "
        "계산하며 하루 최대 8시간으로 제한합니다. "
        "전체 개발시간은 Repository 간 중복 시간을 제거합니다.\n"
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
    # KST 기준 최근 7일
    # --------------------------------------------------------

    today = datetime.now(KST)

    start_date = (
        today.date()
        - timedelta(days=6)
    )

    since = datetime.combine(
        start_date,
        datetime.min.time(),
        tzinfo=KST
    )

    until = datetime.combine(
        today.date() + timedelta(days=1),
        datetime.min.time(),
        tzinfo=KST
    )

    repository_logs = {}

    all_commit_times = []

    # --------------------------------------------------------
    # Repository별 조회
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

        # Repository별 개발시간
        daily_minutes = (
            calculate_daily_development_time(
                commit_times
            )
        )

        # 커밋이 실제로 있는 경우만 저장
        if daily_minutes:

            repository_logs[
                repo
            ] = daily_minutes

            repo_total = sum(
                daily_minutes.values()
            )

            print(
                f"   → {format_minutes(repo_total)}"
            )

        # 전체 개발시간 계산용
        all_commit_times.extend(
            commit_times
        )

    # --------------------------------------------------------
    # 전체 개발시간
    # --------------------------------------------------------

    total_logs = calculate_total_development_time(
        all_commit_times
    )

    total_minutes = sum(
        total_logs.values()
    )

    print(
        "\n⏱️ 전체 개발시간: "
        f"{format_minutes(total_minutes)}"
    )

    # --------------------------------------------------------
    # JSON 저장
    # --------------------------------------------------------

    logs = {
        "repositories": repository_logs,
        "total": total_logs
    }

    save_dev_logs(logs)

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
    # 개발 기록
    # --------------------------------------------------------

    development_chart = (
        generate_weekly_development_chart(
            repository_logs,
            total_logs
        )
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
            + development_chart
        )

    print(
        "\n🎉 README 업데이트 완료!"
    )


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    update_readme()
