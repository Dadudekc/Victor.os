import sys
from PyQt5.QtWidgets import QApplication
from interfaces.pyqt.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        # Log the exception details and exit gracefully
        print("An error occurred while running Dream.OS:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()