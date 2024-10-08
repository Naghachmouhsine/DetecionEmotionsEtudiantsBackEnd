from flask import Flask, request, jsonify, render_template
import cv2
import numpy as np
import torch
import joblib
from flask_cors import CORS
from PIL import Image
import base64
from io import BytesIO
import modelYolo
from waitress import serve
from dataBase import auth,gestionSeance
import mysql.connector as cnx

app = Flask(__name__)
# CORS(app, resources={r"/detect": {"origins": "http://127.0.0.1:3000"}})
CORS(app)
yolo=modelYolo.FaceDetector()

conn=cnx.connect(
    host="localhost",
    database="emotionDetectionDB",
    user="root",
    password=""
)
authentification=auth.Authentification(conn)
ges=gestionSeance.GestionSeance(conn)





faces_detected=[]
@app.route('/')
def index():
    return render_template('index.html')

@app.route("/tstCnx",methods=["GET"])
def tstCnx() :
    return jsonify({"cnx" : True})

@app.route('/detect', methods=['POST'])
def detect(): 
    data = request.get_json()
    print(data["isStop"])
    if data["isStop"] : 
        return {"class_name" : [],"frame" : data["image"]}
    image_data = data['image']
    image_data = image_data.split(",")[1]
    image = Image.open(BytesIO(base64.b64decode(image_data)))
    # # Convertir en format compatible avec OpenCV
    image = np.array(image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    # # Utiliser YOLO pour détecter les visages
    user=data["user"]
    resultat=yolo.detect_faces(image,user)
    _, buffer = cv2.imencode('.jpg',resultat[1])
    frame_encoded = base64.b64encode(buffer).decode('utf-8')
    return jsonify({"class_names" : resultat[0],"frame" : frame_encoded})

@app.route('/auth/register', methods=['POST'])
def register():
    print(request.get_json())
    res=authentification.register(request.get_json())
    return jsonify({"res" : res})

@app.route('/auth/updateProfile', methods=['POST'])
def updateProfile():
    print(request.get_json())
    res=authentification.update(request.get_json())
    return jsonify({"succes" : res})


@app.route('/auth/deleteProfile', methods=['POST'])
def deleteProfile():
    print(request.get_json())
    res=authentification.delete(request.get_json()["id"])
    return jsonify({"succes" : res})



@app.route("/auth/login",methods=["POST"])
def auth() : 
    resultat=authentification.auth(request.get_json())
    return jsonify(resultat)

@app.route("/insertNewSeance",methods=["POST"])
def insertNewSeance() : 
    seance=request.get_json()
    tabEmotions=yolo.faces_detected_total[seance["user_id"]]
    print("after yolo.faces_detected_total")
    # print(len(yolo.faces_detected_total))
    r={}
    for e in set(tabEmotions): 
        r[e]=round((tabEmotions.count(e)/len(tabEmotions))*100,2)
    for i in ["surprise","anger","disgust","fear","happiness","neutral","sadness"] : 
        r[i]=r[i] if i in r.keys() else 0
    seance["emotion"]=r
    ges.insertSeance(seance)
    yolo.faces_detected_total[seance["user_id"]]=[]
    return jsonify(r)






@app.route("/getStatistique",methods=["GET"])
def getStatistique()  :
    resultat1={}
    resultat2={}
    for res in ges.getStatistique() : 
        resultat1[res[0]]=[round(res[1],2),round(res[2],2),round(res[3],2),round(res[4],2),round(res[5],2),round(res[6],2),round(res[7],2)]
    resultat2=ges.getStatistique2()
    resultat={
        "statistique1" : resultat1,
        "statistique2" : resultat2,
    }
    return jsonify(resultat)

# @app.route("/getStatistiqu2",methods=["GET"])
# def getStatistique2()  :
#     resultat=ges.getStatistique2()
#     return jsonify(resultat)


@app.route("/getAllUsers",methods=["GET"])
def getAllUsers()  :
    return jsonify(authentification.getAllUsers())



if __name__ == '__main__':
    serve(app, host="0.0.0.0", port=5000, threads=16)


