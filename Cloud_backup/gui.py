import threading
import os
from tkinter import ttk, messagebox
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

        self.google_drop = ttk.Frame(self.google_frame, relief="sunken", borderwidth=1)
        self.google_drop.grid(row=1, column=1, sticky="ew", padx=(5, 10))
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

        self.yandex_drop = ttk.Frame(self.yandex_frame, relief="sunken", borderwidth=1)
        self.yandex_drop.grid(row=1, column=1, sticky="ew", padx=(5, 10))
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
        self.google_button.config(text="Choose files")


    def auth_yandex(self):
        from authentification.yandex import start_yandex_auth
        start_yandex_auth(self.on_yandex_auth_done)


    def on_yandex_auth_done(self, token):
        set_token("yandex", token)
        self.yandex_token = token
        self.yandex_button.config(text="Choose files")


    def on_drop_google(self, event):
        paths = self.tk.splitlist(event.data)
        self.start_upload_thread(paths, service="google")


    def on_drop_yandex(self, event):
        paths = self.tk.splitlist(event.data)
        self.start_upload_thread(paths, service="yandex")


    def start_upload_thread(self, paths, service):
        thread = threading.Thread(target=self.upload_work, args=(paths, service), daemon=True)
        thread.start()


    def upload_work(self, paths, service):
        total = len(paths)
        for i, local_path in enumerate(paths, start=1):
            remote_path = f"/Backup/{os.path.basename(local_path)}"
            try:
                if service == "google":
                    from upload.google_uploader import upload_file_to_google_drive
                    upload_file_to_google_drive(local_path, parent_id="root", access_token=self.google_token)
                else:
                    from upload.yandex_uploader import upload_file_to_yandex_disk
                    upload_file_to_yandex_disk(local_path, remote_path, self.yandex_token)
            except Exception as e:
                print(f"Error uploading {local_path}: {e}")

            percent = int(i / total * 100)
            self.after(0, lambda p=percent, svc=service: self.update_progress(svc, p))
        self.after(0, lambda: messagebox.showinfo("Ready", f"Uploaded {total} files in {service}"))


    def update_progress(self, service, percent):
        if service == "google":
            self.google_progress["value"] = percent
        else:
            self.yandex_progress["value"] = percent
