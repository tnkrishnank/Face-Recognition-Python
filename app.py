import utils
import os
import cv2
import shutil
import base64
import hashlib
from flask import Flask, request, render_template, redirect, make_response, Response
from pymongo import MongoClient
import pdfkit
import certifi

app = Flask(__name__)

cluster = MongoClient("mongodb+srv://admin:admin@face-recognition.ybmyppy.mongodb.net/Face-Recognition?retryWrites=true&w=majority", tlsCAFile=certifi.where())
db = cluster["Face-Recognition"]

civilian = db["Civilian"]
police = db["Police"]
criminal = db["Criminal"]
record = db["Record"]
admin = db["Admin"]

global title
title = ""

global msgDisp
msgDisp = ""

global fileUrls
fileUrls = []

global unknown
unknown = []

global camera

global known_face_encodings
known_face_encodings = []

global known_face_names
known_face_names = []

global known_face_gender
known_face_gender = []

global known_face_age
known_face_age = []

if len(known_face_encodings) <= 0:
    q = civilian.find({}, {"_id": 0, "UUID": 1, "Photo": 1, "Gender": 1, "Age": 1})
    dirPath = os.getcwd() + "\\" + "civilians"
    known_face_encodings, known_face_names, known_face_gender, known_face_age = utils.enc_names(q, dirPath)

@app.route("/", methods = ["GET", "POST"])
def signin():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    global camera
    camera = ""

    try:
        if 'cUser' in request.cookies:
            return redirect('/dashboard')

        if request.method == "POST":
            pid = request.form["pid"]
            password = request.form["password"]

            q = police.find_one({"PID": pid})

            if q is not None:
                r = q["Password"]

                password_hash = hashlib.md5(password.encode())
                if r == password_hash.hexdigest():
                    resp = make_response(redirect('/dashboard'))
                    resp.set_cookie('cUser', pid, max_age=604800)

                    return resp
                else:
                    return render_template("index.html", passMsg = "Invalid Password !")
            else:
                return render_template("index.html", usrMsg = "Invalid Police ID !")
        else:
            return render_template("index.html")
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = True, admin = False)

@app.route("/dashboard", methods = ["GET", "POST"])
def dashboard():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    global camera
    camera = ""

    if 'cUser' not in request.cookies:
        return redirect("/")

    try:
        if request.method == "POST":
            if request.form["logout"] == "signout":
                resp = make_response(redirect('/'))
                resp.set_cookie('cUser', '', max_age=0)

                return resp
            else:
                pass
        else:
            pid = request.cookies.get('cUser')
            q = police.find_one({"PID": pid})
            uuid = q["UUID"]
            q = civilian.find_one({"UUID": uuid})

            q = "HELLO ! " + q["Name"]

            return render_template("dashboard.html", welcome = q)
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = True, admin = False)

@app.route("/imageEnumeration", methods = ["GET", "POST"])
def imageEnumeration():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    global fileUrls
    fileUrls.clear()

    global unknown
    unknown.clear()

    global camera
    camera = ""

    try:
        if request.method == 'POST':
            dirPath = os.getcwd() + "\\" + "uploads" + "\\" + "images" + "\\" + request.cookies.get('cUser')
            if not os.path.exists(dirPath):
                os.makedirs(dirPath)
            for f in request.files.getlist("files[]"):
                path = dirPath + "\\" + f.filename
                f.save(path)
                fileUrls.append(path)
            return redirect("/getImageReport")
        else:
            return render_template("imageEnumeration.html")
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/getImageReport", methods = ["GET", "POST"])
def getImageReport():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    global fileUrls

    global unknown
    unknown.clear()

    global camera
    camera = ""

    global known_face_encodings

    global known_face_names

    global known_face_gender

    global known_face_age

    try:
        if request.method == 'POST':
            return ""
        else:
            if len(fileUrls) > 0:
                data = []

                dPath = os.getcwd() + "\\" + "civilians" + "\\"

                for i in fileUrls:
                    known, unk = utils.compare_faces(i, known_face_encodings, known_face_names, known_face_gender, known_face_age)

                    for j in known:
                        q = civilian.find_one({"UUID": j[0]})
                        url2 = utils.img_to_link(j[1])
                        p1 = dPath + j[0] + ".jpg"
                        url1 = utils.img_to_link(p1)
                        if q is not None:
                            doc = {
                                "UUID": q["UUID"],
                                "Name": q["Name"],
                                "Gender": q["Gender"],
                                "Age": q["Age"],
                                "Email": q["Email"],
                                "Mobile": q["Mobile"],
                                "Address": q["Address"],
                                "City": q["City"],
                                "ZipCode": q["ZipCode"],
                                "Original": url1,
                                "Assumption": url2
                            }
                            data.append(doc)
                        #os.remove(j[1])
                    #os.remove(i)
                    unknown = unknown + unk

                val = False
                if len(unknown) > 0:
                    val = True

                fileUrls.clear()
            else:
                return redirect("/imageEnumeration")
            return render_template("getImageReport.html", data = data, unk = val)
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/unrecogAnalysis", methods = ["GET", "POST"])
def unrecogAnalysis():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    global unknown

    global camera
    camera = ""

    try:
        if request.method == 'POST':
            q = civilian.find({}, {"_id": 0, "UUID": 1, "Gender": 1, "Age": 1})

            if len(request.form.getlist('gender')) > 0:
                for i in unknown:
                    g = utils.predict_gender(i[3])
                    t = 0
                    while t < len(i[2]):
                        if i[2][t][2] != g:
                            i[2].pop(t)
                        else:
                            t += 1
            if len(request.form.getlist('age')) > 0:
                for i in unknown:
                    a = utils.predict_age(i[3])
                    t = 0
                    while t < len(i[2]):
                        if i[2][t][3] >= a[0] and i[2][t][3] <= a[1]:
                            t += 1
                        else:
                            i[2].pop(t)
            return render_template("unrecogAnalysis.html", data = unknown)
        else:
            if len(unknown) > 0:
                for i in unknown:
                    i[2].sort(key=lambda x:x[1])
                    if len(i[2]) > 10:
                        i[2] = i[2][:10]
            else:
                return redirect("/dashboard")
            return render_template("unrecogAnalysis.html", data = unknown)
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/cctvLive", methods = ["GET", "POST"])
def cctvLive():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    global camera
    camera = cv2.VideoCapture(0)

    global known_face_encodings

    global known_face_names

    global known_face_gender

    global known_face_age

    q = civilian.find({}, {"_id": 0, "UUID": 1, "Photo": 1, "Gender": 1, "Age": 1})
    r = criminal.find({}, {"_id": 0, "UUID": 1})

    q1 = []
    for i in r:
        q1.append(i["UUID"])

    with open("identified.txt", "w") as f:
        f.write("")

    try:
        return Response(utils.generate_frames(q, q1, camera, known_face_encodings, known_face_names, known_face_gender, known_face_age),mimetype='multipart/x-mixed-replace; boundary=frame')
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/videoEnumeration", methods = ["GET", "POST"])
def videoEnumeration():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    global fileUrls
    fileUrls.clear()

    global unknown
    unknown.clear()

    try:
        if request.method == 'POST':
            dirPath = os.getcwd() + "\\" + "uploads" + "\\" + "videos" + "\\" + request.cookies.get('cUser')
            if not os.path.exists(dirPath):
                os.makedirs(dirPath)
            for f in request.files.getlist("files[]"):
                path = dirPath + "\\" + f.filename
                f.save(path)
                fileUrls.append(path)
            return redirect("/getVideoReport")
        else:
            return render_template("videoEnumeration.html")
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/getVideoReport", methods = ["GET", "POST"])
def getVideoReport():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    global fileUrls

    global known_face_encodings

    global known_face_names

    global known_face_gender

    global known_face_age

    try:
        if request.method == 'POST':
            return ""
        else:
            if len(fileUrls) > 0:
                dirPath = os.getcwd() + "\\" + "civilians" + "\\"

                log, unknown = utils.get_video_log(fileUrls[0], known_face_encodings, known_face_names)

                data = []

                os.remove(fileUrls[0])
                fileUrls.clear()

                for i in log.keys():
                    q = civilian.find_one({"UUID": i})
                    if q is not None:
                        path = dirPath + i + ".jpg"
                        path = utils.img_to_link(path)
                        doc = {
                            "UUID": q["UUID"],
                            "Name": q["Name"],
                            "Gender": q["Gender"],
                            "Age": q["Age"],
                            "Email": q["Email"],
                            "Mobile": q["Mobile"],
                            "Address": q["Address"],
                            "City": q["City"],
                            "ZipCode": q["ZipCode"],
                            "Photo": path,
                            "TimeInterval": log[i]
                        }
                        data.append(doc)
            else:
                return redirect("/videoEnumeration")
            return render_template("getVideoReport.html", data = data)
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/others", methods = ["GET", "POST"])
def others():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    if 'cUser' not in request.cookies:
        return redirect("/")

    try:
        if request.method == "POST":
            return ""
        else:
            return render_template("others.html")
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/addCivilian", methods = ["GET", "POST"])
def addCivilian():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    try:
        if request.method == 'POST':
            name = request.form["name"]
            gender = request.form["gender"]
            age = request.form["age"]
            email = request.form["email"]
            mobile = request.form["mobile"]
            address = request.form["address"]
            city = request.form["city"]
            zipcode = request.form["zipcode"]

            for f in request.files.getlist("photo"):
                path = os.getcwd() + "\\" + "temp" + "\\" + f.filename
                f.save(path)

            result, encoding = utils.enc_a_face(path)
            if result:
                q = civilian.find({}, {"_id": 0, "UUID": 1})
                
                x = [0]
                for i in q:
                    x.append(int(i["UUID"][1:]))

                uuid = "C" + str(max(x) + 1)
                new_name = os.getcwd() + "\\" + "temp" + "\\" + uuid + ".jpg"
                new_path = os.getcwd() + "\\" + "civilians" + "\\"
                os.rename(path, new_name)
                shutil.move(new_name, new_path)
                new_path = new_path + uuid + ".jpg"
                
                with open(new_path, "rb") as imageFile:
                    imageString = base64.b64encode(imageFile.read())

                doc = {
                    "UUID": uuid,
                    "Name": name,
                    "Gender": gender,
                    "Age": age,
                    "Email": email,
                    "Mobile": mobile,
                    "Address": address,
                    "City": city,
                    "ZipCode": zipcode,
                    "Photo": imageString,
                    "Encoding": encoding.tolist()
                }

                civilian.insert_one(doc)

                title = "Civilian Added"
                msgDisp = "Civilian ID : " + uuid
                return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)
            else:
                title = "Add Civilian Failed"
                msgDisp = "Invalid Photo !"
                return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)
        else:
            return render_template("addCivilian.html")
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/addCriminal", methods = ["GET", "POST"])
def addCriminal():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    try:
        if request.method == 'POST':
            uuid = request.form["uuid"]

            q = civilian.find_one({"UUID": uuid})
            if q is not None:
                q = criminal.find_one({"UUID": uuid})
                if q is None:
                    q = criminal.find({}, {"_id": 0, "CRID": 1})

                    x = [0]
                    for i in q:
                        x.append(int(i["CRID"][2:]))

                    crid = "CR" + str(max(x) + 1)
                    doc = {
                        "CRID": crid,
                        "UUID": uuid,
                    }

                    criminal.insert_one(doc)

                    title = "Criminal Added"
                    msgDisp = "Civilian ID : " + uuid + "<br><br>Criminal ID : " + crid
                    return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)
                else:
                    return render_template("addCriminal.html", usrMsg = "Criminal Already Exist !")
            else:
                return render_template("addCriminal.html", usrMsg = "Civilian Not Found !")
        else:
            return render_template("addCriminal.html")
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/addCrime", methods = ["GET", "POST"])
def addCrime():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    try:
        if request.method == 'POST':
            location = request.form["location"]
            typex = request.form["type"]
            crid = request.form["crid"]
            description = request.form["description"]

            q = record.find({}, {"_id": 0, "RID": 1})

            x = [0]
            for i in q:
                x.append(int(i["RID"][1:]))

            rid = "R" + str(max(x) + 1)
            doc = {
                "RID": rid,
                "Location": location,
                "Type": typex,
                "CRID": crid,
                "Description": description
            }

            record.insert_one(doc)

            title = "Crime Added"
            msgDisp = "Crime ID : " + rid
            return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)
        else:
            return render_template("addCrime.html")
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/deleteCivilian", methods = ["GET", "POST"])
def deleteCivilian():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    try:
        if request.method == 'POST':
            uuid = request.form["uuid"]

            q = civilian.find_one({"UUID": uuid})

            if q is not None:
                civilian.delete_one({"UUID": uuid})

                title = "Delete Civilian"
                msgDisp = "Civilian Deleted Successfully !<br><br>Civilian ID : " + uuid
                return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)
            else:
                return render_template("deleteCivilian.html", usrMsg = "Civilian Not Found !")
        else:
            return render_template("deleteCivilian.html")
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/deleteCriminal", methods = ["GET", "POST"])
def deleteCriminal():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    try:
        if request.method == 'POST':
            crid = request.form["crid"]

            q = criminal.find_one({"CRID": crid})

            if q is not None:
                criminal.delete_one({"CRID": crid})

                title = "Delete Criminal"
                msgDisp = "Criminal Deleted Successfully !<br><br>Criminal ID : " + crid
                return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)
            else:
                return render_template("deleteCriminal.html", usrMsg = "Criminal Not Found !")
        else:
            return render_template("deleteCriminal.html")
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/deleteCrime", methods = ["GET", "POST"])
def deleteCrime():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    try:
        if request.method == 'POST':
            rid = request.form["rid"]

            q = record.find_one({"RID": rid})

            if q is not None:
                record.delete_one({"RID": rid})

                title = "Delete Crime"
                msgDisp = "Crime Deleted Successfully !<br><br>Crime ID : " + rid
                return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)
            else:
                return render_template("deleteCrime.html", usrMsg = "Crime Not Found !")
        else:
            return render_template("deleteCrime.html")
    except:
        if 'cUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = False)

@app.route("/adminPanel", methods = ["GET", "POST"])
def adminPanel():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    try:
        if 'aUser' in request.cookies:
            return redirect('/adminDashboard')

        if request.method == "POST":
            aid = request.form["aid"]
            password = request.form["password"]

            q = admin.find_one({"AID": aid})

            if q is not None:
                r = q["Password"]

                password_hash = hashlib.md5(password.encode())
                if r == password_hash.hexdigest():
                    resp = make_response(redirect('/adminDashboard'))
                    resp.set_cookie('aUser', aid, max_age=604800)

                    return resp
                else:
                    return render_template("adminPanel.html", passMsg = "Invalid Password !")
            else:
                return render_template("adminPanel.html", usrMsg = "Invalid Admin ID !")
        else:
            return render_template("adminPanel.html")
    except:
        if 'aUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = True, admin = True)

@app.route("/adminDashboard", methods = ["GET", "POST"])
def adminDashboard():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    if 'aUser' not in request.cookies:
        return redirect("/")

    try:
        if request.method == "POST":
            if request.form["logout"] == "signout":
                resp = make_response(redirect('/'))
                resp.set_cookie('aUser', '', max_age=0)

                return resp
            else:
                pass
        else:
            aid = request.cookies.get('aUser')
            q = admin.find_one({"AID": aid})
            uuid = q["UUID"]
            q = civilian.find_one({"UUID": uuid})

            q = "HELLO ! " + q["Name"]

            return render_template("adminDashboard.html", welcome = q)
    except:
        if 'aUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = True, admin = True)

@app.route("/getpid", methods = ["GET", "POST"])
def getpid():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    try:
        if request.method == "POST":
            uuid = request.form["uuid"]

            q = police.find_one({"UUID": uuid})

            if q is not None:
                pid = q["PID"]

                title = "Police ID"
                msgDisp = "Civilian ID : " + uuid + "<br><br>Police ID : " + pid
                return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = True)
            else:
                return render_template("getpid.html", usrMsg = "Police Not Found !")
        else:
            return render_template("getpid.html")
    except:
        if 'aUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = True)

@app.route("/signup", methods = ["GET", "POST"])
def signup():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    try:
        if request.method == "POST":
            uuid = request.form["uuid"]
            password = request.form["password"]
            reTypePassword = request.form["re-password"]

            q = civilian.find_one({"UUID": uuid})

            if q is not None:
                q = police.find_one({"UUID": uuid})
                if q is None:
                    if utils.isValidPassword(password):
                        if password == reTypePassword:
                            q = police.find({}, {"_id": 0, "PID": 1})

                            x = [0]
                            for i in q:
                                x.append(int(i["PID"][1:]))

                            password_hash = hashlib.md5(password.encode())

                            pid = "P" + str(max(x) + 1)
                            doc = {
                                "PID": pid,
                                "UUID": uuid,
                                "Password": password_hash.hexdigest()
                            }

                            police.insert_one(doc)

                            return redirect("/adminDashboard")
                        else:
                            return render_template("signup.html", rePsswdMsg = "Passwords do not match !")
                    else:
                        return render_template("signup.html", psswdMsg = "Atleast 8 characters. Atleast one character in Uppercase !")
                else:
                    return render_template("signup.html", usrMsg = "Police Already Exist !")
            else:
                return render_template("signup.html", usrMsg = "Invalid Unique User ID !")
        else:
            return render_template("signup.html")
    except:
        if 'aUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = True)

@app.route("/deletePolice", methods = ["GET", "POST"])
def deletePolice():
    global title
    title = ""

    global msgDisp
    msgDisp = ""

    try:
        if request.method == "POST":
            pid = request.form["pid"]

            q = police.find_one({"PID": pid})

            if q is not None:
                police.delete_one({"PID": pid})

                title = "Delete Police"
                msgDisp = "Account Deleted Successfully !<br><br>Police PID : " + pid
                return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = True)
            else:
                return render_template("deletePolice.html", usrMsg = "Police Not Found !")
        else:
            return render_template("deletePolice.html")
    except:
        if 'aUser' not in request.cookies:
            return redirect("/")

        title = "404 ERROR"
        msgDisp = "404 ERROR. PAGE NOT FOUND !!!"
        return render_template("msgDisplay.html", title = title, msgDisp = msgDisp, login = False, admin = True)

if __name__ == '__main__':
    app.run(
        host = '0.0.0.0',
        debug = True,
        port = 80,
        threaded = True
    )
