import pymysql
import cv2
import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from keras.preprocessing import image
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler  
import time

os.environ["CUDA_VISIBLE_DEVICES"]="0"
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        tf.config.experimental.set_memory_growth(gpus[0], True)
    except RuntimeError as e:
        print(e)

BODY_PARTS_BODY_25 = {0: "Nose", 1: "Neck", 2: "RShoulder", 3: "RElbow", 4: "RWrist",
                      5: "LShoulder", 6: "LElbow", 7: "LWrist", 8: "MidHip", 9: "RHip",
                      10: "RKnee", 11: "RAnkle", 12: "LHip", 13: "LKnee", 14: "LAnkle"}

POSE_PAIRS_BODY_25 = [[0, 1], [1, 2], [1, 5], [1, 8], [8, 9], [8, 12], [9, 10], [12, 13], [2, 3],
                      [3, 4], [5, 6], [6, 7], [10, 11], [13, 14]]
                      # 15~24 버렸기 때문에 얘네 라인 그리는 부분 지움

VGG_LABEL = [0, 1, 10, 11, 12, 13, 14, 15, 2, 3, 4, 5, 6, 7, 8, 9]
# VGG 추론 결과 라벨링(보기 쉽도록)

# POSETIME = [30, 30, 30, 30, 30] # 0, 1, 2, 3, 4번 동작의 유지 시간

'''사실상 select랑 delete는 vgg_res 테이블 아님!!!! vgg 추론 결과 웹으로 넘겨주기 위한 테이블이 vgg_res'''
# sql = "SELECT * FROM vgg_res ORDER BY RESULT"   #어차피 vgg_res 테이블엔 RESULT 컬럼 하나밖에 없기때문에 아래 sql문과 같은 결과임
sql_select = "SELECT * FROM pose"    #DB에 뭐가 있나?
sql_delete = "DELETE FROM pose LIMIT 1"
# sql_update = "UPDATE vgg_res SET MYTIME = %s, RESULT = %s"
sql_update = "UPDATE vgg_res SET MYTIME = %s, RESULT = %s, RESBOOL = %s"

# sql_delete = "DELETE FROM current_pose ORDER BY POSE DESC LIMIT 1"
# ㄴ>current_pose 테이블의 POSE 컬럼에 제일 마지막으로 추가된 열 삭제

# # 이거 두개 cur.execute(sql_insert, ~~) 로 할 수 있나 확인하기~~!
# sql_insert_false = "INSERT INTO vgg_res VALUE (False);"
# sql_insert_true = "INSERT INTO vgg_res VALUE (True);"


def output_keypoints(image_path, net, threshold=0.1):
    frame = cv2.imread(image_path)
    # out_frame = frame.copy()
    #resize 오류나서 그냥 frame.copy()로 하긴 했는데 cv.resize가 왜 안되는지 확인
    # out_frame = cv2.resize(frame,(256, 256))
    out_frame = cv2.resize(frame,(224, 224))
    frameHeight, frameWidth, _ = frame.shape

    # Specify the input image dimensions
    inWidth = 368
    inHeight = 368

    # Prepare the frame to be fed to the network (전처리)
    inpBlob = cv2.dnn.blobFromImage(frame, 1.0 / 255, (inWidth, inHeight), (0, 0, 0), swapRB=False, crop=False)

    # Set the prepared object as the input blob of the network
    net.setInput(inpBlob)

    output = net.forward()

    H = output.shape[2]
    W = output.shape[3]
    # Empty list to store the detected keypoints
    points = []
    for i in range(len(BODY_PARTS_BODY_25)): #body25이기 때문에 range(len(BODY_PARTS_BODY_25))가 맞는데, 16~24까지 keypoint 필요 X... 이러면 coco가 낫나..?
        probMap = output[0, i, :, :]

        minVal, prob, minLoc, point = cv2.minMaxLoc(probMap)
        #prob = 있을 확률
        #point = x,y좌표

        # Scale the point to fit on the original image
        x = (224 * point[0]) / W
        y = (224 * point[1]) / H

        if prob > threshold :
            points.append((int(x), int(y)))
        else:
            points.append(None)
    return points, out_frame    #좌표랑 224,224로 resize된 이미지 리턴

def output_keypoints_with_lines(POSE_PAIRS_BODY_25, frame, points):
    # global my_num
    frameCopy = frame.copy()    #224,224로 resize된 이미지 받음

    for pair in POSE_PAIRS_BODY_25:
        partA = pair[0]
        partB = pair[1]
        # print(f'partA: {partA}, partB: {partB}')

        if points[partA] and points[partB]:
            # print(f'partA: {partA}, partB: {partB}')
            cv2.line(frameCopy, points[partA], points[partB], (0, 255, 0), 3)

    # cv2.imwrite("./event_dir/{}.jpg".format(my_num), frameCopy)
    # my_num+= 1

    return frameCopy    #스켈레톤 그려진 이미지 리턴

'''observer.stop()구문 어디에 넣어야 finish_time==my_time일 때 watchdog 잘 종료될까 생각하기'''
class Watcher:
    DIRECTORY_WATCH = "z:\input_img" #폴더 경로 지정
    # DIRECTORY_WATCH = "../../y/input_img" #폴더 경로 지정
    # DIRECTORY_WATCH = "./event_dir" #폴더 경로 지정

    def __init__(self):
        self.observer = Observer()  #실행시 Observer객체 생성
  
    def run(self):
        event_handler = Handler() #이벤트 핸들러 객체 생성 
        self.observer.schedule(event_handler, self.DIRECTORY_WATCH, recursive=True) 
#schedule(event_handler, path, recursive=False) : path를 계속 지켜보고 동작이 발생하면 응답을 주도록 하는 함수, 응답이 있을때 event_handler동작대로 실행됨
#recursive : True는 해당 path하위 디렉토리에 반복적으로 이벤트가 생성되는 경우 설정, 다른 경우는 False
        self.observer.start()   
        try:
            while True:
                time.sleep(0.5)   #굳이 얠 넣어야 하나..?
                if my_time == finish_time:
                    self.observer.stop()    #main에서 w.run() 함수가 종료됨
                    break
                # print("try")
        except:
            self.observer.stop()
            print("Error")
        self.observer.join()  #스레드가 정상적으로 종료될때까지 기다림

class Handler(FileSystemEventHandler):    #이벤트 정의
    '''어차피 파일 create 돼도 on_modified도 같이 불리기 때문에 on_created 따로 정의할 필요 없긴함.
       해당 동작 끝나면 input_img 디렉터리 내 모든 파일 날리고 다시 저장하기때문에 on_create만 정의해도 ㅇㅋ'''
    def on_created(self, event):    # 원래 두 번씩 불렸는데 갑자기 한 번만 불림.....
        super(Handler, self).on_created(event)
        print(f"on_created: {event.src_path}")

        start = time.time()

        points, frame_man = output_keypoints(image_path=event.src_path, net=net, threshold=0.1)

        # print(f"on_created: {file_path}")
        # points, frame_man = output_keypoints(image_path=file_path, net=net, threshold=0.1)
        # points, frame_man = output_keypoints(image_path="./event_dir/full_body.jpg", net=net, threshold=0.1)

        ret_frame = output_keypoints_with_lines(POSE_PAIRS_BODY_25, frame_man, points)  #ret_frame은 스켈레톤 그려진 이미지

        '''여기 추가~~~~~~~~~~'''
        ret_frame = ret_frame / 255.
        prediectins = vgg(ret_frame[np.newaxis, :])
        inf_res = VGG_LABEL[np.argmax(prediectins)]  #이게 추론 결과
        
        if int(current_pose) == 0:
            if inf_res == 0 or inf_res == 5 or inf_res == 6 or inf_res == 7:
                resbool = 1
            else:
                resbool = 0
        elif int(current_pose) == 1:
            if inf_res == 1 or inf_res == 8:
                resbool = 1
            else:
                resbool = 0
        elif int(current_pose) == 2:
            if inf_res == 2 or inf_res == 9 or inf_res == 10:
                resbool = 1
            else:
                resbool = 0
        elif int(current_pose) == 3:
            if inf_res == 3 or inf_res == 11 or inf_res == 12 or inf_res == 13:
                resbool = 1
            else:
                resbool = 0
        else: #4
            if inf_res == 4 or inf_res == 14:
                resbool = 1
            else:
                resbool = 0
        
        # classes = vgg.predict(ret_frame)
        '''여기 추가~~~~~~~~~~'''
        # x = image.img_to_array(ret_frame)   #retframe으로 vgg추론시키려고 함
        # x = np.expand_dims(x, axis=0)

        # image_tensor = np.vstack([x])
        # classes = vgg.predict(image_tensor) #retframe으로 vgg추론~~ classes랑 웹이 저장한 db에서 받아온 정보랑 비교해서 True/False 구분해야됨

        print(f"{time.time() - start} sec")

        print(f"{inf_res==int(current_pose)}")    #True/False 출력

        if inf_res == int(current_pose):
            global my_time  #전역변수 변경하려면 global로 선언 후 변경
            my_time += 1 
        print(inf_res)
        print(int(current_pose))
        print(int(int(inf_res==int(current_pose))))
        # cur.execute(sql_update, (my_time, int(np.argmax(classes[0])==int(current_pose)))) # True(1), False(0)값만
        cur.execute(sql_update, (my_time, inf_res, resbool)) # vgg inference 결과인 class num 전달
        
        #     cur.execute(sql_update, (np.argmax(classes[0])==int(current_pose), my_time)) 
        # else:
        #     cur.execute(sql_update, (np.argmax(classes[0])==int(current_pose), my_time)) 


    # def on_modified(self, event):
    #     super(Handler, self).on_modified(event)
    #     print(f"on_modified: {event.src_path}")
    #     points, frame_man = output_keypoints(image_path=event.src_path, net=net, threshold=0.1)

    #     # print(f"on_modified: {file_path}")
    #     # points, frame_man = output_keypoints(image_path=file_path, net=net, threshold=0.1)
    #     # points, frame_man = output_keypoints(image_path="./event_dir/full_body.jpg", net=net, threshold=0.1)

    #     ret_frame = output_keypoints_with_lines(POSE_PAIRS_BODY_25, frame_man, points)  #ret_frame은 스켈레톤 그려진 이미지
    #     x = image.img_to_array(ret_frame)   #retframe으로 vgg추론시키려고 함
    #     x = np.expand_dims(x, axis=0)

    #     image_tensor = np.vstack([x])
    #     classes = vgg.predict(image_tensor) #retframe으로 vgg추론~~ classes랑 웹이 저장한 db에서 받아온 정보랑 비교해서 True/False 구분해야됨
    #     print(f"{np.argmax(classes[0])==0}")    #True/False 출력
    #     if np.argmax(classes[0]) == int(current_pose):
    #         cur.execute(sql_insert_true) # 여기서 cur이 가능???
    #         global my_time  #전역변수 변경하려면 global로 선언 후 변경
    #         my_time += 1 
    #     else:
    #         cur.execute(sql_insert_false)


    # @staticmethod
    # def on_any_event(event):   #모든 이벤트 발생시
    #     print('이벤트 발생시 동작정의')

protoFile = "./pose/body_25/pose_deploy.prototxt"
weightsFile = "./pose/body_25/pose_iter_584000.caffemodel"
net = cv2.dnn.readNetFromCaffe(protoFile, weightsFile)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
vgg = keras.models.load_model('final_cap_model_0603.h5')
current_pose = 0    #웹에서 DB에 저장시킨 현재 사용자가 따라해야 하는 동작 저장하는 변수(그냥 초기화하려고 여기 선언)
finish_time = 0     #지금 동작이 몇초동안 운동해야 되는지(그냥 초기화하려고 여기 선언)
my_time = 0         #사용자의 운동 시간(그냥 초기화하려고 여기 선언)
# file_path = ""

while True:
    # start = time.time()
    conn = pymysql.connect(host='172.20.10.5',    #DB 연결 (평균 0.003초 정도 걸림)
                        user='test',            #thread pool처럼 DB pool쓰면 시간 단축될까..? => pymysql은 DB connection pool 지원 X
                        password='iotcap!',
                        db='test',
                        autocommit=True)    #autocommit=True 추가해서 커밋 자동 반영되게(이거 안 하면 cur.execute(sql_delete)해도 delete 반영 안됨)
    # print(time.time() - start)
    with conn:
        with conn.cursor() as cur:
            try:
                cur.execute(sql_select) #데이터 뽑기 위한 구문
                db_outputs = cur.fetchall() #result에 db에 있는 데이터들이 튜플형식으로 들어감
                print(f'{db_outputs[0][0]}, {db_outputs[0][1]}')  # ~~~~~~c첫번째 입력된 데이터 뽑기~~~~~~~
                                                                    # 해당 행의 0번째 열과 1번째 열
                cur.execute(sql_delete) #마지막으로 입력된 데이터 삭제시킴!

                current_pose = db_outputs[-1][1]

                # 위 코드는 DB에 무언가가 추가될때까지 기다렸다가 추가되면 추가된거 뽑은 후에 뭔가 하려는 코드 짜기
                # 왜 DB에 뭐가 추가될 때까지 기다리냐면, 뭔가 추가된다는 건 해당 동작으로 사용자가 운동을 한다는 거고, 
                # 이는 공유폴더에 사용자 이미지가 들어오는 것을 의미함

                # ~~~뭔가 코드~~~~
                my_time = 0
                finish_time = db_outputs[-1][0]    #finish_time도 DB에서 뽑아오거나 이렇게 하거나..
                                                        #user마다 finish time이 다르면 DB에서 뽑는게 맞음

                print(f"current_pose: {current_pose}, finish_time: {finish_time}")

                w = Watcher()
                w.run()
                print(f'{current_pose} 끝~~~')  # if finish_time==my_time이면 w.run()에서 빠져나와서 이거 프린트함
                # os.system("rm ./event_dir/*")
                os.system("powershell.exe rm z:\input_img/*")  #z:\input_img 디렉터리 내 모든 파일 삭제
                cur.execute(sql_update, (0, 15, 0))    #동작 끝나면 해당 테이블 초기화해주려고 업데이트
                                                    #(15는 차렷 클래스로, 동작 시작하라고 알려주면 좋을듯?)

            except: # vgg_res의 RESULT 컬럼에 아무런 데이터도 없으면 except문으로 빠짐
                os.system("powershell.exe rm z:\input_img/*")  #z:\input_img 디렉터리 내 모든 파일 삭제
                print("오류!~~~~~~")
    
# conn.close()  #with 구문 안 할 경우 주석 풀어서 close 따로 해주기
