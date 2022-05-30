from flask import Flask, session, render_template, redirect, request, url_for, Response
from importlib_metadata import method_cache
import cv2
import pymysql
import os
import json
import time
from datetime import datetime
import json

# flask 인스턴스 생성
# __name__: 현재 활성 모듈 이름 포함 
app = Flask(__name__)
app.secret_key = os.urandom(24)

is_success = False
TODAY = 0

@app.route('/', methods=['GET', 'POST'])
def main():
    error = None
    global TODAY
    TODAY = datetime.today().strftime('%Y-%m-%d')
 
    if request.method == 'POST':
        id = request.form['id']
        pw = request.form['pw']
 
        conn = pymysql.connect(host='localhost', 
                                user='root',
                                password='godqhr1622^^', 
                                db='mar_db',
                                port=3307)
        cursor = conn.cursor()


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
        time = 0

        conn = pymysql.connect(host='localhost', 
                                user='root',
                                password='godqhr1622^^', 
                                db='mar_db',
                                port=3307)
        cursor = conn.cursor()
 
        sql = "INSERT INTO users VALUES ('%s', '%s', '%d')" % (id, pw, time)
        cursor.execute(sql)
 
        data = cursor.fetchall()

 
        if not data:
            conn.commit()
            return redirect(url_for('main'))
        else:
            conn.rollback()
            return "Register Failed"
 
    return render_template('register.html', error=error)

select_time = 30

@app.route('/timeselect', methods=['GET', 'POST'])
def timeselect():
    global is_success
    is_success = False
    print(f"timeselect -- {is_success}")
    error = None
    id = session['login_user']
    print("timeselect")

    if request.method == 'POST':
        print("timeslect_POST")

        global select_time
        select_time = int(request.form['time'])
        pose = int(request.form['pose'])

        conn = pymysql.connect(host='localhost', 
                                user='root',
                                password='godqhr1622^^', 
                                db='mar_db',
                                port=3307)
        cursor = conn.cursor()
 
        if (pose==0):
            src="static/images/goyangee.JPG"
        elif (pose==1):
            src="static/images/jeonsa.JPG"
        elif (pose==2):
            src="static/images/namu.JPG"

        sql = "INSERT INTO pose VALUES ('%d', '%d')" % (select_time, pose)
        cursor.execute(sql)

        cursor.close()
        conn.close()

        return render_template(('health.html'), src=src, name = id)

 
    return render_template('timeselect.html', error=error, name=id)
 

 
@app.route('/home.html', methods=['GET', 'POST'])
def home():
    error = None
    id = session['login_user']

    return render_template('home.html', error=error, name=id)
 

@app.route('/calendar')
def calendar():

    id = session['login_user']  #로그인 한 id

    print("calendar")

    # DB에서 해당 id를 가진 값들을 뽑으려고!
    sql = "select * from for_calendar where id = '%s'" % (id)

    conn = pymysql.connect(host='localhost', 
                                user='root',
                                password='godqhr1622^^', 
                                db='mar_db',
                                port=3307)
    
    datas_list = []

    with conn:
        with conn.cursor() as cur:
            cur.execute(sql) #데이터 뽑기 위한 구문
            result = cur.fetchall() 
            print(result)    

            for datas in result:    # for문 돌면서 DB에서 뽑은 한개의 행씩 dates에 저장함
                file_data = dict()  # json파일에 저장하기 위해 딕셔너리 형태로 만듦
                print(f"{datas[3]}, {datas[2]}")    
                # for data in datas:
                #     print(data)
                file_data["title"] = f"운동시간: {datas[3]}\n소모칼로리: ~~"   # title은 DB의 total_time 값
                                                     # 이건 문자열타입으로 저장한건데
                                                     # 숫자형 타입도 ㄱㅊ으면 그냥 file_data["title"] = {dates[3]} 
                file_data["start"] = datas[2]   # start는 DB의 date 값
                datas_list.append(file_data)    # 리스트에 넣어줌
            # result = list(result)
            print(datas_list)
    with open('for_cal.json', 'w', encoding='utf-8') as f:  #json파일에 씀
        json.dump(datas_list, f, ensure_ascii=False, indent="\t")

    return render_template('calendar.html')

@app.route('/data')
def return_data():

    print("return_data")

    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    

    with open("for_cal.json", "r", encoding="utf-8") as input_data:   # def calendar()에서 만든 json파일
        # you should use something else here than just plaintext
        # check out jsonfiy method or the built in json module
        # http://flask.pocoo.org/docs/0.10/api/#module-flask.json
        return input_data.read()


camera = cv2.VideoCapture(0)  

def gen_frames():  # generate frame by frame from camera
    while True:
        success, frame = camera.read()  # read the camera frame
        frame = cv2.flip(frame, 1)
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')




@app.route('/health', methods=['GET', 'POST'])
def health():
    error = None
    id = session['login_user']

    return render_template('health.html', error=error, name=id)
    
def update_time(id):
    conn = pymysql.connect(host='localhost', 
                                user='root',
                                password='godqhr1622^^', 
                                db='mar_db',
                                port=3307,
                                autocommit=True)
    cursor = conn.cursor()
    # id에 맞는 time 값 가져오고 더하기
    sql = "SELECT time from users WHERE id = '%s'" % (id)
    cursor.execute(sql)
    data = cursor.fetchall()

    set_primid = f"{TODAY}{id}"

    res = cursor.execute(f"select * from for_calendar where primid = '{set_primid}'")

    if not res: #해당 id가 오늘 처음 운동했을 때
        sum = int(select_time)
    else:
        sum = int(data[0][0]) + int(select_time)

    # time 값 업데이트
    sql = "UPDATE users SET time = '%d' WHERE id = '%s'" % (sum, id)
    cursor.execute(sql)

    # 이거 만약 시간 오래걸리면 위에 if not res: 이 if문 이용하고, INSERT문이랑 UPDATE문 나눠서 실행하기~~!~!~!~!~~!!~!
    sql_calendar = f"INSERT INTO for_calendar SET primid = '{set_primid}', id='{id}', date='{TODAY}', total_time = {sum}\
    ON DUPLICATE KEY UPDATE id='{id}', date='{TODAY}', total_time = {sum}"
    print(sql_calendar)
    cursor.execute(sql_calendar)

    cursor.close()
    conn.close()


def get_info(id):
    global is_success

    while True:
        print(f"get_info -- {is_success}")
        if is_success:
            break
        conn = pymysql.connect(host='localhost', 
                                user='root',
                                password='godqhr1622^^', 
                                db='mar_db',
                                port=3307)
        cursor = conn.cursor()

        # SQL문 실행
        sql = "SELECT * FROM info"
        cursor.execute(sql)
    
        # cursor의 data fetch
        data = cursor.fetchall()

        json_data = json.dumps({'success': data[0][0], 'booool': data[0][1]})
        yield f"data:{json_data}\n\n"
        print(f"{json_data}\n\n")
        time.sleep(0.5)
        cursor.close()
        conn.close()
            
        if int(select_time) <= int(data[0][0]):
            update_time(id) # 총 시간 구하는 함수 실행
            json_data = json.dumps({'success': 9999, 'booool': 9999})
            yield f"data:{json_data}\n\n"
            is_success = True
            break
    
        
@app.route('/info')
def info():
    
    id = session['login_user']
    return Response(get_info(id), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(debug=True)