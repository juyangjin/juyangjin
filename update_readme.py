import os
import json
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict


# ============================================================
# 설정
# ============================================================

GITHUB_USERNAME = "juyangjin"
GITHUB_EMAIL = "wndid2008@gmail.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

PROJECT_NAMES = {
    "juyangjin/JAVA-s-Study": "Java Study",
    "juyangjin/Coding-Test": "Coding Test",
    "juyangjin/Code-Tree": "CodeTree",
    "swyp-5th-team9/backend": "모여볼",
    "swyp-web15-3team/backend": "술케줄",
}

# 모든 Branch를 조회할 Repository
BRANCH_TRACKING_REPOSITORIES = {
    "swyp-5th-team9/backend",
    "swyp-web15-3team/backend",
}

# 개발 시간 계산 규칙
COMMIT_MINUTES = 30
MAX_GAP_MINUTES = 60
SESSION_BREAK_MINUTES = 120
MAX_DAILY_MINUTES = 8 * 60

# README 자동 업데이트 커밋 제외
IGNORED_COMMIT_PREFIXES = (
    "Update development log",
    "Update weekly study chart and logs",
)

KST = timezone(timedelta(hours=9))

BASE_URL = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
}


# ============================================================
# GitHub API 공통 함수
# ============================================================

def github_get(url, params=None):
    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    if response.status_code != 200:
        print(
            f"   ⚠️ GitHub API 오류 "
            f"[{response.status_code}] {url}"
        )
        try:
            print(f"      → {response.json().get('message')}")
        except Exception:
            pass
        return None

    return response.json()


# ============================================================
# 본인 Commit인지 확인
# ============================================================

def is_my_commit(commit):
    """
    GitHub Commit의 여러 정보를 기준으로 본인 커밋인지 확인한다.

    우선순위:
    1. GitHub 로그인 username
    2. commit author email
    3. commit author name
    """

    author = commit.get("author") or {}
    git_author = commit.get("commit", {}).get("author") or {}

    github_login = author.get("login", "")
    author_email = git_author.get("email", "")
    author_name = git_author.get("name", "")

    # GitHub 계정으로 확인
    if github_login.lower() == GITHUB_USERNAME.lower():
        return True

    # Git email로 확인
    if author_email.lower() == GITHUB_EMAIL.lower():
        return True

    # 이름으로 확인
    normalized_name = author_name.strip().lower()

    allowed_names = {
        "juyangjin",
        "juyang_jin",
        "juyang jin",
    }

    if normalized_name in allowed_names:
        return True

    return False


# ============================================================
# Commit 제외 여부
# ============================================================

def is_ignored_commit(commit):
    message = (
        commit.get("commit", {})
        .get("message", "")
        .strip()
    )

    return message.startswith(IGNORED_COMMIT_PREFIXES)


# ============================================================
# 기본 Branch Commit 조회
# ============================================================

def fetch_default_branch_commits(repository, since, until):
    """
    일반 Repository는 기본 Branch만 조회한다.
    """

    url = f"{BASE_URL}/repos/{repository}/commits"

    commits = []
    page = 1

    while True:
        data = github_get(
            url,
            params={
                "since": since,
                "until": until,
                "per_page": 100,
                "page": page,
            },
        )

        if not data:
            break

        commits.extend(data)

        if len(data) < 100:
            break

        page += 1

    return commits


# ============================================================
# 모든 Branch 조회
# ============================================================

def fetch_all_branch_commits(repository, since, until):
    """
    지정된 프로젝트 Repository의 모든 Branch를 조회하고
    각 Branch의 Commit을 가져온다.

    같은 Commit이 여러 Branch에 존재할 수 있으므로
    SHA 기준으로 중복 제거한다.
    """

    print("   ⭐ 프로젝트 Repository → 모든 Branch 조회")

    branches_url = f"{BASE_URL}/repos/{repository}/branches"

    branches = []
    page = 1

    # --------------------------------------------------------
    # Branch 목록 가져오기
    # --------------------------------------------------------

    while True:
        data = github_get(
            branches_url,
            params={
                "per_page": 100,
                "page": page,
            },
        )

        if not data:
            break

        branches.extend(data)

        if len(data) < 100:
            break

        page += 1

    print(f"   → Branch {len(branches)}개 발견")

    if not branches:
        return []

    # --------------------------------------------------------
    # Branch별 Commit 조회
    # --------------------------------------------------------

    unique_commits = {}

    for branch in branches:
        branch_name = branch.get("name")

        if not branch_name:
            continue

        print(f"      └─ {branch_name}")

        commits_url = f"{BASE_URL}/repos/{repository}/commits"

        page = 1

        while True:
            data = github_get(
                commits_url,
                params={
                    "sha": branch_name,
                    "since": since,
                    "until": until,
                    "per_page": 100,
                    "page": page,
                },
            )

            if not data:
                break

            for commit in data:
                sha = commit.get("sha")

                if sha:
                    unique_commits[sha] = commit

            if len(data) < 100:
                break

            page += 1

    return list(unique_commits.values())


# ============================================================
# Repository Commit 조회
# ============================================================

def fetch_commits(repository, since, until):
    """
    모여볼 / 술케줄
        → 모든 Branch 조회

    그 외 Repository
        → 기본 Branch 조회
    """

    if repository in BRANCH_TRACKING_REPOSITORIES:
        commits = fetch_all_branch_commits(
            repository,
            since,
            until,
        )
    else:
        commits = fetch_default_branch_commits(
            repository,
            since,
            until,
        )

    # 본인 Commit + 자동 README Commit 제외
    filtered_commits = []

    for commit in commits:

        if is_ignored_commit(commit):
            continue

        if not is_my_commit(commit):
            continue

        filtered_commits.append(commit)

    # 혹시 API 결과 순서가 섞여 있어도 시간순 정렬
    filtered_commits.sort(
        key=lambda commit: commit["commit"]["author"]["date"]
    )

    return filtered_commits


# ============================================================
# 개인 Repository + Commit Repository 발견
# ============================================================

def discover_all_repositories():
    repositories = set()

    # --------------------------------------------------------
    # 개인 Repository 검색
    # --------------------------------------------------------

    print("📂 개인 Repository 검색 중...")

    url = f"{BASE_URL}/users/{GITHUB_USERNAME}/repos"

    page = 1

    while True:
        data = github_get(
            url,
            params={
                "per_page": 100,
                "page": page,
            },
        )

        if not data:
            break

        for repo in data:
            full_name = repo.get("full_name")

            if full_name:
                repositories.add(full_name)

        if len(data) < 100:
            break

        page += 1

    print(f"   → 개인 Repository {len(repositories)}개")

    # --------------------------------------------------------
    # 최근 Commit 검색
    # --------------------------------------------------------

    print("🔎 최근 Commit에서 Repository 검색 중...")

    search_url = f"{BASE_URL}/search/commits"

    data = github_get(
        search_url,
        params={
            "q": f"author:{GITHUB_USERNAME}",
            "per_page": 100,
        },
    )

    commit_repo_count = 0

    if data:
        items = data.get("items", [])

        for item in items:
            repo = (
                item
                .get("repository", {})
                .get("full_name")
            )

            if repo:
                repositories.add(repo)
                commit_repo_count += 1

    print(f"   → Commit에서 {commit_repo_count}개 발견")

    # --------------------------------------------------------
    # 반드시 추적해야 하는 프로젝트 Repository 추가
    # --------------------------------------------------------

    for repository in PROJECT_NAMES.keys():
        if repository not in repositories:
            repositories.add(repository)

    print(
        f"📌 등록된 프로젝트 "
        f"{len(PROJECT_NAMES)}개 추가"
    )

    return sorted(repositories)


# ============================================================
# 개발 시간 계산
# ============================================================

def calculate_development_time(commits):
    """
    Commit timestamp를 기준으로 개발 시간을 추정한다.

    규칙:
    - 첫 Commit: 30분
    - Commit 간격 <= 60분:
        실제 간격을 개발 시간으로 계산
    - Commit 간격 > 60분:
        30분 추가
    - Commit 간격 >= 2시간:
        새로운 Session으로 판단하여 30분 추가
    - 하루 최대 8시간
    """

    if not commits:
        return {}

    commits_by_date = defaultdict(list)

    for commit in commits:
        date_string = (
            commit["commit"]["author"]["date"]
        )

        dt = datetime.fromisoformat(
            date_string.replace("Z", "+00:00")
        ).astimezone(KST)

        date_key = dt.date()

        commits_by_date[date_key].append(dt)

    daily_minutes = {}

    for date, timestamps in commits_by_date.items():

        timestamps.sort()

        total_minutes = COMMIT_MINUTES

        for i in range(1, len(timestamps)):

            gap = (
                timestamps[i] - timestamps[i - 1]
            ).total_seconds() / 60

            if gap <= MAX_GAP_MINUTES:
                total_minutes += gap

            elif gap >= SESSION_BREAK_MINUTES:
                total_minutes += COMMIT_MINUTES

            else:
                total_minutes += COMMIT_MINUTES

        total_minutes = min(
            int(total_minutes),
            MAX_DAILY_MINUTES,
        )

        daily_minutes[date] = total_minutes

    return daily_minutes


# ============================================================
# 전체 개발 시간 계산
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
# README 프로젝트 이름
# ============================================================

def get_project_name(repository):
    """
    Repository가 PROJECT_NAMES에 등록되어 있으면
    지정된 프로젝트명을 사용한다.
    """

    return PROJECT_NAMES.get(
        repository,
        repository,
    )


# ============================================================
# README 생성
# ============================================================

def update_readme(daily_logs):
    """
    기존 README의 포트폴리오 영역 + 최근 7일 개발 기록을
    생성한다.

    프로젝트명은 PROJECT_NAMES의 값을 사용한다.
    """

    readme_path = "README.md"

    # --------------------------------------------------------
    # 최근 7일
    # --------------------------------------------------------

    today = datetime.now(KST).date()

    last_7_days = [
        today - timedelta(days=i)
        for i in range(6, -1, -1)
    ]

    # --------------------------------------------------------
    # 전체 시간
    # --------------------------------------------------------

    total_minutes = sum(
        daily_logs.get(day, 0)
        for day in last_7_days
    )

    # --------------------------------------------------------
    # README 작성
    # --------------------------------------------------------

    lines = []

    lines.append("# 👋 Juyang Jin")
    lines.append("")
    lines.append("백엔드 개발자를 준비하고 있습니다.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🛠️ Tech Stack")
    lines.append("")
    lines.append("- Java 17")
    lines.append("- Spring Boot")
    lines.append("- Spring Data JPA")
    lines.append("- QueryDSL")
    lines.append("- PostgreSQL")
    lines.append("- Redis")
    lines.append("- Docker")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 최근 7일 개발 기록")
    lines.append("")
    lines.append(
        f"**총 개발시간: "
        f"{format_minutes(total_minutes)}**"
    )
    lines.append("")

    # --------------------------------------------------------
    # 7일 개발 기록
    # --------------------------------------------------------

    for day in last_7_days:

        minutes = daily_logs.get(day, 0)

        if minutes > 0:
            time_text = format_minutes(minutes)
        else:
            time_text = "기록 없음"

        lines.append(
            f"- {day.strftime('%Y-%m-%d')} : "
            f"{time_text}"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📚 Projects")
    lines.append("")

    # 프로젝트명 표시
    for repository, project_name in PROJECT_NAMES.items():

        lines.append(
            f"- **{project_name}**"
        )

    lines.append("")

    with open(
        readme_path,
        "w",
        encoding="utf-8",
    ) as file:
        file.write("\n".join(lines))


# ============================================================
# 메인
# ============================================================

def main():

    if not GITHUB_TOKEN:
        print(
            "❌ GITHUB_TOKEN 환경변수가 없습니다."
        )
        return

    print("=" * 60)
    print("🚀 GitHub 개발시간 계산 시작")
    print("=" * 60)

    # --------------------------------------------------------
    # Repository 검색
    # --------------------------------------------------------

    repositories = discover_all_repositories()

    print(
        f"\n📦 총 {len(repositories)}개 Repository 추적"
    )

    # --------------------------------------------------------
    # 최근 7일 범위
    # --------------------------------------------------------

    today = datetime.now(KST).date()

    start_date = today - timedelta(days=6)

    since = datetime.combine(
        start_date,
        datetime.min.time(),
        tzinfo=KST,
    ).astimezone(timezone.utc).isoformat()

    until = datetime.combine(
        today + timedelta(days=1),
        datetime.min.time(),
        tzinfo=KST,
    ).astimezone(timezone.utc).isoformat()

    # --------------------------------------------------------
    # 전체 일자별 개발 시간
    # --------------------------------------------------------

    total_daily_logs = defaultdict(int)

    # --------------------------------------------------------
    # Repository별 조회
    # --------------------------------------------------------

    for repository in repositories:

        project_name = get_project_name(repository)

        print(
            f"\n🔍 [{project_name}]"
        )

        commits = fetch_commits(
            repository,
            since,
            until,
        )

        if not commits:
            print("   → 본인 Commit 없음")
            continue

        print(
            f"   → Commit: {len(commits)}개"
        )

        daily_time = calculate_development_time(
            commits
        )

        repository_total = 0

        for date, minutes in daily_time.items():

            total_daily_logs[date] += minutes
            repository_total += minutes

        print(
            f"   → 개발시간: "
            f"{format_minutes(repository_total)}"
        )

    # --------------------------------------------------------
    # 하루 전체 최대 8시간 적용
    # --------------------------------------------------------

    final_daily_logs = {}

    for date, minutes in total_daily_logs.items():

        final_daily_logs[date] = min(
            minutes,
            MAX_DAILY_MINUTES,
        )

    # --------------------------------------------------------
    # 전체 개발시간
    # --------------------------------------------------------

    total_minutes = sum(
        final_daily_logs.values()
    )

    print("\n" + "=" * 60)
    print(
        f"⏱️ 전체 개발시간: "
        f"{format_minutes(total_minutes)}"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # JSON 저장
    # --------------------------------------------------------

    json_data = {
        str(date): minutes
        for date, minutes in sorted(
            final_daily_logs.items()
        )
    }

    with open(
        "dev_logs.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            json_data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # --------------------------------------------------------
    # README 업데이트
    # --------------------------------------------------------

    update_readme(final_daily_logs)

    print("\n🎉 README 업데이트 완료!")


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    main()
