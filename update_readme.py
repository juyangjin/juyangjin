import json
import requests
from datetime import datetime, timedelta

# JSON 파일 경로
LOG_FILE = "study_logs.json"

# GitHub 사용자 정보
GITHUB_USERNAME = "juyangjin"
GITHUB_TOKEN = "your_github_personal_access_token"  # 필수: 토큰 발급 필요

# GitHub API를 통해 레포지토리 목록 가져오기
def fetch_repositories(username):
    url = f"https://api.github.com/users/{username}/repos"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        repos = response.json()
        return [repo['name'] for repo in repos]
    else:
        print(f"Failed to fetch repositories: {response.status_code}")
        return []

# JSON 파일에서 학습 데이터 로드
def load_study_logs(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# JSON 파일에 학습 데이터 저장
def save_study_logs(logs, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4, ensure_ascii=False)

# 학습 데이터에 새 레포지토리 추가
def merge_new_repositories(logs, repositories):
    for repo in repositories:
        if repo not in logs:
            logs[repo] = {}  # 새로운 레포지토리는 빈 데이터로 추가
    return logs

# 오늘의 학습 데이터를 추가
def update_daily_log(logs, repo, hours):
    today = datetime.now().strftime("%Y-%m-%d")
    if repo not in logs:
        logs[repo] = {}
    logs[repo][today] = logs[repo].get(today, 0) + hours

# 최근 일주일 기록 생성 (총 학습 시간만 표시)
def generate_weekly_study_chart(logs):
    one_week_ago = datetime.now() - timedelta(days=7)
    date_range = [(one_week_ago + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    chart = ""
    for repo, log in logs.items():
        chart += f"### {repo}\n"
        
        total_hours = sum(log.get(date, 0) for date in date_range)
        chart += f"총 학습 시간: **{total_hours}시간**\n\n"
    
    return chart


# 학습 데이터 갱신 및 README 업데이트
def update_readme():
    # 학습 데이터 로드
    logs = load_study_logs(LOG_FILE)

    # GitHub에서 레포지토리 목록 가져오기
    repositories = fetch_repositories(GITHUB_USERNAME)

    # 새 레포지토리를 기존 데이터에 병합
    logs = merge_new_repositories(logs, repositories)

    # 오늘 학습 데이터 업데이트 (예시: 사용자 입력)
    update_daily_log(logs, "projcet", 1)

    # 데이터 저장
    save_study_logs(logs, LOG_FILE)

    # 주간 학습 기록 생성
    weekly_chart = generate_weekly_study_chart(logs)

    # 고정된 README 내용
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

## Kmove IT스페셜리스트 (2022.04 ~ 2022.12)
### [Kmove 과제 및 공부자료](https://github.com/juyangjin/2022_Kmove)
- 설명 : kmove 과정에서 공부한 자료들입니다.

## 📚 스파르타 코딩클럽 Spring&Kotlin 4기(2024.11~ 2025.3)
### [chapter1. 웹개발 희망편](https://github.com/DeaHyun0911/sparta-web-team)
- 설명 : 스파르타 코딩클럽 1주차 웹개발 과제

### [chapter3-1. 코드족(?)팀](https://github.com/cnux9/Newsfeed)
- 설명 : 스파르타 코딩클럽 7,8주차 기초프로젝트 일정관리앱 과제

### [chapter 4. 채찍의 민족](https://github.com/roqkfchqh/outsourcing)
- 설명 : 스파르타 코딩클럽 10주차 주특기 심화 프로젝트 아웃소싱 프로젝트 과제 

## 📚 스파르타 코딩클럽 JAVA 단기심화 4기(2025.9~ 2025.12)
## [프로젝트 1]
- 설명 : 
## [프로젝트 2]
- 설명 : 
## [프로젝트 3]
- 설명 : 

## 📑 과제 페이지
### [대학과제](https://github.com/juyangjin/BU-2017-2022)
- 설명: 대학 과제 및 프로젝트 작업물입니다.
"""

    # README 업데이트
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(fixed_content + "\n\n" + weekly_chart)

# 실행
update_readme()

