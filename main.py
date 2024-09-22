import tkinter as tk
from tkinter import messagebox
import customtkinter
import os
import time
import json
import threading
import winreg as reg
import subprocess

temp_dir = os.path.join(os.environ.get('SystemRoot'), 'Temp')
additional_dir = os.path.join(os.environ.get('TEMP'))
delete_at_reboot_file = 'delete_at_reboot.txt'
stop_timer_flag = False
scheduled_time_exists = False

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("green")

class TempFileDeletionApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Temporary Files Deletion Tool")
        self.geometry("720x480")
        self.create_widgets()
        self.remaining_time_label = customtkinter.CTkLabel(self, text="", anchor="w")
        self.remaining_time_label.pack(side="left", padx=10, pady=10)
        self.load_timer_data()
  
    def create_widgets(self):
        frame = customtkinter.CTkFrame(master=self, corner_radius=20)
        frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        self.label = customtkinter.CTkLabel(master=frame, text="Select an option:")
        self.label.pack(pady=10)

        self.delete_button = customtkinter.CTkButton(master=frame, text="Delete Files Immediately",
                                                    command=self.delete_files,
                                                    height=50,
                                                    width=300,
                                                    corner_radius=10)
        self.delete_button.pack(pady=10)

        self.schedule_button = customtkinter.CTkButton(master=frame, text="Schedule Deletion of Temporary Files", 
                                                        command=self.display_schedule_options,
                                                        height=50,
                                                        width=300,
                                                        corner_radius=10)
        self.schedule_button.pack(pady=10)

        self.stop_button = customtkinter.CTkButton(master=frame, text="Stop Scheduled Deletion", 
                                                    command=self.stop_scheduled_deletion,
                                                    height=50,
                                                    width=300,
                                                    corner_radius=10)
        self.stop_button.pack(pady=10)
        
        self.return_button = customtkinter.CTkButton(master=frame, text="4. Return to Main Menu", 
                                                    command=self.reset_to_main_menu,
                                                    height=50,
                                                    width=300,
                                                    corner_radius=10)

    def list_temp_files(self):
        temp_files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
        additional_files = [f for f in os.listdir(additional_dir) if os.path.isfile(os.path.join(additional_dir, f))]
        return temp_files + additional_files

    def delete_temp_files(self, files):
        for file in files:
            if not os.path.isdir(os.path.join(temp_dir, file)):
                try:
                    os.remove(os.path.join(temp_dir, file))
                    self.label.configure(text=f"Deleted file: {file}", text_color="green", justify="left")
                except PermissionError:
                    self.label.configure(text=f"Access denied for file: {file}. Skipping...", text_color="green", justify="left")

    def schedule_deletion_files(self, files, delay_seconds):
        with open(delete_at_reboot_file, 'w') as f:
            f.write(f"{int(time.time()) + delay_seconds}\n")
            f.write("\n".join(files))

    def remove_scheduled_deletion(self):
        global stop_timer_flag, scheduled_time_exists
        if os.path.exists(delete_at_reboot_file):
            os.remove(delete_at_reboot_file)
            stop_timer_flag = True
            scheduled_time_exists = False
            self.remove_registry_entry()
            self.label.configure(text="Scheduled deletion stopped.")
            self.remaining_time_label.configure(text="")
        else:
            self.label.configure(text="No scheduled deletion is currently active.")

    def remove_registry_entry(self):
        key = reg.HKEY_CURRENT_USER
        key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        script_name = os.path.splitext(os.path.basename(__file__))[0]

        try:
            with reg.OpenKey(key, key_path, 0, reg.KEY_SET_VALUE) as reg_key:
                reg.DeleteValue(reg_key, script_name)
                self.label.configure(text=f"Removed {script_name} from Windows Registry.")
        except FileNotFoundError:
            self.label.configure(text=f"File not found: {script_name}")
        except PermissionError:
            self.label.configure(text="Permission denied when attempting to delete registry value.")

    def create_scheduled_task_on_startup(self):
        command = f"schtasks /create /tn TempFileDeletionTask /tr {os.path.abspath(__file__)} /sc onstart /ru System /RL HIGHEST /F /V1 /IT /K"
        subprocess.run(command, shell=True)
        
    def create_startup_entry(self):
        key = reg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        script_path = os.path.abspath(__file__)
        script_name = os.path.splitext(os.path.basename(__file__))[0]

        try:
            reg_key = reg.OpenKey(key, key_path, 0, reg.KEY_SET_VALUE)
            reg.SetValueEx(reg_key, script_name, 0, reg.REG_SZ, script_path)
            reg.CloseKey(reg_key)
            print(f"Added {script_name} to Windows Registry to run on startup.")
        except Exception as e:
            print(f"An error occurred: {e}")


    def create_scheduled_task(self, task_name, python_script_path, trigger_string, working_directory):
        command = f"schtasks /create /tn {task_name} /tr {python_script_path} /sc once /st {trigger_string} /sd 01/01/1901 /ru System /RL HIGHEST /F /V1 /IT /K"
        subprocess.run(command, shell=True, cwd=working_directory)

    def check_existing_scheduled_time(self):
        global scheduled_time_exists
        if os.path.exists(delete_at_reboot_file):
            scheduled_time_exists = True
        else:
            scheduled_time_exists = False

    def display_schedule_options(self):
        global scheduled_time_exists
        self.check_existing_scheduled_time()
        if not scheduled_time_exists:
            self.label.configure(text="Select the delay option:")
            self.delete_button.configure(text="1. Delete after one day", command=lambda: self.schedule_deletion(1))
            self.schedule_button.configure(text="2. Delete after one week", command=lambda: self.schedule_deletion(7))
            self.stop_button.configure(text="3. Delete after one month", command=lambda: self.schedule_deletion(30))
            self.return_button.pack(pady=10)
        else:
            self.label.configure(text="Scheduled time already set. Please stop the current scheduled time to set a new one.")
            self.remaining_time_label.configure(text="")

    def reset_to_main_menu(self):
        self.return_button.pack_forget()
        self.label.configure(text="Select an option:")
        self.delete_button.configure(text="Delete Files Immediately", command=self.delete_files)
        self.schedule_button.configure(text="Schedule Deletion of Temporary Files", command=self.display_schedule_options)
        self.stop_button.configure(text="Stop Scheduled Deletion", command=self.stop_scheduled_deletion)

    def load_timer_data(self):
        timer_data_file = 'timer_data.json'
        if os.path.exists(timer_data_file):
            with open(timer_data_file, 'r') as f:
                data = json.load(f)
                self.end_time = data['end_time']
                self.stop_timer_flag = data['stop_timer_flag']
                if not self.stop_timer_flag:
                    threading.Thread(target=self.display_remaining_time, args=(self.end_time, self.list_temp_files())).start()

    def save_timer_data(self):
        timer_data = {'end_time': self.end_time, 'stop_timer_flag': self.stop_timer_flag}
        with open('timer_data.json', 'w') as f:
            json.dump(timer_data, f)

    def display_remaining_time(self, end_time, files):
        global stop_timer_flag
        while time.time() < end_time and not stop_timer_flag:
            remaining_time = end_time - time.time()
            hours, remainder = divmod(remaining_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))
            self.remaining_time_label.configure(text=f"Time remaining for deletion: {time_str}")
            time.sleep(1)
        if not stop_timer_flag:
            self.remaining_time_label.configure(text="Deleting temporary files...")
            self.delete_temp_files(files)
            self.remaining_time_label.configure(text="Temporary files deleted.")
            self.remove_scheduled_deletion() 

    def delete_files(self):
        temp_files = self.list_temp_files()
        self.delete_temp_files(temp_files)
        self.label.configure(text="Temporary files deleted immediately.")

    def stop_scheduled_deletion(self):
        self.remove_scheduled_deletion()

    def schedule_deletion(self, days):
        global stop_timer_flag, scheduled_time_exists
        stop_timer_flag = False
        self.check_existing_scheduled_time()
        if not scheduled_time_exists:
            delay_seconds = days * 24 * 60 * 60
            temp_files = self.list_temp_files()
            self.label.configure(text=f"Scheduling deletion of temporary files in {days} days...")
            end_time = time.time() + delay_seconds
            threading.Thread(target=self.display_remaining_time, args=(end_time, temp_files)).start()
            self.schedule_deletion_files(temp_files, delay_seconds)
            self.create_startup_entry()
            self.create_scheduled_task("TempFileDeletionTask", os.path.abspath(__file__), "15:00", os.getcwd())
            self.reset_to_main_menu()
        else:
            self.label.configure(text="Scheduled time already set. Please stop the current scheduled time to set a new one.")


if __name__ == "__main__":
    app = TempFileDeletionApp()
    app.create_scheduled_task_on_startup()
    app.mainloop()
