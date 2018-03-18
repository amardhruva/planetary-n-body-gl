
from PyQt5.QtWidgets import QWidget, QApplication, QPushButton, QHBoxLayout


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.button = QPushButton('Test', self)

        mainLayout = QHBoxLayout()
        mainLayout.addWidget(self.button)

        self.setLayout(mainLayout)



if __name__ == '__main__':
    app = QApplication(['Yo'])
    window = MainWindow()
    window.show()
    app.exec_() 
