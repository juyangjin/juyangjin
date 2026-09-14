import json
import os
import requests

from datetime import datetime, timedelta, timezone


# ============================================================
# 설정
# ============================================================

LOG_FILE = "dev_logs.json"

GITHUB_USERNAME = "juyangjin"
GITHUB_EMAIL = "wndid2008@gmail.com"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN 환경변수가 없습니다.")


# ============================================================
# 프로젝트 표시 이름
# ============================================================

PROJECT_NAMES = {
    "juyangjin/JAVA-s-Study": "Java Study",
    "juyangjin/Coding-Test": "Coding Test",
    "juyangjin/Code-Tree": "CodeTree",

    "swyp-5th-team9/backend": "모여볼",
    "swyp-web15-3team/backend": "술케줄",
}


# ============================================================
# Commit 작성자
# ============================================================

GITHUB_AUTHOR_NAMES = {
    "juyangjin",
    "Juyang_Jin",
    "Juyang Jin",
}

GITHUB_AUTHOR_EMAILS = {
    "wndid2008@gmail.com",
}


# ============================================================
# 개발시간 계산 기준
# ============================================================

# Commit이 하나뿐인 경우
FIRST_COMMIT_MINUTES = 30

# Commit 사이 최대 인정 시간
MAX_GAP_MINUTES = 60

# 이 시간 이상 공백이면 새로운 개발 세션
SESSION_GAP_MINUTES = 120

# 하루 최대 개발시간
MAX_DAILY_MINUTES = 8 * 60


# ============================================================
# 한국 시간
# ============================================================

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


def github_get(url, params=None):
    """
    GitHub API GET 공통 함수
    """

    response = requests.get(
        url,
        headers=get_headers(),
        params=params,
        timeout=30
    )

    if response.status_code != 200:

        print(
            f"GitHub API 요청 실패: "
            f"{response.status_code}"
        )

        print(response.text)

        return None

    return response.json()


# ============================================================
# 개인 Repository 조회
# ============================================================

def fetch_personal_repositories(username):
    """
    개인 계정의 Public Repository 조회
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

        data = github_get(
            url,
            params
        )

        if data is None:
            break

        if not data:
            break

        for repo in data:

            if not repo.get("private", False):

                repositories.append(
                    repo["full_name"]
                )

        if len(data) < 100:
            break

        page += 1

    return repositories


# ============================================================
# Commit Search를 이용한 Repository 발견
# ============================================================

def discover_repositories_from_commits(
    username,
    since,
    until
):
    """
    최근 Commit을 검색하여
    사용자가 실제로 Commit한 Repository를 찾는다.

    Organization Repository도 발견 가능하다.
    """

    url = "https://api.github.com/search/commits"

    repositories = set()

    page = 1

    while True:

        query = (
            f"author:{username} "
            f"committer-date:"
            f"{since.strftime('%Y-%m-%d')}.."
            f"{until.strftime('%Y-%m-%d')}"
        )

        params = {
            "q": query,
            "per_page": 100,
            "page": page
        }

        data = github_get(
            url,
            params
        )

        if data is None:
            break

        items = data.get(
            "items",
            []
        )

        if not items:
            break

        for item in items:

            repository = (
                item
                .get("repository", {})
                .get("full_name")
            )

            if repository:

                repositories.add(
                    repository
                )

        total_count = data.get(
            "total_count",
            0
        )

        # GitHub Search API 최대 1000개
        if (
            len(items) < 100
            or page * 100 >= min(
                total_count,
                1000
            )
        ):
            break

        page += 1

    return sorted(repositories)


# ============================================================
# 전체 Repository 발견
# ============================================================

def discover_all_repositories(
    username,
    since,
    until
):
    """
    개인 Repository + Commit Search 결과를 합친다.
    """

    repositories = set()

    # --------------------------------------------------------
    # 개인 Repository
    # --------------------------------------------------------

    print(
        "📂 개인 Repository 검색 중..."
    )

    personal_repositories = (
        fetch_personal_repositories(
            username
        )
    )

    repositories.update(
        personal_repositories
    )

    print(
        f"   → 개인 Repository "
        f"{len(personal_repositories)}개"
    )

    # --------------------------------------------------------
    # Commit Search
    # --------------------------------------------------------

    print(
        "🔎 최근 Commit에서 Repository 검색 중..."
    )

    commit_repositories = (
        discover_repositories_from_commits(
            username,
            since,
            until
        )
    )

    repositories.update(
        commit_repositories
    )

    print(
        f"   → Commit에서 "
        f"{len(commit_repositories)}개 발견"
    )

    return sorted(repositories)


# ============================================================
# 본인 Commit 판별
# ============================================================

def is_my_commit(commit):
    """
    GitHub 계정 / Git author 이름 / 이메일을 이용하여
    본인의 Commit인지 판단한다.

    우선순위:
    1. GitHub login
    2. Git author email
    3. Git author name
    """

    # --------------------------------------------------------
    # GitHub 계정
    # --------------------------------------------------------

    github_author = commit.get(
        "author"
    )

    if github_author:

        github_login = (
            github_author
            .get("login")
        )

        if github_login == GITHUB_USERNAME:
            return True

    # --------------------------------------------------------
    # Git author 정보
    # --------------------------------------------------------

    git_author = (
        commit
        .get("commit", {})
        .get("author", {})
    )

    git_name = (
        git_author
        .get("name", "")
        .strip()
    )

    git_email = (
        git_author
        .get("email", "")
        .strip()
        .lower()
    )

    # --------------------------------------------------------
    # 이메일 기준
    # --------------------------------------------------------

    if git_email in {
        email.lower()
        for email in GITHUB_AUTHOR_EMAILS
    }:
        return True

    # --------------------------------------------------------
    # 이름 기준
    # --------------------------------------------------------

    if git_name in GITHUB_AUTHOR_NAMES:
        return True

    return False


# ============================================================
# Repository Commit 조회
# ============================================================

def fetch_commits(
    repository,
    since,
    until
):
    """
    특정 Repository의 Commit 조회.

    GitHub login
    + Git author email
    + Git author name

    을 이용하여 본인의 Commit만 필터링한다.
    """

    url = (
        f"https://api.github.com/repos/"
        f"{repository}/commits"
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

        data = github_get(
            url,
            params
        )

        if data is None:
            break

        # 빈 Repository
        if not data:
            break

        for commit in data:

            # =================================================
            # 자동 README 업데이트 제외
            # =================================================

            message = (
                commit
                .get("commit", {})
                .get("message", "")
            )

            if message.startswith(
                "Update development log"
            ):
                continue

            if message.startswith(
                "Update weekly study chart and logs"
            ):
                continue

            # =================================================
            # 본인 Commit인지 확인
            # =================================================

            if not is_my_commit(commit):
                continue

            commits.append(
                commit
            )

        if len(data) < 100:
            break

        page += 1

    return commits


# ============================================================
# Commit 시간 추출
# ============================================================

def get_commit_times(commits):

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

            commit_time = (
                commit_time.astimezone(
                    KST
                )
            )

            times.append(
                commit_time
            )

        except ValueError:

            continue

    return sorted(times)


# ============================================================
# 중복 Commit 시간 제거
# ============================================================

def remove_duplicate_times(commit_times):
    """
    여러 Repository에서 같은 시간에 발생한 Commit을
    전체 개발시간 계산 시 중복으로 세지 않도록 제거한다.
    """

    if not commit_times:
        return []

    unique_times = []

    previous_time = None

    for commit_time in sorted(commit_times):

        if (
            previous_time is None
            or commit_time != previous_time
        ):

            unique_times.append(
                commit_time
            )

            previous_time = commit_time

    return unique_times


# ============================================================
# 날짜별 Commit 그룹화
# ============================================================

def group_commits_by_date(
    commit_times
):

    commits_by_date = {}

    for commit_time in commit_times:

        date = commit_time.strftime(
            "%Y-%m-%d"
        )

        commits_by_date.setdefault(
            date,
            []
        ).append(
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
    Commit 시간을 기반으로 개발시간을 추정한다.

    규칙:

    Commit 0개
        → 0분

    Commit 1개
        → 30분

    Commit 간격 < 2시간
        → 실제 간격을 인정하되 최대 60분

    Commit 간격 >= 2시간
        → 새로운 세션으로 판단
        → 새로운 Commit 30분 인정

    하루 최대
        → 8시간
    """

    daily_minutes = {}

    commits_by_date = (
        group_commits_by_date(
            commit_times
        )
    )

    for date, times in commits_by_date.items():

        if not times:
            continue

        times = sorted(
            times
        )

        # ----------------------------------------------------
        # 첫 Commit
        # ----------------------------------------------------

        minutes = FIRST_COMMIT_MINUTES

        # ----------------------------------------------------
        # 이후 Commit
        # ----------------------------------------------------

        for i in range(
            1,
            len(times)
        ):

            gap = (
                times[i]
                - times[i - 1]
            ).total_seconds() / 60

            # ------------------------------------------------
            # 2시간 이상 공백
            # → 새로운 세션
            # ------------------------------------------------

            if gap >= SESSION_GAP_MINUTES:

                minutes += (
                    FIRST_COMMIT_MINUTES
                )

            # ------------------------------------------------
            # 같은 세션
            # → 최대 60분 인정
            # ------------------------------------------------

            else:

                minutes += min(
                    gap,
                    MAX_GAP_MINUTES
                )

        # ----------------------------------------------------
        # 하루 최대 8시간
        # ----------------------------------------------------

        minutes = min(
            round(minutes),
            MAX_DAILY_MINUTES
        )

        if minutes > 0:

            daily_minutes[
                date
            ] = minutes

    return daily_minutes


# ============================================================
# 전체 개발시간 계산
# ============================================================

def calculate_total_development_time(
    all_commit_times
):
    """
    모든 Repository의 Commit을 합쳐
    전체 개발시간을 계산한다.

    여러 Repository에서 동시에 발생한 Commit은
    하나의 활동으로 취급한다.

    즉,

        backend 19:00
        frontend 19:05

    라면 전체 개발시간에서는
    5분의 간격만 계산한다.

    프로젝트별 시간은 각각 별도로 계산한다.
    """

    if not all_commit_times:
        return {}

    # --------------------------------------------------------
    # 동일 시간 Commit 제거
    # --------------------------------------------------------

    all_commit_times = (
        remove_duplicate_times(
            all_commit_times
        )
    )

    return calculate_daily_development_time(
        all_commit_times
    )


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
# 프로젝트 표시명
# ============================================================

def get_project_name(repository):

    if repository in PROJECT_NAMES:

        return PROJECT_NAMES[
            repository
        ]

    return repository


# ============================================================
# README 개발 기록
# ============================================================

def generate_weekly_development_chart(
    repository_logs,
    total_logs
):

    today = datetime.now(
        KST
    ).date()

    dates = [
        today - timedelta(days=i)
        for i in range(
            6,
            -1,
            -1
        )
    ]

    date_strings = [
        date.strftime(
            "%Y-%m-%d"
        )
        for date in dates
    ]

    chart = (
        "## 📊 최근 7일 개발 기록\n\n"
    )

    # ========================================================
    # 전체 개발시간
    # ========================================================

    total_week_minutes = sum(
        total_logs.get(
            date,
            0
        )
        for date in date_strings
    )

    chart += (
        f"### ⏱️ 총 개발시간 "
        f"**{format_minutes(total_week_minutes)}**\n\n"
    )

    # ========================================================
    # 전체 표
    # ========================================================

    chart += (
        "| 프로젝트 | "
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
            format_minutes(
                minutes
            )
        )

    chart += (
        "| **전체** | "
        + " | ".join(
            total_values
        )
        + f" | **{format_minutes(total_week_minutes)}** |\n"
    )

    chart += "\n"

    # ========================================================
    # 프로젝트별 기록
    # ========================================================

    chart += (
        "### 📚 프로젝트별 기록\n\n"
    )

    chart += (
        "| 프로젝트 | "
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

    for repository, daily_logs in sorted(
        repository_logs.items(),
        key=lambda item: get_project_name(
            item[0]
        )
    ):

        project_name = get_project_name(
            repository
        )

        values = []

        project_total = 0

        for date in date_strings:

            minutes = daily_logs.get(
                date,
                0
            )

            project_total += minutes

            values.append(
                format_minutes(
                    minutes
                )
            )

        chart += (
            f"| {project_name} | "
            + " | ".join(
                values
            )
            + f" | **{format_minutes(project_total)}** |\n"
        )

    chart += "\n"

    # ========================================================
    # 설명
    # ========================================================

    chart += (
        "> 💡 GitHub Commit 시간을 기준으로 "
        "개발 활동 시간을 추정합니다. "
        "Commit이 없는 날은 기록하지 않습니다. "
        "Commit 1개는 30분으로 인정하며, "
        "같은 개발 세션의 Commit 간격은 최대 60분까지 "
        "인정합니다. "
        "2시간 이상 공백이 발생하면 새로운 개발 세션으로 "
        "계산합니다. "
        "하루 최대 8시간으로 제한합니다. "
        "여러 Repository에서 동시에 발생한 Commit은 "
        "전체 개발시간 계산 시 중복으로 계산하지 않습니다. "
        "GitHub Actions의 자동 README 업데이트 Commit은 "
        "제외합니다.\n"
    )

    return chart


# ============================================================
# README 업데이트
# ============================================================

def update_readme():

    print(
        "🚀 개발 기록 업데이트 시작"
    )

    print()

    # --------------------------------------------------------
    # 최근 7일
    # --------------------------------------------------------

    today = datetime.now(
        KST
    )

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
        today.date()
        + timedelta(days=1),
        datetime.min.time(),
        tzinfo=KST
    )

    # --------------------------------------------------------
    # 전체 Repository 발견
    # --------------------------------------------------------

    repositories = (
        discover_all_repositories(
            GITHUB_USERNAME,
            since,
            until
        )
    )

    print()

    print(
        f"📦 총 {len(repositories)}개 "
        f"Repository 추적"
    )

    print()

    repository_logs = {}

    all_commit_times = []

    # --------------------------------------------------------
    # Repository별 처리
    # --------------------------------------------------------

    for repository in repositories:

        print(
            f"🔍 [{repository}]"
        )

        commits = fetch_commits(
            repository,
            since,
            until
        )

        if not commits:

            print(
                "   → 본인 Commit 없음"
            )

            continue

        commit_times = get_commit_times(
            commits
        )

        if not commit_times:

            print(
                "   → 유효한 Commit 없음"
            )

            continue

        # ----------------------------------------------------
        # Repository별 개발시간
        # ----------------------------------------------------

        daily_minutes = (
            calculate_daily_development_time(
                commit_times
            )
        )

        if daily_minutes:

            repository_logs[
                repository
            ] = daily_minutes

            repo_total = sum(
                daily_minutes.values()
            )

            print(
                f"   → Commit: "
                f"{len(commit_times)}개"
            )

            print(
                f"   → 개발시간: "
                f"{format_minutes(repo_total)}"
            )

        # ----------------------------------------------------
        # 전체 계산용
        # ----------------------------------------------------

        all_commit_times.extend(
            commit_times
        )

    # --------------------------------------------------------
    # 전체 개발시간
    # --------------------------------------------------------

    total_logs = (
        calculate_total_development_time(
            all_commit_times
        )
    )

    total_minutes = sum(
        total_logs.values()
    )

    print()

    print(
        f"⏱️ 전체 개발시간: "
        f"{format_minutes(total_minutes)}"
    )

    # --------------------------------------------------------
    # JSON 저장
    # --------------------------------------------------------

    logs = {
        "repositories": repository_logs,
        "total": total_logs
    }

    save_dev_logs(
        logs
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
- 설명: 스포츠 펍 파인더 앱 서비스

### [술케줄(2026.08 ~ )](https://github.com/swyp-web15-3team/backend)
- 설명: 한일 위스키 가격 비교와 면세 쇼핑 플랜 웹 서비스
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

    print()
    print(
        "🎉 README 업데이트 완료!"
    )


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    update_readme()
