import threading
import os
import tkinter as tk
from upload.google_uploader import upload_file_to_google_drive, sync_directory_to_drive, get_or_create_folder_google_drive
from upload.yandex_uploader import upload_file_to_yandex_disk, sync_directory_to_yandex, create_folder_on_yandex
from tkinter import ttk, messagebox, filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES
from tokens import get_token, set_token

class CloudBackup(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cloud Backup")
        self.geometry("800x400")
        self.configure(background="#CBEEF3")
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.google_frame = ttk.LabelFrame(self, text="Google Drive")
        self.google_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.google_frame.columnconfigure(0, weight=0)
        self.google_frame.columnconfigure(1, weight=1)

        self.google_button = ttk.Button(self.google_frame, text="Login", command=self.auth_google)
        self.google_button.grid(row=0, column=0, columnspan=2, pady=10)

        existing = get_token("google_access")
        if existing:
            self.google_token = existing
            self.google_button.config(text="Choose files")
        else:
            self.google_token = None

        ttk.Label(self.google_frame, text="Move files here") \
            .grid(row=1, column=0, sticky="w", padx=(10, 5))

        self.google_drop = tk.Frame(self.google_frame, relief="sunken", borderwidth=1, height=30, background='white')
        self.google_drop.grid(row=1, column=1, sticky="ew", padx=(5, 10), pady=5)
        self.google_drop.drop_target_register(DND_FILES)
        self.google_drop.dnd_bind('<<Drop>>', self.on_drop_google)

        self.google_progress = ttk.Progressbar(self.google_frame, mode="determinate")
        self.google_progress.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 10))

        self.yandex_frame = ttk.LabelFrame(self, text="Yandex Disk")
        self.yandex_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.yandex_frame.columnconfigure(0, weight=0)
        self.yandex_frame.columnconfigure(1, weight=1)

        self.yandex_button = ttk.Button(self.yandex_frame, text="Login", command=self.auth_yandex)
        self.yandex_button.grid(row=0, column=0, columnspan=2, pady=10)

        existing = get_token("yandex")
        if existing:
            self.yandex_token = existing
            self.yandex_button.config(text="Choose files")
        else:
            self.yandex_token = None

        ttk.Label(self.yandex_frame, text="Move files here") \
            .grid(row=1, column=0, sticky="w", padx=(10, 5))

        self.yandex_drop = tk.Frame(self.yandex_frame, relief="sunken", borderwidth=1, height=30, background='white')
        self.yandex_drop.grid(row=1, column=1, sticky="ew", padx=(5, 10), pady=5)
        self.yandex_drop.drop_target_register(DND_FILES)
        self.yandex_drop.dnd_bind('<<Drop>>', self.on_drop_yandex)

        self.yandex_progress = ttk.Progressbar(self.yandex_frame, mode="determinate")
        self.yandex_progress.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 10))


    def auth_google(self):
        from authentification.google import start_google_auth
        start_google_auth(self.on_google_auth_done)


    def on_google_auth_done(self, token):
        set_token("google_access", token)
        self.google_token = token
        self.google_button.config(text="Choose files", command=self.choose_google_files)


    def auth_yandex(self):
        from authentification.yandex import start_yandex_auth
        start_yandex_auth(self.on_yandex_auth_done)


    def on_yandex_auth_done(self, token):
        set_token("yandex", token)
        self.yandex_token = token
        self.yandex_button.config(text="Choose files", command=self.choose_yandex_files)


    def on_drop_google(self, event):
        paths = self.tk.splitlist(event.data)
        self.start_upload_thread(paths, service="google")


    def on_drop_yandex(self, event):
        paths = self.tk.splitlist(event.data)
        self.start_upload_thread(paths, service="yandex")


    def choose_google_files(self):
        paths = filedialog.askopenfilenames()
        if paths:
            self.start_upload_thread(paths, service="google")


    def choose_yandex_files(self):
        paths = filedialog.askopenfilenames()
        if paths:
            self.start_upload_thread(paths, service="yandex")


    def start_upload_thread(self, paths, service):
        thread = threading.Thread(target=self.upload_work, args=(paths, service), daemon=True)
        thread.start()


    def upload_work(self, paths, service):
        total = len(paths)
        if service == "yandex":
            create_folder_on_yandex("Backup", self.yandex_token)
            base_remote = "Backup"
        else:
            base_remote = get_or_create_folder_google_drive(
                "Backup", parent_id="root", access_token=self.google_token
            )

        for i, local_path in enumerate(paths, start=1):
            name = os.path.basename(local_path)
            try:
                if os.path.isdir(local_path):
                    if service == "yandex":
                        sync_directory_to_yandex(
                            local_directory=local_path,
                            remote_directory=f"{base_remote}/{name}",
                            access_token=self.yandex_token
                        )
                    else:
                        sync_directory_to_drive(
                            local_directory=local_path,
                            parent_id=base_remote,
                            access_token=self.google_token
                        )
                else:
                    if service == "yandex":
                        upload_file_to_yandex_disk(
                            local_path,
                            f"{base_remote}/{name}",
                            self.yandex_token
                        )
                    else:
                        upload_file_to_google_drive(
                            local_path,
                            parent_id=base_remote,
                            access_token=self.google_token
                        )

            except Exception as e:
                print(f"Error uploading {local_path}: {e}")

            percent = int(i / total * 100)
            self.after(0, lambda p=percent, svc=service: self.update_progress(svc, p))

        self.after(0, lambda: messagebox.showinfo(
            "Ready", f"Uploaded {total} items в {service}"
        ))


    def update_progress(self, service, percent):
        if service == "google":
            self.google_progress["value"] = percent
        else:
            self.yandex_progress["value"] = percent
