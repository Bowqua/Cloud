import threading
import os
import tkinter as tk
from requests import HTTPError
from Cloud_backup.upload.google_uploader import list_google_drive_files, download_files_from_google_drive
from Cloud_backup.upload.yandex_uploader import download_file_from_yandex
from upload.google_uploader import upload_file_to_google_drive, sync_directory_to_drive, get_or_create_folder_google_drive
from upload.yandex_uploader import upload_file_to_yandex_disk, sync_directory_to_yandex, get_or_create_folder_on_yandex, \
    list_yandex_directory
from Cloud_backup.utils import compress_path
from tkinter import ttk, messagebox, filedialog, Listbox, Scrollbar
from tkinterdnd2 import TkinterDnD, DND_FILES
from tokens import get_token, set_token
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

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

        list_frame = ttk.Frame(self.yandex_frame)
        list_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(5, 0))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.yandex_files_list = Listbox(list_frame, background="white")
        self.yandex_files_list.grid(row=0, column=0, sticky="nsew")

        scrollbar = Scrollbar(list_frame, orient="vertical", command=self.yandex_files_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.yandex_files_list.config(yscrollcommand=scrollbar.set)

        buttons_frame = ttk.Frame(self.yandex_frame)
        buttons_frame.grid(row=4, column=0, pady=10)

        self.download_button = ttk.Button(buttons_frame, text="Download", command=self.download_yandex)
        self.download_button.pack(side="left", padx=5)

        self.update_button = ttk.Button(buttons_frame, text="Update listings", command=self.start_list_update_thread)
        self.update_button.pack(side="left", padx=5)

        list_frame_google = ttk.Frame(self.google_frame)
        list_frame_google.grid(row=3, column=0, sticky="nsew", padx=10, pady=(5, 0))
        list_frame_google.rowconfigure(0, weight=1)
        list_frame_google.columnconfigure(0, weight=1)

        self.google_files_list = Listbox(list_frame_google, background="white")
        self.google_files_list.grid(row=0, column=0, sticky="nsew")

        google_scrollbar = Scrollbar(list_frame_google, orient="vertical", command=self.google_files_list.yview)
        google_scrollbar.grid(row=0, column=1, sticky="ns")
        self.google_files_list.config(yscrollcommand=google_scrollbar.set)

        google_buttons_frame = ttk.Frame(self.google_frame)
        google_buttons_frame.grid(row=4, column=0, pady=10)

        self.download_button_google = ttk.Button(google_buttons_frame, text="Download", command=self.download_google)
        self.download_button_google.pack(side="left", padx=5)

        self.refresh_button_google = ttk.Button(google_buttons_frame, text="Update listings", command=self.refresh_listing_google)
        self.refresh_button_google.pack(side="left", padx=5)

        self.google_files_data = []


    def download_selected_files_yandex(self):
        selected = self.istbox.curselection()
        if not selected:
            messagebox.showwarning("Yandex Disk", "Please select a file to download")
            return

        entry = self.listbox.get(selected[0])
        name = entry.split(" ")[0]
        local = filedialog.asksaveasfilename(initialfile=name)
        if not local:
            return
        try:
            download_file_from_yandex(f"Backup/{name}", local, self.yandex_token)
            messagebox.showinfo("Yandex Disk", f"Downloaded {name}")
        except Exception as e:
            messagebox.showerror("Yandex Disk", f"Error while downloading: {e}")


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
        self.after(0, lambda: self.yandex_button.config(
            text="Choose files", command=self.choose_yandex_files, state="normal"
        ))


    def on_drop_google(self, event):
        paths = self.tk.splitlist(event.data)
        self.start_upload_thread(paths, service="google")


    def on_drop_yandex(self, event):
        if not getattr(self, "yandex_token", None):
            messagebox.showwarning("Yandex Disk", "Please login to Yandex Disk first")
            return
        paths = self.tk.splitlist(event.data)
        self.start_upload_thread(paths, service="yandex")


    def choose_google_files(self):
        paths = filedialog.askopenfilenames()
        if paths:
            self.start_upload_thread(paths, service="google")


    def choose_yandex_files(self):
        if not getattr(self, "yandex_token", None):
            messagebox.showwarning("Yandex Disk", "Please login to Yandex Disk")
            return
        paths = filedialog.askopenfilenames(title="Select files to upload")
        if not paths:
            return
        self.start_upload_thread(paths, service="yandex")


    def start_upload_thread(self, paths, service):
        thread = threading.Thread(target=self.upload_work, args=(paths, service), daemon=True)
        thread.start()


    def upload_work(self, paths, service):
        total = len(paths)
        if service == "yandex":
            get_or_create_folder_on_yandex("Backup", self.yandex_token)
            base_remote = "Backup"
        else:
            access_token = self.google_token
            base_remote = get_or_create_folder_google_drive(
                "Backup", parent_id="root", access_token=access_token
            )

        for i, original_path in enumerate(paths, start=1):
            try:
                archive_path = compress_path(original_path)
                archive_name = os.path.basename(archive_path)
                if service == "yandex":
                    upload_file_to_yandex_disk(
                        archive_path,
                        f"{base_remote}/{archive_name}",
                        self.yandex_token
                    )
                else:
                    upload_file_to_google_drive(
                        archive_path,
                        parent_id=base_remote,
                        access_token=self.google_token
                    )
                os.remove(archive_path)

            except Exception as e:
                print(f"Error uploading {original_path}: {e}")

            percent = int(i / total * 100)
            self.after(0, lambda p=percent, svc=service: self.update_progress(svc, p))

        self.after(0, lambda: messagebox.showinfo(
            "Ready", f"Uploaded {total} items to {service}"
        ))


    def update_progress(self, service, percent):
        if service == "google":
            self.google_progress["value"] = percent
        else:
            self.yandex_progress["value"] = percent


    def refresh_listing(self):
        try:
            items = list_yandex_directory("Backup", self.yandex_token)

            if not items:
                self.listbox.insert("end", "No files found in Backup")
                return
        except Exception as e:
            messagebox.showerror("Yandex Disk", f"Error checking file: {e}")
            return

        self.listbox.delete(0, "end")
        for item in items:
            self.listbox.insert("end", f"{item['name']} ({item['type']})")


    def start_list_update_thread(self):
        if not self.yandex_token:
            messagebox.showerror("Error", "Please log in to Yandex first.")
            return
        thread = threading.Thread(target=self.update_yandex_listings, daemon=True)
        thread.start()


    def update_yandex_listings(self):
        self.after(0, self.yandex_files_list.delete, 0, "end")
        try:
            files = list_yandex_directory("Backup", self.yandex_token)
        except HTTPError as e:
            if e.response.status_code == 404:
                files = []
            else:
                return self.after(0, self.yandex_files_list.insert, "end", f"Error: {e}")

        if not files:
            self.after(0, self.yandex_files_list.insert, "end", "No files found in Backup")
        else:
            for item in files:
                self.after(0, self.yandex_files_list.insert, "end", item['name'])


    def download_yandex(self):
        sel = self.yandex_files_list.curselection()
        if not sel:
            messagebox.showwarning("Yandex Disk", "Please select a file")
            return
        filename = self.yandex_files_list.get(sel[0])
        local = filedialog.asksaveasfilename(initialfile=filename)
        if not local:
            return
        threading.Thread(
            target=self._download_worker,
            args=("yandex", filename, local),
            daemon=True
        ).start()


    def _download_worker(self, provider, remote_id, local_path):
        bar = self.yandex_progress if provider == "yandex" else self.google_progress
        self.after(0, bar.config, {'value': 0})
        try:
            if provider == "yandex":
                download_file_from_yandex(f"Backup/{remote_id}", local_path, self.yandex_token)
            else:
                svc = self.get_google_service()
                download_files_from_google_drive(svc, remote_id, local_path)

            self.after(0, bar.config, {'value': 100})
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"File '{os.path.basename(local_path)}' downloaded."
            ))
        except Exception as e:
            self.after(0, lambda error=e: messagebox.showerror(
                "Error", f"Download failed: {error}"
            ))
        finally:
            self.after(1500, bar.config, {'value': 0})


    def refresh_listing_google(self):
        if not self.google_token:
            messagebox.showwarning("Google Drive", "Please log in to Google first")
            return
        thread = threading.Thread(target=self.update_google_listings, daemon=True)
        thread.start()


    def update_google_listings(self):
        self.after(0, self.google_files_list.delete, 0, 'end')
        self.google_files_data.clear()
        service = self.get_google_service()
        if not service:
            return
        try:
            backup_folder_id = get_or_create_folder_google_drive("Backup", parent_id="root", access_token=self.google_token)
            items = list_google_drive_files(service, folder_id=backup_folder_id)
            if not items:
                self.after(0, self.google_files_list.insert, 'end', "No files found in Backup")
                return

            self.google_files_data = items
            for item in items:
                self.after(0, self.google_files_list.insert, 'end', item['name'])

        except Exception as e:
            self.after(0, self.google_files_list.insert, 'end', f"Error: {e}")


    def download_google(self):
        sel = self.google_files_list.curselection()
        if not sel:
            messagebox.showwarning("Google Drive", "Please select a file")
            return

        idx = sel[0]
        file_info = self.google_files_data[idx]
        name = file_info['name']
        file_id = file_info['id']
        local = filedialog.asksaveasfilename(initialfile=name)
        if not local:
            return

        threading.Thread(
            target=self._download_worker,
            args=("google", file_id, local),
            daemon=True
        ).start()


    def get_google_service(self):
        if not self.google_token:
            return None
        try:
            credentials = Credentials(token=self.google_token)
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            messagebox.showerror("Google Auth Error", f"Failed to build Google service: {e}")
            return None
