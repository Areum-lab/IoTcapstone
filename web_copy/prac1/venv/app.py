from django.shortcuts import render
from flask import Flask, session, render_template, redirect, request, url_for
from flaskext.mysql import MySQL
from importlib_metadata import method_cache


mysql = MySQL()
app = Flask(__name__)
# flask 인스턴스 생성
# __name__: 현재 활성 모듈 이름 포함 
 
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'godqhr1622^^' #MySQL 계정 password
app.config['MYSQL_DATABASE_DB'] = 'mydb'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
app.secret_key = "1234" #db password
mysql.init_app(app)
 
@app.route('/', methods=['GET', 'POST'])
# @app.route('/'): decorator/ 함수 코드 바꾸지 않고도 함수의 동작 조절가능
# route('/'): 웹 표현 메소드
# flask에서는 이러한 decorator가 URL 연결에 활용됨

# GET method: 데이터 읽거나(Read) 검색(Retrieve)시 사용
# 어떤 정보 가져와서 조회하기 위해 사용하는 방식
# GET 성공 시, XML이나 JSON과 함께 200(Ok) HTTP 응답코드 리턴
# GET 실패 시, 404(Not found)나 400(Bad request) 에러 발생

# POST method: 새로운 리소스 생성(create)
# 데이터를 서버로 제출하여 추가/수정하기 위해 사용하는 방식


def main():
    error = None
 
    if request.method == 'POST':
        id = request.form['id']
        pw = request.form['pw']
 
        # MySQL Connection 연결
        conn = mysql.connect()
        # Connection으로부터 Cursor 생성
        cursor = conn.cursor()
        # SQL문 실행
        sql = "SELECT id FROM users WHERE id = %s AND pw = %s"
        value = (id, pw)
        cursor.execute("set names utf8")
        cursor.execute(sql, value)
 
        # cursor의 data fetch
        data = cursor.fetchall()
        cursor.close()
        conn.close()
 
        for row in data:
            data = row[0]
 
        if data:
            session['login_user'] = id
            return redirect(url_for('home'))
        else:
            error = 'invalid input data detected !'
    return render_template('main.html', error = error)
 
 
@app.route('/register.html', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        id = request.form['regi_id']
        pw = request.form['regi_pw']
 
        conn = mysql.connect()
        cursor = conn.cursor()
 
        sql = "INSERT INTO users VALUES ('%s', '%s')" % (id, pw)
        cursor.execute(sql)
 
        data = cursor.fetchall()
        # cursor.close()
        # conn.close()
 
        if not data:
            conn.commit()
            return redirect(url_for('main'))
        else:
            conn.rollback()
            return "Register Failed"
 
    return render_template('register.html', error=error)
 
@app.route('/home.html', methods=['GET', 'POST'])
def home():
    error = None
    id = session['login_user']
    return render_template('home.html', error=error, name=id)
 
@app.route('/health')
def health():
    error = None
    id = session['login_user']
    return render_template('health.html', error=error, name=id)

@app.route('/calendar')
def calendar():
    return render_template('calendar.html')


if __name__ == '__main__':
    app.run()