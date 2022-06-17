import time
import os
import cv2
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler  
import sys
 #이벤트 import  *on_any_event, on_created, on_modified 등등.. 

os.environ["CUDA_VISIBLE_DEVICES"]="0"

BODY_PARTS_BODY_25 = {0: "Nose", 1: "Neck", 2: "RShoulder", 3: "RElbow", 4: "RWrist",
                      5: "LShoulder", 6: "LElbow", 7: "LWrist", 8: "MidHip", 9: "RHip",
                      10: "RKnee", 11: "RAnkle", 12: "LHip", 13: "LKnee", 14: "LAnkle"}

POSE_PAIRS_BODY_25 = [[0, 1], [1, 2], [1, 5], [1, 8], [8, 9], [8, 12], [9, 10], [12, 13], [2, 3],
                      [3, 4], [5, 6], [6, 7], [10, 11], [13, 14]]
                      # 15~24 버렸기 때문에 얘네 라인 그리는 부분 지움


def output_keypoints(image_path, net, threshold=0.1):
    frame = cv2.imread(image_path)
    out_frame = cv2.resize(frame,(224, 224))
    frameHeight, frameWidth, _ = frame.shape

    inWidth = 368
    inHeight = 368

    inpBlob = cv2.dnn.blobFromImage(frame, 1.0 / 255, (inWidth, inHeight), (0, 0, 0), swapRB=False, crop=False)

    net.setInput(inpBlob)

    output = net.forward()

    H = output.shape[2]
    W = output.shape[3]
    points = []
    num=0
    for i in range(len(BODY_PARTS_BODY_25)): #body25이기 때문에 range(len(BODY_PARTS_BODY_25))가 맞는데, 16~24까지 keypoint 필요 X
        probMap = output[0, i, :, :]

        minVal, prob, minLoc, point = cv2.minMaxLoc(probMap)

        # Scale the point to fit on the original image
        x = (224 * point[0]) / W
        y = (224 * point[1]) / H

        if prob > threshold :
            num+=1
            points.append((int(x), int(y)))
        else :
            points.append(None)
    if num != 15:
        return "NOPE", "NOPE"
    else:
        return points, out_frame
    
def output_keypoints_with_lines(file_num, POSE_PAIRS_BODY_25, frame, points):
    frameCopy = frame.copy()

    for pair in POSE_PAIRS_BODY_25:
        partA = pair[0]
        partB = pair[1]
        # print(f'partA: {partA}, partB: {partB}')

        if points[partA] and points[partB]:
            # print(f'partA: {partA}, partB: {partB}')
            cv2.line(frameCopy, points[partA], points[partB], (0, 255, 0), 3)

    cv2.imwrite('./dataset/{}/{}.jpg'.format(dir_num, file_num), frameCopy)
    cv2.destroyAllWindows()
    file_num += 1
    return frameCopy


class Watcher:
    DIRECTORY_WATCH = "z:\input_img" #폴더 경로 지정
    

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
                time.sleep(0.5)
        except:
            self.observer.stop()
            print("Error")
        self.observer.join()  #스레드가 정상적으로 종료될때까지 기다림
 
class Handler(FileSystemEventHandler):    #이벤트 정의
    def on_created(self, event):    # 원래 두 번씩 불렸는데 갑자기 한 번만 불림.....
        super(Handler, self).on_created(event)
        print(f"on_created: {event.src_path}")
        start_time = time.time()
        points, frame_man = output_keypoints(image_path=event.src_path, net=net, threshold=0.1)

        if frame_man != "NOPE":
            output_keypoints_with_lines(file_num, POSE_PAIRS_BODY_25, frame_man, points)
        
        print(f'{time.time() - start_time}sec')


dir_num = sys.argv[1]
file_num = sys.argv[2]

if __name__ == '__main__':
    protoFile = "./pose/body_25/pose_deploy.prototxt"
    weightsFile = "./pose/body_25/pose_iter_584000.caffemodel"
    net = cv2.dnn.readNetFromCaffe(protoFile, weightsFile)
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)

    w = Watcher()
    w.run()
    os.system("powershell.exe rm z:\input_img/*")  #z:\input_img 디렉터리 내 모든 파일 삭제
