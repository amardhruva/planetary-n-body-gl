import json
from collections import deque

import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtCore import QTimer, QAbstractTableModel, Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QOpenGLWidget, QDialog
from PyQt5.uic import loadUi

FPS = 60
DELTA = .001
# Decrease this to increase performance decrease trail length
TOTAL_TRAILS = 400
# Decrease this to increase trail quality decrease trail length
TRAIL_THRESHOLD = 100

TRANSLATION_SPEED = 10
ROTATION_SPEED = .1

GRAVITY_CONSTANT = 1000


def toCart(theta, phi):
    theta, phi = np.radians(theta), np.radians(phi)
    x = np.cos(phi) * np.sin(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(theta)
    return np.array([-x, -y, z])


class Planet:

    def paint(self):
        glColor3fv(self.color)
        glPointSize(7)
        glBegin(GL_POINTS)
        glVertex3fv(self.pos)
        glEnd()

        glLineWidth(2)
        glBegin(GL_LINE_STRIP)
        for i in self.trail:
            glVertex3fv(i)
        glVertex3fv(self.pos)
        glEnd()

    def calculate(self):
        self.vel += self.accel * DELTA
        self.pos += self.vel * DELTA
        if self.trailcount >= TRAIL_THRESHOLD:
            self.addTrail()
            self.trailcount -= TRAIL_THRESHOLD
        else:
            self.trailcount += 1

    def addTrail(self):
        self.trail.append(np.copy(self.pos))

    def __init__(self, pos=[0, 0, 0], vel=[0, 0, 0], mass=100, name="Earth", color=(1, 1, 1), radius=10):

        self.accel = np.array([0, 0, 0], np.float64)
        self.mass, self.radius = 10, 10

        self.color = color
        self.name = str(name)
        self.pos = np.array(pos, np.float64)
        self.vel = np.array(vel, np.float64)
        self.mass = float(mass)
        self.radius = float(radius)
        self.trailcount = 0
        self.trail = deque(maxlen=TOTAL_TRAILS)
        self.addTrail()

    def toDict(self):
        d = {
            "name": self.name,
            "pos": self.pos.tolist(),
            "vel": self.vel.tolist(),
            "mass": self.mass,
            "color": self.color,
            "radius": self.radius,
        }
        return d


class PlanetModel(QAbstractTableModel):
    horizontalHeaders = ["Name", "X", "Y", "Z"]

    def toDict(self):
        d = [x.toDict() for x in self.planets]
        return d

    def fromdict(self, d):
        self.planets = [
            Planet(x["pos"], x["vel"], x["mass"], x["name"], x["color"], x["radius"]) for x in d
        ]
        self.emitDataChanged()

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self.horizontalHeaders)

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self.planets)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            row = index.row()
            column = index.column()
            planet = self.planets[row]
            if column == 0:
                return planet.name
            elif column == 1:
                return str(planet.pos[0])
            elif column == 2:
                return str(planet.pos[1])
            elif column == 3:
                return str(planet.pos[2])

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.horizontalHeaders[section]
            if orientation == Qt.Vertical:
                return section + 1

    def __init__(self, tableView, parent=None):  # real signature unknown; restored from __doc__
        super(PlanetModel, self).__init__(parent)
        self.planets = []
        tableView.setModel(self)

    def addPlanet(self, planet):
        self.planets.append(planet)
        a = self.index(0, 0)
        self.layoutChanged.emit()

    def emitDataChanged(self):
        self.dataChanged.emit(self.createIndex(1, 0), self.createIndex(3, self.rowCount()))


class MyGLWidget(QOpenGLWidget):
    def __init__(self, *args, **kwargs):
        super(MyGLWidget, self).__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)
        self.pressedKeys = {}
        self.pressedMouseButtons = {}
        self.camera = {"pos": np.array([0, 0, -1000], np.float64), "angle": np.array([0, 0, 0], np.float64)}

    def initializeGL(self):
        glLoadIdentity()
        glEnable(GL_DEPTH_TEST)
        gluPerspective(45, 1, 0.1, 5000)
        glPushMatrix()

    def resizeGL(self, x, y):
        pass

    def paintGL(self):
        glPopMatrix()
        glPushMatrix()
        angle = self.camera["angle"]
        pos = self.camera["pos"]
        glRotatef(angle[1], 1, 0, 0)
        glRotatef(angle[0], 0, 1, 0)
        glRotatef(angle[2], 0, 0, 1)
        glTranslatef(pos[0], pos[1], pos[2])
        for x in self.planetModel.planets:
            x.paint()

    def calculate(self):
        for i in self.planetModel.planets:
            i.accel = np.array([0, 0, 0], np.float64)
            for j in self.planetModel.planets:
                if i is not j:
                    dx = j.pos - i.pos
                    distance = np.sum(np.square(dx))
                    i.accel += (GRAVITY_CONSTANT * j.mass / (distance ** 1.5)) * dx

        for x in self.planetModel.planets:
            x.calculate()

    def keyPressEvent(self, k):
        self.pressedKeys[k.key()] = True

    def keyReleaseEvent(self, k):
        self.pressedKeys[k.key()] = False

    def mousePressEvent(self, m):
        self.pressedMouseButtons[m.button()] = True
        self.previousMousePos = m.localPos()

    def mouseReleaseEvent(self, m):
        self.pressedMouseButtons[m.button()] = False

    def mouseMoveEvent(self, m):
        self.makeCurrent()
        currentPos = m.localPos()
        diff = self.previousMousePos - currentPos
        self.camera["angle"] += ROTATION_SPEED * np.array([diff.x(), diff.y(), 0])
        self.previousMousePos = currentPos
        self.repaint()

    def handleInput(self):
        angle = self.camera["angle"]
        if self.pressedKeys.get(Qt.Key_W, False):
            self.camera["pos"] += TRANSLATION_SPEED * toCart(angle[0], angle[1])
        if self.pressedKeys.get(Qt.Key_S, False):
            self.camera["pos"] -= TRANSLATION_SPEED * toCart(angle[0], angle[1])
        if self.pressedKeys.get(Qt.Key_A, False):
            self.camera["pos"] += TRANSLATION_SPEED * toCart(angle[0]-90, angle[1])
        if self.pressedKeys.get(Qt.Key_D, False):
            self.camera["pos"] -= TRANSLATION_SPEED * toCart(angle[0]-90, angle[1])
        if self.pressedKeys.get(Qt.Key_F, False):
            self.camera["pos"] -= TRANSLATION_SPEED * toCart(angle[0], angle[1]+90)
        if self.pressedKeys.get(Qt.Key_R, False):
            self.camera["pos"] += TRANSLATION_SPEED * toCart(angle[0], angle[1]+90)


class AddPlanetForm(QDialog):

    def __init__(self, parent=None):
        super(AddPlanetForm, self).__init__(parent)
        loadUi('addplanetdialog.ui', self)


class MyMainWindow(QMainWindow):

    def runButtonToggle(self, state):
        self.state = state

    def addPlanetClicked(self):
        self.dialog = AddPlanetForm(self)
        self.dialog.setVisible(True)

    def saveTriggered(self):
        d = self.planetModel.toDict()
        with open("save.json", "w") as fp:
            fp.write(json.dumps(d, indent=4))

    def loadTriggered(self):
        with open("save.json", "r") as fp:
            d = json.loads(fp.read())
        self.planetModel.fromdict(d)

    def timerTimeout(self):
        self.openGLWidget.handleInput()
        if self.state:
            speed = self.speedSlider.value()
            for i in range(speed):
                self.openGLWidget.calculate()
        self.openGLWidget.repaint()
        self.planetModel.emitDataChanged()

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        loadUi('mainwindow.ui', self)
        self.runButtonToggle(False)
        self.planetModel = PlanetModel(self.tableView)
        self.openGLWidget.planetModel = self.planetModel
        self.runButton.toggled.connect(self.runButtonToggle)
        self.addPlanetButton.clicked.connect(self.addPlanetClicked)
        self.actionSave.triggered.connect(self.saveTriggered)
        self.actionLoad.triggered.connect(self.loadTriggered)
        self.timer = QTimer()
        self.timer.timeout.connect(self.timerTimeout)
        self.timer.setInterval(1000 / FPS)
        self.planetModel.addPlanet(Planet([-100, 0, 0], [0, -20, 0], 10))
        self.planetModel.addPlanet(Planet([0, 0, 0], [0, 0, 0], 100))
        p = Planet([+100, 0, 0], [0, 0, +25], 10)
        p.name = "Mars"
        p.color = (0, 1, 0)
        self.planetModel.addPlanet(p)
        self.timer.start()


def main():
    app = QApplication(["hmm"])
    window = MyMainWindow()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
