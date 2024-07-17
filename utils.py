import os
import cv2
import copy
import numpy as np
import dlib
import base64
from PIL import Image, ImageDraw
import face_recognition
from twilio.rest import Client
from datetime import datetime
from imagekitio import ImageKit

FACE_PROTO = "static/dataset/opencv_face_detector.pbtxt"
FACE_MODEL = "static/dataset/opencv_face_detector_uint8.pb"

GENDER_MODEL = '/static/dataset/deploy_gender.prototxt'
GENDER_PROTO = '/static/dataset/gender_net.caffemodel'

AGE_MODEL = "/static/dataset/deploy_age.prototxt"
AGE_PROTO = "/static/dataset/age_net.caffemodel"

MODEL_MEAN_VALUES=(78.4263377603, 87.7689143744, 114.895847746)

faceNet = cv2.dnn.readNet(FACE_MODEL, FACE_PROTO)

# CONVERT IMAGE TO LINK
def img_to_link(filename):
  imagekit = ImageKit(
  private_key = '<private_key>',
    public_key = '<public_key>',
    url_endpoint = 'https://ik.imagekit.io/<endpoint>')

  image_name = filename.split('\\')[-1].split('.')[0] + '.jpg'

  with open(filename, "rb") as f:
    b64 = base64.b64encode(f.read())

  upload = imagekit.upload_file(
    file = b64,
    file_name = image_name,
    options = {}
  )

  return upload.url

# CHECK IF A PASSWORD IS VALID
def isValidPassword(s):
    if len(s) >= 8:
        for i in s:
            if i.isupper():
                return True

    return False

# GET ONE FACE ENCODING
def enc_a_face(path):
    new_image = face_recognition.load_image_file(path)
    x = face_recognition.face_encodings(new_image)
    if len(x) == 1:
        return True, x[0]

    return False, ""

# GET FACE ENCODINGS AND NAMES
def enc_names(q, dirPath):
    known_face_encodings = []
    known_face_names = []
    known_face_gender = []
    known_face_age = []

    for i in q:
        path = dirPath + "\\" + i["UUID"] + ".jpg"
        if os.path.exists(path):
            new_image = face_recognition.load_image_file(path)
            x = face_recognition.face_encodings(new_image)
            if len(x) == 1:
                known_face_encodings.append(x[0])
                known_face_names.append(i["UUID"])
                known_face_gender.append(i["Gender"])
                known_face_age.append(i["Age"])

    return known_face_encodings, known_face_names, known_face_gender, known_face_age

# CROP AND SAVE FACES FROM IMAGE
def crop_faces(file_name, face_locations, face_encodings):
    filePaths = []
    folder = "\\".join(file_name.split('\\')[:-1])
    folder = folder + "\\"
    image_name = ".".join(file_name.split('\\')[-1].split('.')[:-1])
    f = folder + image_name
    img = Image.open(file_name)
    c = 1
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        cropped_img = img.crop((left, top, right, bottom))
        path = f + str(c) + ".jpg"
        cropped_img.save(path)
        filePaths.append(path)
        c += 1

    return filePaths

# COMPARE FACES
def compare_faces(file_name, known_face_encodings, known_face_names, known_face_gender, known_face_age):
    known = []
    unknown = []

    folder = "\\".join(file_name.split('\\')[:-1])
    folder = folder + "\\"
    image_name = ".".join(file_name.split('\\')[-1].split('.')[:-1])
    f = folder + image_name
    unknown_image = face_recognition.load_image_file(file_name)
    face_locations = face_recognition.face_locations(unknown_image)
    face_encodings = face_recognition.face_encodings(unknown_image, face_locations)
    if len(face_encodings) > 1:
        filePaths = crop_faces(file_name, face_locations, face_encodings)
    else:
        filePaths = [file_name]

    c = 1
    new_list = []
    for face_encoding in face_encodings:
        new_list.clear()
        path = filePaths[c-1]
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        name = "Unknown"
        if matches[best_match_index]:
            name = known_face_names[best_match_index]
        if name == "Unknown":
            for i in range(len(known_face_names)):
                new_list.append([known_face_names[i], round(face_distances[i],2), known_face_gender[i], known_face_age[i]])
            unknown.append([img_to_link(path), face_encoding, copy.deepcopy(new_list), path])
        else:
            known.append([name, path])
        c += 1

    return known, unknown

# GET VIDEO LOG
def get_video_log(file_name, known_face_encodings, known_face_names):
    unknown = []
    log = {}
    face_locations = []
    face_encodings = []

    video_capture = cv2.VideoCapture(file_name)
    fps = video_capture.get(cv2.CAP_PROP_FPS)

    cFrame = 0
    pTime = 0
    while True:
        cFrame += 1
        t = round((cFrame / fps), 2)
        ret, frame = video_capture.read()

        if not ret:
            break

        try:
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = small_frame[:, :, ::-1]
        except:
            rgb_small_frame = frame[:, :, ::-1]

        face_locations = face_recognition.face_locations(np.array(rgb_small_frame))
        face_encodings = face_recognition.face_encodings(np.array(rgb_small_frame), face_locations)

        if len(known_face_encodings) > 0:
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                name = "Unknown"
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]
                if name == "Unknown":
                    unknown.append([t, face_encoding])
                elif name not in log.keys():
                    log[name] = [[t, t]]
                else:
                    if log[name][-1][1] == pTime:
                        log[name][-1][1] = t
                    else:
                        log[name].append([t, t])
            pTime = t
    video_capture.release()

    return log, unknown

# SMS ALERT SYSTEM
def do_sms(uuid):
    # TWILIO CREDENTIALS
    account_sid = '<ACCOUNT SID>'
    auth_token = '<AUTH TOKEN>'
    client = Client(account_sid, auth_token)

    # UNCOMMENT THIS FOR SMS USING TWILIO SERVICE
    # message = client.messages \
    #                 .create(
    #                     body="ALERT !! Criminal identified with Civilian ID : " + uuid,
    #                     from_='+1<mobile-no>',
    #                     to='+91<mobile-no>'
    #                 )

# CCTV ANLYSIS
def highlightFace(net, frame, conf_threshold=0.7):
    frameOpencvDnn = frame.copy()
    frameHeight = frameOpencvDnn.shape[0]
    frameWidth = frameOpencvDnn.shape[1]
    blob = cv2.dnn.blobFromImage(frameOpencvDnn, 1.0, (300, 300), [104, 117, 123], True, False)

    net.setInput(blob)
    detections = net.forward()
    faceBoxes = []
    for i in range(detections.shape[2]):
        confidence = detections[0,0,i,2]
        if confidence > conf_threshold:
            x1=int(detections[0,0,i,3]*frameWidth)
            y1=int(detections[0,0,i,4]*frameHeight)
            x2=int(detections[0,0,i,5]*frameWidth)
            y2=int(detections[0,0,i,6]*frameHeight)
            faceBoxes.append([x1,y1,x2,y2])
            cv2.rectangle(frameOpencvDnn, (x1,y1), (x2,y2), (0,255,0), int(round(frameHeight / 150)), 8)
    return frameOpencvDnn,faceBoxes

def generate_frames(q, q1, camera, known_face_encodings, known_face_names, known_face_gender, known_face_age):
    path = os.getcwd() + "\\" + "temp" + "\\" + "done.jpg"
    log_path = os.getcwd() + "\\" + "cctv_logs" + "\\" + "logs.txt"
    while cv2.waitKey(1) < 0:
        success, frame = camera.read()
        if not success:
            cv2.waitKey()
            break
        else:
            try:
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = small_frame[:, :, ::-1]
            except:
                rgb_small_frame = frame[:, :, ::-1]

            face_locations = face_recognition.face_locations(np.array(rgb_small_frame))
            face_encodings = face_recognition.face_encodings(np.array(rgb_small_frame), face_locations)

            pil_image = Image.fromarray(rgb_small_frame)
            draw = ImageDraw.Draw(pil_image)

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                name = "Unknown"
                if matches[best_match_index]:
                    if face_distances[best_match_index] < 0.55:
                        name = known_face_names[best_match_index]
                if name in q1:
                    color = (255, 0, 0)
                    h = 0
                    f = open("identified.txt", "r")
                    l = f.readlines()
                    if name in l:
                        h = 1
                    if h == 0:
                        with open("identified.txt", "a") as f:
                            f.write("\n" + name)
                        do_sms(name)
                elif name == "Unknown":
                    color = (255, 196, 0)
                else:
                    color = (0, 0, 255)
                with open(log_path, "a") as f:
                    f.write(str(datetime.now()) + " " + name + "\n")
                draw.rectangle(((left, top), (right, bottom)), outline=color)
                _, _, text_width, text_height = draw.textbbox((0, 0), text=name)
                draw.rectangle(((left, bottom - text_height - 10), (right, bottom)), fill=color, outline=color)
                draw.text((left + 6, bottom - text_height - 5), name)

            pil_image.save(path)
            img = cv2.imread(path)
            ret, buffer = cv2.imencode('.jpg', img)
            frame = buffer.tobytes()

        yield(b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# GET GENDER OF A PERSON
def predict_gender(file_name):
    frame = cv2.imread(file_name)
    genderList = ['Male','Female']
    genderNet = cv2.dnn.readNet(GENDER_MODEL, GENDER_PROTO)
    resultImg, faceBoxes = highlightFace(faceNet, frame)
    padding = 20
    for faceBox in faceBoxes:
        face = frame[max(0,faceBox[1]-padding):
                   min(faceBox[3]+padding,frame.shape[0]-1),max(0,faceBox[0]-padding)
                   :min(faceBox[2]+padding, frame.shape[1]-1)]

        blob = cv2.dnn.blobFromImage(face, 1.0, (227,227), MODEL_MEAN_VALUES, swapRB = False)
        genderNet.setInput(blob)
        genderPreds = genderNet.forward()
        gender = genderList[genderPreds[0].argmax()]
        if gender == "Male":
            return "M"
        else:
            return "F"

# GET AGE CATEGORY OF A PERSON
def predict_age(file_name):
    frame = cv2.imread(file_name)
    ageList = ['(0-2)', '(4-6)', '(8-12)', '(15-20)', '(25-32)', '(38-43)', '(48-53)', '(60-100)']
    ageNet = cv2.dnn.readNet(AGE_MODEL, AGE_PROTO)
    resultImg, faceBoxes = highlightFace(faceNet, frame)
    padding = 20
    for faceBox in faceBoxes:
        face = frame[max(0,faceBox[1]-padding):
                   min(faceBox[3]+padding,frame.shape[0]-1),max(0,faceBox[0]-padding)
                   :min(faceBox[2]+padding, frame.shape[1]-1)]

        blob = cv2.dnn.blobFromImage(face, 1.0, (227,227), MODEL_MEAN_VALUES, swapRB = False)
        ageNet.setInput(blob)
        agePreds = ageNet.forward()
        age = ageList[agePreds[0].argmax()]
        age = age.replace("(", "")
        age = age.replace(")", "")
        age = age.split("-")
        age = [int(age[0]), int(age[1])]
        return age
