from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
import sys


def main():
    app = QApplication(sys.argv)
    main_window = QMainWindow()

    main_window.setWindowTitle("Practice window")
    main_window.setGeometry(100, 100, 400, 300)

    central = QWidget()
    main_window.setCentralWidget(central)
    label = QLabel("Example of label")
    button = QPushButton("Example Of pyqt5 PushButton")
    layout = QVBoxLayout()
    layout.addWidget(label)
    layout.addWidget(button)

    central.setLayout(layout)

    main_window.show()
    sys.exit(app.exec_())


main()
