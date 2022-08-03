from functions import *

#NoWinkraftPoints = getNoWindkraftPoints()
WinkraftPoints = getWinkraftPoints()

def FillDataSet(Points, label=True):
    length = len(Points)
    dfWP = pd.read_csv("WindkraftData.csv")
    alreadyDone = [(float(x[1:-1].split(", ")[0]), float(x[1:-1].split(", ")[1])) for x in dfWP["loc"].to_list()]
    
    for i, point in enumerate(Points):
        if point in alreadyDone:
            print("Already added point")
        else:
            d = {}
            d["loc"] = point
            d["umschließendeTags"] = getUnmschließendeTags(point)
            d["benachbarteTags"] = getBenachbarteTags(point)
            d["distanceAndWind"] = getDistancesAndWind(point)
            d["distancedPointInfo"] = getDistancedPointInfo(point)
            d["Label"] = label
            d.update(convertResVecToDict(PointInSchutzgebiet(point)))
            dfWP = dfWP.append(d, ignore_index = True)
            dfWP.to_csv("WindkraftData.csv", index=False)
            print("Added point", i+1, "/", length, "=", round((i+1)/length*100), "%")
FillDataSet(WinkraftPoints, True)
#FillDataSet(NoWinkraftPoints, False)
