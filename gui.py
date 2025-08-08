#!/usr/bin/env python3
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox,
                             QProgressBar, QCheckBox, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from sonex import MediaOrganizer  # Import your existing script

class Worker(QThread):
    progress_updated = pyqtSignal(int)
    message_updated = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, organizer, camera_path, destination_path):
        super().__init__()
        self.organizer = organizer
        self.camera_path = camera_path
        self.destination_path = destination_path

    def run(self):
        try:
            self.organizer.camera_path = self.camera_path
            self.organizer.destination_root = self.destination_path
            self.organizer.save_config()

            files = []
            for root, _, filenames in os.walk(self.camera_path):
                for filename in filenames:
                    files.append(os.path.join(root, filename))

            total_files = len(files)
            processed = 0

            for file_path in files:
                date_str = self.organizer.get_creation_date(file_path)
                destination_dir = os.path.join(self.destination_path, date_str)
                os.makedirs(destination_dir, exist_ok=True)

                if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                    output_filename = os.path.splitext(os.path.basename(file_path))[0] + '.jpg'
                    output_path = os.path.join(destination_dir, output_filename)
                    self.organizer.convert_image_to_jpg(file_path, output_path)
                elif file_path.lower().endswith(('.mts', '.cpi')):
                    output_filename = os.path.splitext(os.path.basename(file_path))[0] + '.m2ts'
                    output_path = os.path.join(destination_dir, output_filename)
                    if file_path.lower().endswith('.cpi'):
                        video_file = self.organizer.find_associated_video(file_path)
                        if video_file:
                            self.organizer.convert_to_m2ts(video_file, output_path)
                    else:
                        self.organizer.convert_to_m2ts(file_path, output_path)

                processed += 1
                progress = int((processed / total_files) * 100)
                self.progress_updated.emit(progress)
                self.message_updated.emit(f"Processing: {os.path.basename(file_path)}")

            self.finished.emit(True)
        except Exception as e:
            self.message_updated.emit(f"Error: {str(e)}")
            self.finished.emit(False)

class MediaOrganizerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Media Organizer")
        self.setGeometry(100, 100, 600, 400)

        self.organizer = MediaOrganizer()

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # Path selection group
        path_group = QGroupBox("Path Selection")
        path_layout = QVBoxLayout()

        # Camera path
        camera_layout = QHBoxLayout()
        self.camera_label = QLabel("Camera Path:")
        self.camera_path = QLineEdit()
        self.camera_path.setReadOnly(True)
        self.camera_browse = QPushButton("Browse...")
        self.camera_browse.clicked.connect(self.browse_camera)
        camera_layout.addWidget(self.camera_label)
        camera_layout.addWidget(self.camera_path)
        camera_layout.addWidget(self.camera_browse)

        # Destination path
        dest_layout = QHBoxLayout()
        self.dest_label = QLabel("Destination Path:")
        self.dest_path = QLineEdit()
        self.dest_path.setReadOnly(True)
        self.dest_browse = QPushButton("Browse...")
        self.dest_browse.clicked.connect(self.browse_destination)
        dest_layout.addWidget(self.dest_label)
        dest_layout.addWidget(self.dest_path)
        dest_layout.addWidget(self.dest_browse)

        path_layout.addLayout(camera_layout)
        path_layout.addLayout(dest_layout)
        path_group.setLayout(path_layout)

        # Progress group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status_label = QLabel("Ready")
        self.log_text = QLabel("")

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.log_text)
        progress_group.setLayout(progress_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Organizing")
        self.start_button.clicked.connect(self.start_organizing)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_operation)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)

        # Add all to main layout
        layout.addWidget(path_group)
        layout.addWidget(progress_group)
        layout.addLayout(button_layout)

        # Load saved paths
        self.load_saved_paths()

    def load_saved_paths(self):
        self.organizer.load_config()
        self.camera_path.setText(self.organizer.camera_path)
        self.dest_path.setText(self.organizer.destination_root)

    def browse_camera(self):
        path = QFileDialog.getExistingDirectory(self, "Select Camera Directory")
        if path:
            self.camera_path.setText(path)

    def browse_destination(self):
        path = QFileDialog.getExistingDirectory(self, "Select Destination Directory")
        if path:
            self.dest_path.setText(path)

    def start_organizing(self):
        camera_path = self.camera_path.text()
        dest_path = self.dest_path.text()

        if not camera_path:
            QMessageBox.warning(self, "Error", "Please select a camera path")
            return

        if not dest_path:
            QMessageBox.warning(self, "Error", "Please select a destination path")
            return

        if not os.path.exists(camera_path):
            QMessageBox.warning(self, "Error", "Camera path does not exist")
            return

        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Processing...")
        self.progress_bar.setValue(0)
        self.log_text.setText("")

        self.worker = Worker(self.organizer, camera_path, dest_path)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.message_updated.connect(self.update_log)
        self.worker.finished.connect(self.operation_finished)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_log(self, message):
        self.log_text.setText(message)

    def operation_finished(self, success):
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        if success:
            self.status_label.setText("Completed successfully!")
            QMessageBox.information(self, "Success", "Media organization completed successfully!")
        else:
            self.status_label.setText("Operation failed")
            QMessageBox.critical(self, "Error", "Media organization failed. See log for details.")

    def cancel_operation(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.status_label.setText("Operation cancelled")
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = MediaOrganizerGUI()
    gui.show()
    sys.exit(app.exec_())
