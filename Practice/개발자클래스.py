#라이브러리를 사용
import glob

#raw string notation(날것 그대로 사용)
print(glob.glob(r"C:\work\*.py"))

# Developer 클래스를 정의화면서 
# id, name, skill이라는 변수가 있고,
# printInfo라는 메서드가 해당 정보를 출력함.

class Developer:
    def __init__(self, id, name, skill):
        self.id = id
        self.name = name
        self.skill = skill

    def printInfo(self):
        print(f"ID: {self.id}, Name: {self.name}, Skill: {self.skill}")

# 인스턴스 생성
dev1 = Developer(1, "Alice", "Python")          
dev1.printInfo()  # 메서드 호출 