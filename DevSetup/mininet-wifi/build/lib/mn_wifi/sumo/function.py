from mn_wifi.sumo import traci


def intersect(a, b):
    """ return the intersection of two lists """
    return list(set(a) & set(b))


def initialisation(ListVeh, ListTravelTime, ListVisited, Visited,
                   time, speed, vehID, vehCmds):
    # enregistrement de chaque vehicule qui apparait et initialisation des Lists
    ListVeh.append(vehID)
    ListTravelTime.append([])
    ListVisited.append([])

    # enregistrement pour chaque vehicule du premier lien visite
    ListVisited[ListVeh.index(vehID)].append(vehCmds.getRoadID(vehID))
    Visited.append([])

    # initialisation du premier lien visite pour chaque vehicule
    Visited[ListVeh.index(vehID)] = vehCmds.getRoadID(vehID)
    time.append(0)
    speed.append(0)

    # initialisation de la vitesse du vehicule sur le lien actuel
    speed[ListVeh.index(vehID)] = vehCmds.getSpeed(vehID)

    return ListVeh, ListTravelTime, ListVisited, Visited, time, speed


def noChangeSaveTimeAndSpeed(Visited, ListVeh, time, speed,
                             vehID, vehCmds):

    if Visited[ListVeh.index(vehID)] == vehCmds.getRoadID(vehID) or (Visited[ListVeh.index(vehID)] != vehCmds.getRoadID(vehID))  and not(vehCmds.getRoadID(vehID) in vehCmds.getRoute(vehID)):
        time[ListVeh.index(vehID)] = time[ListVeh.index(vehID)] + 1
        speed[ListVeh.index(vehID)] = speed[ListVeh.index(vehID)] + vehCmds.getSpeed(vehID)

    # si le vehicule change de lien sur un pas de temps : enregistrement du temps et de la vitesse
    if time[ListVeh.index(vehID)] == 0 and Visited[ListVeh.index(vehID)] != vehCmds.getRoadID(vehID):
        time[ListVeh.index(vehID)] = time[ListVeh.index(vehID)] + 1
        speed[ListVeh.index(vehID)] = speed[ListVeh.index(vehID)] + vehCmds.getSpeed(vehID)

    return Visited, time, speed


def changeSaveTimeAndSpeed(Visited, ListVeh, time, speed, ListVisited, vehID, ListTravelTime, vehCmds):
    # le vehicule change de lien
    if (Visited[ListVeh.index(vehID)] != vehCmds.getRoadID(vehID)) \
            and (vehCmds.getRoadID(vehID) in vehCmds.getRoute(vehID)):
        S = speed[ListVeh.index(vehID)]
        T = time[ListVeh.index(vehID)]
        if S > 0 and T > 0:

            # enregistrement du temps de parcours du lien precedent
            ListTravelTime[ListVeh.index(vehID)].append(S / T)

        # mis a jour du nouveau lien
        Visited[ListVeh.index(vehID)] = vehCmds.getRoadID(vehID)

        # enregistrement du parcours
        ListVisited[ListVeh.index(vehID)].append(vehCmds.getRoadID(vehID))

        # mis a jour du temps et de a vitesse
        time[ListVeh.index(vehID)] = 0
        speed[ListVeh.index(vehID)] = 0
    return Visited, time, speed, ListVisited, ListTravelTime


def reroutage(VisitedEdge2, ListTravelTime, vehID1, vehID2, ListVeh, vehCmds):
    if len(VisitedEdge2) > 0:
        # reroutage du vehicule 1 en fonction des donnees collectees
        for edge in VisitedEdge2:
            TravelTime = ListTravelTime[ListVeh.index(vehID2)]
            traci.edge.adaptTraveltime(edge, TravelTime[VisitedEdge2.index(edge)])
            vehCmds.rerouteTraveltime(vehID1)

        # mis a jour du temps de parcours des liens modifies pour le reroutage
        for edge in VisitedEdge2:
            lane = edge + '_0'
            L = traci.lane.getLength(lane)
            S = traci.lane.getMaxSpeed(lane)
            # poids initial : longueur/Vitesse max
            T = L / S
            traci.edge.adaptTraveltime(edge, T)


def stop(vehID, vehCmds):
    try:
        setSpeed(vehID, 0, vehCmds)
        #setSpeedMode(vehID, 0, vehCmds)
        roadID = vehCmds.getRoadID(vehID)
        pos = vehCmds.getLanePosition(vehID)
        laneIndex = vehCmds.getLaneIndex(vehID)
        #vehCmds.setStop(vehID, roadID, pos=pos, laneIndex=laneIndex)
    except traci.exceptions.TraCIException:
        pass


def resume(vehID, vehCmds):
    try:
        setSpeed(vehID, 12, vehCmds)
        vehCmds.resume(vehID)  # this seems to not work as expected
    except traci.exceptions.TraCIException:
        pass


def setSpeedMode(vehID, speed, vehCmds):
    try:
        vehCmds.setSpeedMode(vehID, speed)
    except traci.exceptions.TraCIException:
        pass


def setSpeed(vehID, speed, vehCmds):
    try:
        vehCmds.setSpeed(vehID, speed)
    except traci.exceptions.TraCIException:
        pass


def rerouteEffort(vehID, vehCmds):
    try:
        vehCmds.rerouteEffort(vehID)
    except traci.exceptions.TraCIException:
        pass


def rerouteTraveltime(vehID, vehCmds):
    try:
        vehCmds.rerouteTraveltime(vehID)
    except traci.exceptions.TraCIException:
        pass


def setRouteID(vehID, vehCmds, *args):
    try:
        routeID = str(args[0])
        vehCmds.setRouteID(vehID, routeID)
    except traci.exceptions.TraCIException:
        pass