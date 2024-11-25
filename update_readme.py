import datetime

# 기존 로그 파일 읽기
log_file = "study-log.txt"
with open(log_file, "r") as f:
    logs = f.readlines()

# 오늘 날짜 추가
today = datetime.date.today().strftime("%Y-%m-%d")
logs.append(f"{today}: 2 hours\n")

# 파일 업데이트
with open(log_file, "w") as f:
    f.writelines(logs)

# README 파일 작성
with open("README.md", "w") as f:
    f.write("# 👋 Hi, I'm [Your Name]\n")
    f.write("\n### 🕒 Recent Activity\n")
    for log in logs[-5:]:  # 최근 5개 기록만 표시
        f.write(f"- {log}")
