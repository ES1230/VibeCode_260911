#파이썬함수연습2.py

def connectURI(server,port):
    #f-string은 변수명을 바로넘김
    strURL = f"http://{server}:{port}"
    return strURL

#테스트
print(connectURI("kpc.com","8080"))
