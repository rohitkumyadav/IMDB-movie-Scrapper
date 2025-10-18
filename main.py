import os
import sys
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from api_client import OMDbClient
from gui import MovieFinderApp

def main():
    """The main entry point for the application."""
    load_dotenv()
    
    try:
        api_key = os.getenv("OMDB_API_KEY")
        client = OMDbClient(api_key=api_key)
        
        # PyQt application setup
        app = QApplication(sys.argv)
        window = MovieFinderApp(client)
        window.show()
        sys.exit(app.exec())

    except ValueError as e:
        print(f"Configuration Error: {e}")
        # A simple popup can be shown even without the main app
        app = QApplication(sys.argv)
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setText(f"Configuration Error:\n\n{e}\nPlease check your .env file and restart.")
        error_box.setWindowTitle("Fatal Error")
        error_box.exec()

if __name__ == "__main__":
    main()