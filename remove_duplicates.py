import argparse
import glob
import os
import sys
import threading
import tkinter as tk
from multiprocessing import parent_process
from tkinter import messagebox, ttk

import imageio
import numpy as np
from AppKit import NSScreen
from PIL import Image, ImageTk
from pillow_heif import register_heif_opener


class Preview_Window(tk.Tk):
    def __init__(self, SCALE_FACTOR=1, title="Preview Window") -> None:
        super().__init__()
        self.SCALE_FACTOR = SCALE_FACTOR
        self.title = title
        self.wait_var = tk.IntVar()
        self.task = tk.IntVar()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        print("Setting up Window")
        self.set_window_size()
        print("Setting up Buttons")
        self.set_buttons()
        print("setting default images")
        self.set_default_img_content()
        print("packing content")
        self.pack_content()
        print("Ready...")
        self.update()
        self.sub_program = None

    def set_buttons(self):
        self.remove_button = tk.Button(
            self, text="Remove", command=self.remove_src, width=20
        )
        self.continue_button = tk.Button(
            self, text="Continue", command=self.next_preview, width=20
        )

    def set_window_size(
        self,
    ) -> None:
        self.screen_w = NSScreen.mainScreen().frame().size.width
        self.screen_h = NSScreen.mainScreen().frame().size.height
        self.size_x = self.screen_w / self.SCALE_FACTOR
        self.size_y = self.screen_h / self.SCALE_FACTOR
        offset_x = int(self.screen_w - self.size_x) // 2
        offset_y = int(self.screen_h - self.size_y) // 2
        self.geometry("%dx%d+%d+%d" % (self.size_x, self.size_y, offset_x, offset_y))
        self.grid_size_x = int(self.size_x // 10)
        self.grid_size_y = int(self.size_y // 10)
        self.content_w = int(self.grid_size_x * 4.5)
        self.content_h = int(self.grid_size_y * 4.5)
        self.content_size = (self.content_w, self.content_h)

    def set_default_img_content(self):
        default = Image.new(mode="RGB", size=self.content_size)
        default = ImageTk.PhotoImage(default)
        self.src_panel = tk.Label(
            self,
            image=default,
            width=self.content_w,
            height=self.content_h,
            background="black",
        )
        self.dest_panel = tk.Label(
            self,
            image=default,
            width=self.content_w,
            height=self.content_h,
            background="black",
        )

    def pack_content(self):
        button_height = self.remove_button.winfo_reqheight()
        button_width = self.remove_button.winfo_reqwidth()
        panel_x = self.grid_size_x // 3
        panel_y = self.grid_size_y // 3
        middle = panel_x + self.content_w + (panel_x - button_width) // 2
        button_x, button_y = (middle, panel_y + self.content_h + button_height)
        self.src_panel.place(x=panel_x, y=panel_y)
        self.dest_panel.place(x=2 * panel_x + self.content_w, y=panel_y)
        self.remove_button.place(x=button_x, y=button_y)
        self.continue_button.place(
            x=button_x,
            y=button_y + button_height * 1.5,
        )

    def remove_src(self):
        self.task.set(1)
        self.next_preview()

    def next_preview(self):
        self.wait_var.set(0)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.withdraw()
            print("trying to close SubProgram")
            self.wait_var.set(-1)

    def wait_continue(self):
        self.update()
        self.next_preview()
        print("Waiting for user to push button")
        self.wait_variable(self.wait_var)
        print("Variable Changed!")
        if self.wait_var.get() == -1:
            print("User pressed cancel")
            os.kill(os.getpid(), 9)
        if self.task.get() == 1:
            print("removing")
            print("User pressed remove")
            # os.remove(file)
        else:
            print("User pressed continue")
            print("continuing", self.task)
        self.task.set(0)


def stream(label: tk.Label, video, content_size):
    video = np.array([im for im in video.iter_data()], dtype=np.uint8)
    while True:
        for image in video:
            image_frame = Image.fromarray(image)
            image_frame.thumbnail(content_size, Image.ANTIALIAS)
            frame_image = ImageTk.PhotoImage(image_frame)
            label.configure(image=frame_image)


def argparser():
    parser = argparse.ArgumentParser(description="Remove duplicate files")
    parser.add_argument(
        "-s", "--source", help="Directory to remove duplicates from", required=True
    )
    parser.add_argument("-d", "--dest", help="Directory compare with.", required=True)
    return parser.parse_args()


def preview_image(file, dest_file, app: Preview_Window):
    print(f"Current file: {file}")
    src_img = Image.open(file)
    dest_img = Image.open(dest_file)
    src_img.thumbnail(app.content_size, Image.ANTIALIAS)
    dest_img.thumbnail(app.content_size, Image.ANTIALIAS)
    src_img = ImageTk.PhotoImage(src_img)
    dest_img = ImageTk.PhotoImage(dest_img)
    app.src_panel["image"] = src_img
    app.dest_panel["image"] = dest_img
    app.wait_continue()


def preview_video(file, dest_file, app: Preview_Window):
    print(file)
    src_video = imageio.get_reader(file)
    dest_video = imageio.get_reader(dest_file)

    src_thread = KillableThread(
        target=stream, args=(app.src_panel, src_video, app.content_size)
    )
    dest_thread = KillableThread(
        target=stream, args=(app.dest_panel, dest_video, app.content_size)
    )

    src_thread.daemon = 1
    dest_thread.daemon = 1
    src_thread.start()
    dest_thread.start()
    app.wait_continue()
    src_thread.kill()
    dest_thread.kill()


class KillableThread(threading.Thread):
    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        self.__run_backup = self.run
        self.run = self.__run
        threading.Thread.start(self)

    def __run(self):
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, event, arg):
        if event == "call":
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, event, arg):
        if self.killed:
            if event == "line":
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True


class DataIterator(threading.Thread):
    def __init__(self, source, dest, app, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.source = source
        self.dest = dest
        self.app = app
        self.pid = os.getpid()
        print("Thread is Ready..")

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
                        preview_image(file, dest_file, self.app)
                    if filename.endswith(".MOV"):
                        preview_video(file, dest_file, self.app)


def iterate_data(args, app):
    data_iterator = DataIterator(args.source, args.dest, app, name="data_iterator")
    print("Initialized Thread")
    app.sub_program = data_iterator
    print("Starting Thread")
    data_iterator.start()


def main():
    register_heif_opener()
    args = argparser()
    app = Preview_Window(4)
    app.after(10, iterate_data, args, app)
    app.mainloop()
    # os.remove(file)
    # print(len(to_del))
    # for k, v in to_del.items():
    #     print(f"{k},{v}")


if __name__ == "__main__":
    main()

# TODO Images do net get updated anymore....
