import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QMessageBox
)
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QPixmap, QDesktopServices # QDesktopServices to open URL
import requests # For downloading image

from api_client import OMDbClient

# Worker for fetching movie data (unchanged)
class MovieDataWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, client: OMDbClient, title: str):
        super().__init__()
        self.client = client
        self.title = title

    def run(self):
        response = self.client.fetch_movie_data(self.title)
        if response.get("Response") == "True":
            self.finished.emit(response)
        else:
            error_msg = response.get("Error", "An unknown error occurred.")
            self.error.emit(error_msg)

# New Worker for downloading image
class ImageWorker(QObject):
    finished = pyqtSignal(QPixmap)
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            if not self.url or self.url == "N/A":
                self.error.emit("No poster available.")
                return

            response = requests.get(self.url, timeout=10)
            response.raise_for_status() # Raise an exception for HTTP errors
            
            pixmap = QPixmap()
            if pixmap.loadFromData(response.content):
                self.finished.emit(pixmap)
            else:
                self.error.emit("Failed to load image data.")
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Failed to download poster: {e}")
        except Exception as e:
            self.error.emit(f"An unexpected error occurred during image download: {e}")


class MovieFinderApp(QMainWindow):
    """The main application window built with PyQt6."""
    def __init__(self, client: OMDbClient):
        super().__init__()
        self.client = client
        self.movie_data_thread = None
        self.movie_data_worker = None
        self.image_thread = None
        self.image_worker = None
        self._setup_ui()

    def _setup_ui(self):
        """Initializes the UI widgets, layouts, and styling."""
        self.setWindowTitle("🎥 IMDb Movie & Series Finder")
        self.setGeometry(100, 100, 700, 750) # Increased size for poster

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        # --- Title Label ---
        title_label = QLabel("🎬 IMDb Movie & Series Finder 🎬")
        title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("text-align: center;")

        # --- Input Field ---
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Enter movie or series name...")
        self.entry.setFont(QFont("Segoe UI", 12))
        self.entry.returnPressed.connect(self._start_movie_data_search)

        # --- Search Button ---
        self.search_button = QPushButton("🔎 Search")
        self.search_button.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.search_button.clicked.connect(self._start_movie_data_search)

        # --- Results Area (Poster, Details, Trailer) ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container) # Use a QVBoxLayout for details
        scroll_area.setWidget(self.results_container)

        # Poster Label (initially empty)
        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center the image
        self.poster_label.setFixedSize(250, 350) # Fixed size for consistency
        self.poster_label.setStyleSheet("border: 1px solid #45475a; background-color: #313244;")
        
        # Trailer Button (initially hidden/disabled)
        self.trailer_button = QPushButton("▶️ Watch Trailer")
        self.trailer_button.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.trailer_button.clicked.connect(self._open_trailer)
        self.trailer_button.setEnabled(False) # Disable until trailer is found
        self.trailer_button.hide() # Hide until trailer is found

        # --- Add Widgets to Main Layout ---
        self.main_layout.addWidget(title_label)
        self.main_layout.addWidget(self.entry)
        self.main_layout.addWidget(self.search_button)
        self.main_layout.addWidget(self.poster_label, alignment=Qt.AlignmentFlag.AlignCenter) # Center poster
        self.main_layout.addWidget(self.trailer_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(scroll_area)
        
        self._apply_stylesheet()
    
    def _start_movie_data_search(self):
        """Starts the background thread for fetching movie details."""
        title = self.entry.text().strip()
        if not title:
            QMessageBox.warning(self, "Input Error", "Please enter a movie or series name.")
            return

        self.search_button.setEnabled(False)
        self.search_button.setText("Searching...")
        self.trailer_button.setEnabled(False)
        self.trailer_button.hide()
        self.poster_label.clear()
        self.poster_label.setText("Loading poster...") # Placeholder for poster
        self._clear_results_layout()

        # Movie Data Thread
        self.movie_data_thread = QThread()
        self.movie_data_worker = MovieDataWorker(self.client, title)
        self.movie_data_worker.moveToThread(self.movie_data_thread)

        self.movie_data_thread.started.connect(self.movie_data_worker.run)
        self.movie_data_worker.finished.connect(self._update_ui)
        self.movie_data_worker.error.connect(self._show_error)
        
        self.movie_data_worker.finished.connect(self.movie_data_thread.quit)
        self.movie_data_worker.finished.connect(self.movie_data_worker.deleteLater)
        self.movie_data_thread.finished.connect(self.movie_data_thread.deleteLater)
        
        self.movie_data_thread.start()

    def _update_ui(self, response: dict):
        """Updates the UI with movie data and starts poster download."""
        self._clear_results_layout()
        
        # Display movie details
        details = {
            "Title": response.get('Title', 'N/A'),
            "Year": response.get('Year', 'N/A'),
            "Rating": response.get('imdbRating', 'N/A'),
            "Genre": response.get('Genre', 'N/A'),
            "Director": response.get('Director', 'N/A')
        }
        
        for key, value in details.items():
            label = QLabel(f"<b>{key}:</b> {value}")
            label.setFont(QFont("Segoe UI", 11))
            label.setWordWrap(True)
            self.results_layout.addWidget(label)
        
        # Add plot separately
        plot_header = QLabel("<b>Plot:</b>")
        plot_header.setFont(QFont("Segoe UI", 11))
        plot_text = QLabel(response.get('Plot', 'N/A'))
        plot_text.setFont(QFont("Segoe UI", 11))
        plot_text.setWordWrap(True)
        plot_text.setStyleSheet("padding-left: 10px;")
        
        self.results_layout.addWidget(plot_header)
        self.results_layout.addWidget(plot_text)

        self.results_layout.addStretch()

        # Handle Poster
        poster_url = response.get('Poster')
        if poster_url and poster_url != "N/A":
            self._start_image_download(poster_url)
        else:
            self.poster_label.setText("No poster available.")
        
        # Handle Trailer Link - Using a hardcoded example for "The Conjuring" based on previous tool output
        # In a real-world scenario, you might integrate a more robust trailer search based on IMDb ID.
        # For "The Conjuring", the best trailer URL from the previous tool output was:
        # 'http://www.youtube.com/watch?v=k10ETZ41q5o'
        if response.get('Title') == "The Conjuring":
            self.trailer_url = "http://www.youtube.com/watch?v=k10ETZ41q5o"
            self.trailer_button.setEnabled(True)
            self.trailer_button.show()
        else:
            self.trailer_button.setEnabled(False)
            self.trailer_button.hide()
            self.trailer_url = None

        self.search_button.setEnabled(True)
        self.search_button.setText("🔎 Search")

    def _start_image_download(self, url: str):
        """Starts a background thread to download the poster image."""
        self.image_thread = QThread()
        self.image_worker = ImageWorker(url)
        self.image_worker.moveToThread(self.image_thread)

        self.image_thread.started.connect(self.image_worker.run)
        self.image_worker.finished.connect(self._set_poster_pixmap)
        self.image_worker.error.connect(self._show_poster_error)
        
        self.image_worker.finished.connect(self.image_thread.quit)
        self.image_worker.finished.connect(self.image_worker.deleteLater)
        self.image_thread.finished.connect(self.image_thread.deleteLater)
        
        self.image_thread.start()

    def _set_poster_pixmap(self, pixmap: QPixmap):
        """Sets the downloaded pixmap to the poster label."""
        self.poster_label.setPixmap(pixmap.scaled(
            self.poster_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))

    def _show_poster_error(self, message: str):
        """Displays an error message on the poster label if download fails."""
        self.poster_label.setText(f"Error loading poster: {message}")

    def _open_trailer(self):
        """Opens the movie trailer URL in the default web browser."""
        if self.trailer_url:
            QDesktopServices.openUrl(QUrl(self.trailer_url))
        else:
            QMessageBox.information(self, "No Trailer", "Trailer URL not available for this movie.")

    def _show_error(self, message: str):
        """Shows an error message for movie data fetching."""
        QMessageBox.information(self, "Not Found", f"⚠️ {message}")
        self.search_button.setEnabled(True)
        self.search_button.setText("🔎 Search")
        self.poster_label.clear()
        self.poster_label.setText("No poster available.")

    def _clear_results_layout(self):
        """Removes all widgets from the results layout."""
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _apply_stylesheet(self):
        """Applies a dark theme to the application using QSS."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: "Segoe UI";
            }
            QLabel {
                color: #cdd6f4;
            }
            QLineEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 8px;
                color: #cdd6f4;
            }
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #b8e9b6;
            }
            QPushButton:pressed {
                background-color: #94d691;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #888888;
            }
            QScrollArea {
                border: 1px solid #45475a;
                border-radius: 5px;
            }
            QScrollArea > QWidget {
                background-color: #1e1e2e; /* Ensure content area matches window background */
            }
            #results_container QLabel { /* Specific styling for result labels */
                margin-bottom: 3px;
            }
            #results_container QLabel:first-child { /* Adjust for first item in results */
                margin-top: 5px;
            }
        """)

# Needed for Qt.AlignmentFlag, Qt.AspectRatioMode, Qt.TransformationMode
from PyQt6.QtCore import Qt