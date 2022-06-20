import argparse
import glob
import os
import sys
from time import sleep

import numpy as np
from AppKit import NSScreen
from PyQt5.QtCore import QCoreApplication, QDir, QEvent, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStyle,
    QVBoxLayout,
    QWidget,
)


class PyQt_App(QApplication):
    def __init__(self, *args, childs) -> None:
        super().__init__(*args)
        self.childs = childs

    def mainloop(self):
        while len(self.childs > 0):
            if not self.childs.is_alive():
                self.childs.pop()
        sys.exit(self.exec_())


class Preview_Window(QMainWindow):
    def __init__(
        self, app, SCALE_FACTOR=1, title="Preview Window", parent=None
    ) -> None:
        super(Preview_Window, self).__init__(parent)
        self.app = app
        self.setWindowTitle(title)
        self.SCALE_FACTOR = SCALE_FACTOR
        self.set_buttons()
        self.wait_variable = 0
        # self.task = tk.IntVar()
        # self.protocol("WM_DELETE_WINDOW", self.on_closing)
        print("Setting up Window")
        self.set_window_size()
        print("Ready...")

    def set_window_size(
        self,
    ) -> None:
        self.screen_w = NSScreen.mainScreen().frame().size.width
        self.screen_h = NSScreen.mainScreen().frame().size.height
        self.size_x = self.screen_w / self.SCALE_FACTOR
        self.size_y = self.screen_h / self.SCALE_FACTOR
        self.offset_x = int(self.screen_w - self.size_x) // 2
        self.offset_y = int(self.screen_h - self.size_y) // 2
        self.resize(self.size_x, self.size_y)
        self.grid_size_x = int(self.size_x // 10)
        self.grid_size_y = int(self.size_y // 10)
        self.content_w = int(self.grid_size_x * 4.5)
        self.content_h = int(self.grid_size_y * 4.5)
        self.content_size = (self.content_w, self.content_h)

    def set_buttons(self):
        self.remove_button = QPushButton()
        self.remove_button.setEnabled(True)
        self.remove_button.setText("Remove")
        self.remove_button.clicked.connect(self.remove_file)
        self.continue_button = QPushButton()
        self.continue_button.setEnabled(True)
        self.continue_button.setText("Continue")
        self.continue_button.clicked.connect(self.next_preview)

    def set_img_content(self, src, dest):
        self.src_img = QLabel()
        self.dest_img = QLabel()

        self.src_img.resize(self.content_w, self.content_h)
        self.dest_img.setAlignment(Qt.AlignCenter)
        self.src_img.setAlignment(Qt.AlignCenter)
        self.dest_img.resize(self.content_w, self.content_h)

        # preview layout
        preview = QHBoxLayout()
        preview.addWidget(self.src_img)
        preview.addWidget(self.dest_img)

        self.pack_content(preview)

        for img, target in zip([src, dest], [self.src_img, self.dest_img]):
            self.openImage(img, target)

    def unload_content(self):
        pass
        # if "src_img" in self.__dict__.keys():
        #     print("Unloading Image")
        #     self.src_img = None
        #     self.dest_img = None
        if "src_video" in self.__dict__.keys():
            print("Unloading Video")
            for obj in [
                self.src_video,
                self.dest_video,
            ]:
                obj.stop()
            self.src_img.close()
            self.dest_img.close()
            self.src_widget = QVideoWidget()
            self.dest_widget = QVideoWidget()
        self.pack_content(None)

    def set_video_content(self, src, dest):
        self.src_video = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.dest_video = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.src_widget = QVideoWidget()
        self.dest_widget = QVideoWidget()

        # preview layout
        preview = QHBoxLayout()
        preview.addWidget(self.src_widget)
        preview.addWidget(self.dest_widget)

        self.src_video.setVideoOutput(self.src_widget)
        self.dest_video.setVideoOutput(self.dest_widget)

        self.pack_content(preview)

        for video, target in zip([src, dest], [self.src_video, self.dest_video]):
            self.openVideo(video, target)
            self.playVideo(target)

    def pack_content(self, preview):
        # Create a widget for window contents

        self.wid = QWidget(self)
        self.setCentralWidget(self.wid)

        # Buttons
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.remove_button)
        buttonLayout.addWidget(self.continue_button)

        # set layout
        layout = QVBoxLayout()
        if preview is not None:
            layout.addLayout(preview)
        layout.addLayout(buttonLayout)

        self.wid.setLayout(layout)

    def openImage(self, fileName, target):
        if fileName != "":
            print(f"Setting Image to {fileName}")
            pixmap = QPixmap(fileName)
            if pixmap.width() > pixmap.height():
                pixmap = pixmap.scaledToWidth(self.content_w)
                print("rescaling width")
            else:
                pixmap = pixmap.scaledToHeight(self.content_h)
                print("rescaling height")
            target.setPixmap(pixmap)

    def openVideo(self, fileName, target):
        if fileName != "":
            print(f"Setting Media to {fileName}")
            target.setMedia(QMediaContent(QUrl.fromLocalFile(fileName)))

    def playVideo(self, mediaPlayer):
        print("Starting Video")
        mediaPlayer.play()

    def exitCall(self):
        sys.exit(self.app.exec_())

    def remove_file(self):
        self.wait_variable = 2

    def next_preview(self):
        self.wait_variable = 1

    def wait_for_input(self):
        while not self.wait_variable:
            if QCoreApplication.closingDown():
                QCoreApplication.exit()
            QCoreApplication.processEvents()
            sleep(0.1)
        if self.wait_variable == 2:
            print("removing")
        else:
            print("continuing")
        self.wait_variable = 0

    def mediaStateChanged(self, state, mediaPlayer):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def positionChanged(self, position):
        self.positionSlider.setValue(position)

    def durationChanged(self, duration):
        self.positionSlider.setRange(0, duration)

    def setPosition(self, position):
        self.mediaPlayer.setPosition(position)

    def handleError(self):
        self.playButton.setEnabled(False)
        self.errorLabel.setText("Error: " + self.mediaPlayer.errorString())


def argparser():
    parser = argparse.ArgumentParser(description="Remove duplicate files")
    parser.add_argument(
        "-s", "--source", help="Directory to remove duplicates from", required=True
    )
    parser.add_argument("-d", "--dest", help="Directory compare with.", required=True)
    return parser.parse_args()


def preview_image(file, dest_file, app: Preview_Window):
    app.unload_content()
    app.set_img_content(file, dest_file)
    app.wait_for_input()


def preview_video(file, dest_file, app: Preview_Window):
    app.unload_content()
    app.set_video_content(file, dest_file)
    app.wait_for_input()


class DataIterator:
    def __init__(self, source, dest, app) -> None:
        self.source = source
        self.dest = dest
        self.app = app

    def stop(self):
        exit()

    def run(self):
        all_source_files = glob.glob(self.source + "/**/*.*", recursive=True)
        all_dest_files = glob.glob(self.dest + "/**/*.*", recursive=True)
        to_del = {}
        for file in all_source_files:
            filename = file.split("/")[-1]
            for dest_file in all_dest_files:
                dest_filename = dest_file.split("/")[-1]
                if filename == dest_filename:
                    if file not in to_del:
                        to_del[file] = []
                    to_del[file].append(dest_file)
                    if filename.endswith(".HEIC"):
                        print(f"Opening {file}")
                        preview_image(file, dest_file, self.app)
                    if filename.endswith(".MOV"):
                        print(f"Opening {file}")
                        preview_video(file, dest_file, self.app)


def iterate_data(args, app):
    data_iterator = DataIterator(args.source, args.dest, app, name="data_iterator")
    print("Initialized Thread")
    app.sub_program = data_iterator
    print("Starting Thread")
    data_iterator.start()


def main():
    # register_heif_opener()
    args = argparser()
    # os.remove(file)
    # print(len(to_del))
    # for k, v in to_del.items():
    #     print(f"{k},{v}")
    app = PyQt_App(sys.argv, childs=None)
    preview_window = Preview_Window(app, 1)
    app.childs = [preview_window]
    preview_window.show()
    data_iterator = DataIterator(args.source, args.dest, preview_window)
    data_iterator.run()
    # app.mainloop()


if __name__ == "__main__":
    main()

# TODO Images do net get updated anymore....
