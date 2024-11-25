import datetime

# 학습 시간 계산
today = datetime.date.today().strftime("%Y-%m-%d")
hours_studied = 2  # 예시 시간

with open("README.md", "w") as f:
    f.write(f"### 🕒 Recent Activity\n")
    f.write(f"- Studied programming for {hours_studied} hours on {today}.\n")
