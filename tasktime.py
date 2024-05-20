import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import time
import threading
import pickle

def day_of_week_to_int(day_of_week_str):
    day_of_week_map = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}
    return day_of_week_map.get(day_of_week_str, -1)

class Task:
    def __init__(self, description, start_time, duration_hours, duration_minutes, day_of_week):
        self.description = description
        self.start_time = datetime.datetime.strptime(start_time, "%H:%M")
        self.day_of_week = day_of_week
        duration = int(duration_hours) * 60 + int(duration_minutes)
        self.end_time = self.start_time + datetime.timedelta(minutes=duration)
        self.notified_start = False
        self.notified_end = False

    def overlaps_with(self, other_task):
        return self.day_of_week == other_task.day_of_week and not (self.end_time <= other_task.start_time or self.start_time >= other_task.end_time)

class TaskApp:
    def __init__(self, root):
        self.root = root
        self.root.title("タスク管理ツール")
        self.root.geometry("800x600")

        self.tasks = {day: [] for day in ["月", "火", "水", "木", "金", "土", "日"]}  # 初期化
        self.editing_task_index = None

        self.setup_ui()
        self.load_tasks()  # タスクをロードして表示
        self.start_notification_thread()

    def setup_ui(self):
        large_font = ('Verdana', 12)
        self.notebook = ttk.Notebook(self.root)
        self.tabs = {}
        self.listboxes = {}

        for day in ["月", "火", "水", "木", "金", "土", "日"]:
            tab = tk.Frame(self.notebook)
            self.notebook.add(tab, text=day)
            self.tabs[day] = tab
            listbox = tk.Listbox(tab, font=large_font, width=50, height=15)
            listbox.pack(padx=10, pady=10)
            listbox.bind('<<ListboxSelect>>', self.on_task_select)
            self.listboxes[day] = listbox

        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        control_frame = tk.Frame(self.root)
        control_frame.pack(fill="x", padx=10, pady=5)
        self.build_control_panel(control_frame, large_font)

        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="タスクを表示", command=self.show_saved_tasks)
        menubar.add_cascade(label="ファイル", menu=file_menu)

    def build_control_panel(self, frame, font):
        self.day_of_week_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.start_hour_var = tk.StringVar()
        self.start_minute_var = tk.StringVar()
        self.duration_hours_var = tk.StringVar()
        self.duration_minutes_var = tk.StringVar()
        self.copy_to_day_var = tk.StringVar()

        tk.Label(frame, text="曜日:", font=font).grid(row=0, column=0, padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.day_of_week_var, values=["月", "火", "水", "木", "金", "土", "日"], width=5, font=font).grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(frame, text="タスクの説明:", font=font).grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.description_var, font=font, width=30).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(frame, text="開始時刻:", font=font).grid(row=2, column=0, padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.start_hour_var, values=[f"{i:02d}" for i in range(24)], width=5, font=font).grid(row=2, column=1, sticky="w", padx=5)
        ttk.Combobox(frame, textvariable=self.start_minute_var, values=[f"{i:02d}" for i in range(0, 60, 5)], width=5, font=font).grid(row=2, column=1, padx=60)

        tk.Label(frame, text="作業時間:", font=font).grid(row=3, column=0, padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.duration_hours_var, values=[f"{i}" for i in range(0, 24)], width=5, font=font).grid(row=3, column=1, sticky="w", padx=5)
        ttk.Combobox(frame, textvariable=self.duration_minutes_var, values=[f"{i:02d}" for i in range(0, 60, 5)], width=5, font=font).grid(row=3, column=1, padx=60)

        tk.Button(frame, text="タスク追加/編集", command=self.add_or_edit_task, font=font, width=20).grid(row=4, column=0, columnspan=2, pady=5)
        tk.Button(frame, text="入力クリア", command=self.clear_inputs, font=font, width=20).grid(row=5, column=0, columnspan=2, pady=5)
        tk.Button(frame, text="タスク削除", command=self.remove_selected_task, font=font, width=20).grid(row=6, column=0, columnspan=2, pady=5)

        tk.Label(frame, text="コピー先の曜日:", font=font).grid(row=7, column=0, padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.copy_to_day_var, values=["月", "火", "水", "木", "金", "土", "日"], width=5, font=font).grid(row=7, column=1, sticky="w", padx=5)
        tk.Button(frame, text="タスクをコピー", command=self.copy_tasks, font=font, width=20).grid(row=8, column=0, columnspan=2, pady=5)

        tk.Button(frame, text="タスク保存", command=self.save_tasks, font=font, width=20).grid(row=9, column=0, columnspan=2, pady=5)

    def on_task_select(self, event):
        if not event.widget.curselection():
            return
        index = event.widget.curselection()[0]
        day_of_week = self.notebook.tab(self.notebook.select(), "text")
        task = self.tasks[day_of_week][index]
        self.editing_task_index = (day_of_week, index)

        self.day_of_week_var.set(day_of_week)
        self.description_var.set(task.description)
        self.start_hour_var.set(task.start_time.strftime("%H"))
        self.start_minute_var.set(task.start_time.strftime("%M"))
        duration_hours, remainder = divmod((task.end_time - task.start_time).seconds, 3600)
        duration_minutes = remainder // 60
        self.duration_hours_var.set(str(duration_hours))
        self.duration_minutes_var.set(f"{duration_minutes:02d}")

    def add_or_edit_task(self):
        day_of_week = self.day_of_week_var.get()
        description = self.description_var.get()
        start_time = f"{self.start_hour_var.get()}:{self.start_minute_var.get()}"
        duration_hours = self.duration_hours_var.get()
        duration_minutes = self.duration_minutes_var.get()

        if not day_of_week or not description or not start_time or not duration_hours or not duration_minutes:
            messagebox.showwarning("警告", "すべてのフィールドを入力してください。")
            return

        new_task = Task(description, start_time, duration_hours, duration_minutes, day_of_week)

        if self.editing_task_index and self.editing_task_index[0] == day_of_week:
            for idx, task in enumerate(self.tasks[day_of_week]):
                if idx != self.editing_task_index[1] and new_task.overlaps_with(task):
                    messagebox.showwarning("エラー", f"{day_of_week}曜日のタスクの時間が重複しています。")
                    return
            self.tasks[day_of_week][self.editing_task_index[1]] = new_task
        else:
            for task in self.tasks[day_of_week]:
                if new_task.overlaps_with(task):
                    messagebox.showwarning("エラー", f"{day_of_week}曜日のタスクの時間が重複しています。")
                    return
            self.tasks[day_of_week].append(new_task)

        self.update_task_listbox(day_of_week)
        self.clear_inputs()

    def clear_inputs(self):
        self.day_of_week_var.set("")
        self.description_var.set("")
        self.start_hour_var.set("")
        self.start_minute_var.set("")
        self.duration_hours_var.set("")
        self.duration_minutes_var.set("")
        self.editing_task_index = None

    def update_task_listbox(self, day_of_week):
        self.listboxes[day_of_week].delete(0, tk.END)
        for task in sorted(self.tasks[day_of_week], key=lambda t: t.start_time):
            self.listboxes[day_of_week].insert(tk.END, f"{task.description} ({task.start_time.strftime('%H:%M')} - {task.end_time.strftime('%H:%M')})")
        total_duration = sum((task.end_time - task.start_time for task in self.tasks[day_of_week]), datetime.timedelta())
        hours, remainder = divmod(total_duration.seconds, 3600)
        minutes = remainder // 60
        self.listboxes[day_of_week].insert(tk.END, f"合計時間: {hours}時間{minutes}分")
        self.listboxes[day_of_week].itemconfig(tk.END, {'fg': 'blue'})

    def remove_selected_task(self):
        if not self.editing_task_index:
            messagebox.showwarning("警告", "削除するタスクを選択してください。")
            return
        day_of_week, index = self.editing_task_index
        del self.tasks[day_of_week][index]
        self.update_task_listbox(day_of_week)
        self.clear_inputs()

    def copy_tasks(self):
        source_day = self.day_of_week_var.get()
        target_day = self.copy_to_day_var.get()

        if not source_day or not target_day or source_day == target_day:
            messagebox.showwarning("警告", "異なる曜日を選択してください。")
            return

        self.tasks[target_day] = [
            Task(task.description, task.start_time.strftime("%H:%M"),
                 str(int((task.end_time - task.start_time).total_seconds() // 3600)),
                 str(int((task.end_time - task.start_time).total_seconds() % 3600 // 60)),
                 target_day) for task in self.tasks[source_day]
        ]

        self.update_task_listbox(target_day)
        messagebox.showinfo("完了", f"{source_day}から{target_day}へのタスクコピーが完了しました。")

    def save_tasks(self):
        with open('tasks.pkl', 'wb') as f:
            pickle.dump(self.tasks, f)
        messagebox.showinfo("保存完了", "タスクが正常に保存されました。")

    def show_saved_tasks(self):
        saved_tasks_window = tk.Toplevel(self.root)
        saved_tasks_window.title("保存されたタスク")
        saved_tasks_window.geometry("600x400")

        scrollbar = tk.Scrollbar(saved_tasks_window)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_area = tk.Text(saved_tasks_window, yscrollcommand=scrollbar.set)
        text_area.pack(fill=tk.BOTH, expand=True)

        for day, tasks in self.tasks.items():
            text_area.insert(tk.END, f"--- {day}曜日 ---\n")
            for task in tasks:
                text_area.insert(tk.END, f"{task.description} ({task.start_time.strftime('%H:%M')} - {task.end_time.strftime('%H:%M')})\n")
            total_duration = sum((task.end_time - task.start_time for task in tasks), datetime.timedelta())
            hours, remainder = divmod(total_duration.seconds, 3600)
            minutes = remainder // 60
            text_area.insert(tk.END, f"合計時間: {hours}時間{minutes}分\n\n")

        scrollbar.config(command=text_area.yview)

        text_area.config(state=tk.DISABLED)

    def load_tasks(self):
        try:
            with open('tasks.pkl', 'rb') as f:
                self.tasks = pickle.load(f)
        except FileNotFoundError:
            self.tasks = {day: [] for day in ["月", "火", "水", "木", "金", "土", "日"]}

    def start_notification_thread(self):
        self.notification_thread = threading.Thread(target=self.monitor_tasks, daemon=True)
        self.notification_thread.start()

    def monitor_tasks(self):
        while True:
            now = datetime.datetime.now()
            for day, tasks in self.tasks.items():
                for task in tasks:
                    self.check_and_notify_task(task, now)
            time.sleep(60)

    def check_and_notify_task(self, task, now):
        task_day_of_week = day_of_week_to_int(task.day_of_week)
        if now.weekday() == task_day_of_week:
            task_start = datetime.datetime.combine(now.date(), task.start_time.time())
            task_end = datetime.datetime.combine(now.date(), task.end_time.time())
            if now >= task_start and not task.notified_start:
                self.root.after(0, lambda: messagebox.showinfo("タスク開始通知", f"タスク '{task.description}' の時間です！"))
                task.notified_start = True
            elif now >= task_end and not task.notified_end:
                self.root.after(0, lambda: messagebox.showinfo("タスク終了通知", f"タスク '{task.description}' が終了しました。"))
                task.notified_end = True

def main():
    root = tk.Tk()
    app = TaskApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.save_tasks(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()
