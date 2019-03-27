import cv2
import json
import imutils
import requests
import numpy as np
import pyzbar.pyzbar as pyzbar

x = 0
y = 0

#Encontrar código QR
def find_marker(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 35, 125)
    
    (cnts, _) = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key = cv2.contourArea)
    return cv2.minAreaRect(c)

#Calcular distancia
def distance_to_camera(width):
    return (KNOWN_WIDTH * KNOWN_DISTANCE) / width

#Posicionar en el centro
def centrar(img):
    
    global x
    global y
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY)[1]

    countours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    countours = imutils.grab_contours(countours)
    c = max(countours, key = cv2.contourArea)
    
    #for c in countours:
    M = cv2.moments(c)
    if M["m00"] != 0:
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        
        #Contorno detectado en movimiento
        borde(img, c)
        cv2.drawContours(thresh, [c], 0, (0, 255, 0), 3)
        cv2.circle(img, (cX, cY), 7, (255, 255, 255), -1)
        
        if x == 0:
            x = cX
        if y == 0:
            y = cY
           
        if(x - cX != 0 or y - cY != 0): 
            mover(cX, cY)
            
        #Contorno principal
        cv2.circle(img, (x, y), 7, (0, 0, 255), -1)
        cv2.putText(img, "center (" + str(x - 20) + ", " + str(y - 20) + ")", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
def mover(cX, cY):
    global x
    global y
    """
    if(cX < x):
        print("Mover " + str(x - cX) + " a la derecha")
    else:
        print("Mover " + str(cX - x) + " a la izquierda")
        
    if(cY < y):
        print("Mover " + str(y - cY) + " hacia abajo")
    else:
        print("Mover " + str(cY - y) + " hacia arriba")
    """
    
def borde(frame, contorno):
    marker = cv2.minAreaRect(contorno)
    box = cv2.boxPoints(marker) if imutils.is_cv2() else cv2.boxPoints(marker)
    box = np.int0(box)
    cv2.drawContours(frame, [box], -1, (0, 255, 0), 2)   
    
def consumer():
    r = requests.get(POSITION_END_POINT)
    if r.status_code == 200:
        content = r.json()
        return content

def diferencia(content):
    difx = x - content['x']
    dify = y - content['y']
    
    headers = {
        'Content-Type': 'application/json',
    }
        
    difference = {
        "difx": difx,
        "dify": dify
    }
    
    r = requests.post(DIFFERENCE_END_POINT, headers=headers, data=json.dumps(difference))
    
    if r.status_code == 200:
        print("(" + str(difx) + "," + str(dify) + ")")

#Servicios web
POSITION_END_POINT = "https://position-service.herokuapp.com/position"
DIFFERENCE_END_POINT = "https://position-service.herokuapp.com/process"


#Distancia base
KNOWN_DISTANCE = 10

#Ancho de imagen
KNOWN_WIDTH = 1800

cap = cv2.VideoCapture("http://148.240.92.98:31299/live/C5/playlist_dvr_range-1552589657-197.m3u8")

inicio = False
left = 0
top = 0

while True:
    _, frame = cap.read()
    marker = frame
    
    if frame is not None:
        frame = imutils.resize(frame, width=frame.shape[0])
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = np.dstack([frame, frame, frame])
    #marker = find_marker(frame)

        decodedObjects = pyzbar.decode(frame)
        for obj in decodedObjects:
            if obj.type == "QRCODE":
                #Posición inicial del QR
                if not inicio :
                    content = consumer()
                    x = content['x']
                    y = content['y']
                    #print("Coordenada inicial: (" + str(obj.rect.width) + ", " + str(obj.rect.height) + ")")
                    #left = obj.rect.left
                    #top = obj.rect.top
                    inicio = True
                else :
                    content = consumer()
                    diferencia(content)
                
                marker = find_marker(frame)
                box = cv2.boxPoints(marker) if imutils.is_cv2() else cv2.boxPoints(marker)
                box = np.int0(box)
                cv2.drawContours(frame, [box], -1, (0, 255, 0), 2)
                
                if(obj.rect.width != 0):
                    distancia = distance_to_camera(obj.rect.width)
                    cv2.putText(frame, "%.2fcm " % distancia, (frame.shape[1] - 300, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 0), 3)
    
        #centrar(frame)
        cv2.imshow("Camera:", frame)
    
    key = cv2.waitKey(1)
    if key == 27:
        break

cv2.destroyAllWindows()