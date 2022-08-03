#!/usr/bin/env python
# coding: utf-8
import os
import pandas as pd
import json
import requests
import fiona
from shapely.geometry import shape, mapping, Point, Polygon, MultiPolygon
import pyproj
import math
import threading                                                                

def distance(point1, point2):
    return ((point1[0]-point2[0])**2+(point1[1]-point2[1])**2)**0.5

def getSDOs(df):
    SDOs = list(df.SDO_ID.unique())
    SDOs.sort()
    return SDOs

def getPointBySDO_ID(df, SDO_ID):
    res = df[df['SDO_ID']==SDO_ID]
    point = tuple(res["loc"].to_list())
    return point[0]

def getSDODF():
    WinddatenSDO = "../data/Winddaten/data/sdo.csv"
    df = pd.read_csv(WinddatenSDO)
    df["loc"] = df.Geogr_Breite + ", " + df.Geogr_Laenge
    a = df["loc"].to_list()
    b = []
    for x, y in [x.split(", ") for x in a]:
        b.append((float((x.replace(",", "."))), float((y.replace(",", ".")))))
    df["loc"] = b
    return df

def getWindDF():
    Winddaten = "../data/Winddaten/data/data.csv"
    df = pd.read_csv(Winddaten, sep=',')
    df.columns = ["SDO_ID", "Zeitstempel", "Wert", "Qualitaet_Byte", "Qualitaet_Niveau", "sth."]
    return df

def loadWindBySDO_ID(dfWind, SDO_ID):
    gf = dfWind.groupby("SDO_ID")
    #print("Winddurchschnitt von", dfWind.Zeitstempel.min(), "bis", dfWind.Zeitstempel.max())
    return gf.get_group(SDO_ID).Wert.mean()

def getDistancesAndWind(point):
    dfWind = getWindDF()
    dfSDO = getSDODF()
    SDOs = getSDOs(dfWind)
    #print(len(SDOs))
    a = {}
    for SDO_ID in SDOs:
        SDOPoint = getPointBySDO_ID(dfSDO, SDO_ID)
        d = distance(point, SDOPoint)
        w = loadWindBySDO_ID(dfWind, SDO_ID)
        a[SDO_ID] = [d, w]
    return a

def getBenachbarteTags(point):
    x, y = point
    #benachbarte Objekte
    data = f"data=%5Btimeout%3A10%5D%5Bout%3Ajson%5D%3B(node(around%3A50%2C{x}%2C{y})%3Bway(around%3A50%2C{x}%2C{y})%3B)%3Bout+tags+geom({x-0.01}%2C{y-0.01}%2C{x+0.01}%2C{y+0.01})%3Brelation(around%3A50%2C{x}%2C{y})%3Bout+geom({x-0.01}%2C{y-0.01}%2C{x+0.01}%2C{y+0.01})%3B"
    response = requests.post('https://query.openstreetmap.org/query-features', data=data)
    res = json.loads(response.text)
    features = {}
    #return res
    for entry in res["elements"]:
        a = entry.get("tags")
        if a:
            for key, value in a.items():
                if "name" not in key:
                    features.update({key:value})
    return features

def getUnmschließendeTags(point):
    x, y = point
    #unmschließendes Objekte
    data = f"data=%5Btimeout%3A10%5D%5Bout%3Ajson%5D%3Bis_in({x}%2C{y})-%3E.a%3Bway(pivot.a)%3Bout+tags+bb%3Bout+ids+geom({x}%2C{y}%2C{x}%2C{y})%3Brelation(pivot.a)%3Bout+tags+bb%3B"
    response = requests.post('https://query.openstreetmap.org/query-features', data=data)
    res = json.loads(response.text)
    features = {}
    #return res
    for entry in res["elements"]:
        a = entry.get("tags")
        if a:
            for key, value in a.items():
                if "name" not in key:
                    features.update({key:value})
    return features

def getDistancedPointInfo(point):
    x, y = point
    data = f"https://nominatim.openstreetmap.org/search.php?q={x}%2C{y}&polygon_geojson=1&format=jsonv2"
    response = requests.get(data)
    res = json.loads(response.text)[0]
    features = {}
    #return res
    features["category"] = res.get("category")
    features["type"] = res.get("type")
    return features

P = pyproj.Proj(proj='utm', zone=31, ellps='WGS84', preserve_units=True)
G = pyproj.Geod(ellps='WGS84')

def LatLon_To_XY(Lat,Lon):
    return P(Lat,Lon)

def XY_To_LatLon(x,y):
    return P(x,y,inverse=True)   

def PointInPoly(point, geojsonPath):
    multipol = fiona.open(geojsonPath)
    for multi in multipol:
        if Point(point).within(shape(multi['geometry'])):
            return True
    return False 

def PointInSchutzgebiet(a):
    point = LatLon_To_XY(a[1], a[0])
    path = "../data/Schutzgebiete/"
    files = ["../data/Schutzgebiete/"+f for f in os.listdir(path) if f[-4:]=="json"]
    res = [i for i in range(len(files))]
    for i, geojsonPath in enumerate(files):
        #print(f"Scanning {geojsonPath}")
        if PointInPoly(point, geojsonPath):
            res[i]=1
        else:
            res[i]=0
    return res      

def convertResVecToDict(res):
    columns = ["Naturmonumente", "Nationalparke", "Vogelschutzgebiet", "Landschaftsschutzgebiete", "Naturschutzgebiete", "Biosphaerenreservate"]
    dictRes = {}
    for i in range(len(columns)):
        dictRes[columns[i]] = res[i]
    return dictRes

def getWinkraftPoints():
    df = pd.read_csv("../prepData/CoordsWindkraftanlagen.csv")
    a = [x.split(", ") for x in df["loc"].to_list()]
    b= []
    for x,y in a:
        b.append([float(x), float(y)])
    WinkraftPoints = [tuple(x) for x in b]
    return WinkraftPoints

def getNoWindkraftPoints():
    df = pd.read_csv("../prepData/CoordsNoWindkraftanlagen.csv")
    points = []
    for item in df["loc"].to_list():
        x, y = item[1:-1].split(", ")
        points.append((float(x), float(y)))
    return points
