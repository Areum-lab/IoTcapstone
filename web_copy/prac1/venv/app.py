from django.shortcuts import render
from flask import Flask, session, render_template, redirect, request, url_for, Response
from flaskext.mysql import MySQL
from importlib_metadata import method_cache
import cv2

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


camera = cv2.VideoCapture(0)  # use 0 for web camera
#  for cctv camera use rtsp://username:password@ip_address:554/user=username_password='password'_channel=channel_number_stream=0.sdp' instead of camera
# for local webcam use cv2.VideoCapture(0)

def gen_frames():  # generate frame by frame from camera
    while True:
        # Capture frame-by-frame
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result


@app.route('/video_feed')
def video_feed():
    #Video streaming route. Put this in the src attribute of an img tag
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/stream')
def index():
    """Video streaming home page."""
    return render_template('stream.html')


if __name__ == '__main__':
    app.run(debug=True)