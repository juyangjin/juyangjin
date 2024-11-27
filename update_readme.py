from datetime import datetime, timedelta

# 고정된 README 내용
fixed_content = """# My GitHub Portfolio

👋 백석대학교 컴퓨터공학부 정보보호학과 졸업 후 백엔드 개발자를 목표로 공부하고 있습니다. :)  
모바일과 웹 위주의 공부를 하고 있고, 관심있는 언어는 C, JAVA 입니다.  

여기는 제가 공부한 내용과 프로젝트를 공유하는 공간이에요.

## 📚 코딩 테스트 레포지토리
### [백준,프로그래머스](https://github.com/juyangjin/Coding-Test)
- 설명: 백준, 프로그래머스 알고리즘 문제 풀이를 다룹니다.

### [코드트리](https://github.com/juyangjin/Code-Tree)
- 설명: 코드트리 알고리즘 문제 풀이를 다룹니다.

## 🧠 개인 공부
### [개인 공부](https://github.com/juyangjin/study)
- 설명: Java 위주 공부와 프로젝트입니다.

### [이것이 자바다](https://github.com/juyangjin/JAVA-s-Study)
- 설명 : '이것이 자바다' 도서를 기반으로 한 공부자료입니다.

## Kmove IT스페셜리스트 (2022.04 ~ 2022.12)
### [Kmove 과제 및 공부자료](https://github.com/juyangjin/2022_Kmove)
- 설명 : kmove 과정에서 공부한 자료들입니다.

## 📚 스파르타 코딩클럽(2024.11~ 2025.3)
### [1주차 웹개발 희망편](https://github.com/DeaHyun0911/sparta-web-team)
- 설명 : 스파르타 코딩클럽 1주차 웹개발 과제

### [개인 과제](https://github.com/juyangjin/personal_assignment)
- 설명: 스파르타 코딩클럽에서 진행한 개인과제

## 📑 과제 페이지
### [대학과제](https://github.com/juyangjin/BU-2017-2022)
- 설명: 대학 과제 및 프로젝트 작업물입니다.

## 그 외
### [이게뭐지?_에러모음](https://github.com/juyangjin/Error)
- 설명 : 에러가 안 풀렸을 때나, 미완성인 코드를 업로드하는 공간입니다.

## 📊 주간 학습 기록
"""

# 학습 데이터
study_logs = {
    "Coding-Test": {
        "2024-11-18": 2,
        "2024-11-19": 1,
        "2024-11-20": 3,
        "2024-11-22": 4,
        "2024-11-24": 5
    },
    "Code-Tree": {
        "2024-11-18": 1,
        "2024-11-19": 2,
        "2024-11-21": 1,
        "2024-11-23": 3
    },
    "Study": {
        "2024-11-20": 2,
        "2024-11-22": 3,
        "2024-11-24": 1
    }
}

# 이모지 매핑 함수
def get_emoji(hours):
    if hours == 0:
        return "⚪"
    elif 1 <= hours <= 2:
        return "🟢"
    elif 3 <= hours <= 4:
        return "🟡"
    else:
        return "🔴"

# 주간 학습 기록 생성
def generate_weekly_study_chart(logs):
    one_week_ago = datetime.now() - timedelta(days=7)
    date_range = [(one_week_ago + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    chart = ""
    for repo, log in logs.items():
        chart += f"### {repo}\n"
        chart += "학습 기록: "
        
        for date in date_range:
            hours = log.get(date, 0)
            chart += get_emoji(hours) + " "
        
        total_hours = sum(log.get(date, 0) for date in date_range)
        chart += f"\n\n총 학습 시간: **{total_hours}시간**\n\n"
    
    return chart

# 주간 학습 기록 생성
weekly_chart = generate_weekly_study_chart(study_logs)

# README 업데이트
with open("README.md", "w", encoding="utf-8") as f:
    f.write(fixed_content)
    f.write("\n")
    f.write(weekly_chart)
