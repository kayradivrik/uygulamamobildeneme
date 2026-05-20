import os
import sqlite3
import datetime
import random
import wave
import struct
import math
import sys
import traceback

def global_exception_handler(exctype, value, tb):
    print(f"CRITICAL ERROR: {exctype} - {value}")
    traceback.print_tb(tb)
    # In a real app, you might save this to a log file or send to a crashlytics service

sys.excepthook = global_exception_handler

from kivy.lang import Builder
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ObjectProperty
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line
from kivy.uix.filechooser import FileChooserIconView

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.button import MDFillRoundFlatButton, MDRoundFlatButton, MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.card import MDCard
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem
from kivy.core.audio import SoundLoader

# ==========================================
# NOTIFICATION HELPER (Plyer Integration)
# ==========================================
def send_local_notification(title, message):
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="Choppa YKS",
            timeout=5
        )
    except Exception as e:
        print(f"Notification error: {e}")

# ==========================================
# BACKUP FILE PATH HELPER
# ==========================================
def get_backup_path():
    if os.path.exists('/sdcard/Download'):
        return '/sdcard/Download/yks_backup.json'
    elif os.path.exists('/sdcard'):
        return '/sdcard/yks_backup.json'
    return os.path.join(os.path.expanduser('~'), 'yks_backup.json')


# ==========================================
# AUDIO BEEP GENERATOR (For Pomodoro alert)
# ==========================================
def generate_beep_sound(filename="alert.wav"):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(filepath):
        return
    try:
        sample_rate = 44100.0
        duration = 0.5  # seconds
        frequency = 1000.0  # Hz
        
        wave_file = wave.open(filepath, 'w')
        wave_file.setparams((1, 2, int(sample_rate), 0, 'NONE', 'not compressed'))
        
        for i in range(int(duration * sample_rate)):
            value = int(32767.0 * math.sin(2.0 * math.pi * frequency * (i / sample_rate)))
            data = struct.pack('<h', value)
            wave_file.writeframesraw(data)
        wave_file.close()
    except Exception as e:
        print(f"Beep sound generation failed: {e}")

def play_alert_sound():
    try:
        sound_path = os.path.join(os.path.dirname(__file__), "alert.wav")
        if os.path.exists(sound_path):
            sound = SoundLoader.load(sound_path)
            if sound:
                sound.play()
    except Exception as e:
        print(f"Ses calinamadi: {e}")

# ==========================================
# DATABASE MANAGER
# ==========================================
class DatabaseManager:
    def __init__(self, db_name="yks_choppa.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 1. Tasks Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    is_completed INTEGER DEFAULT 0,
                    date TEXT NOT NULL
                )
            """)
            
            # 2. Daily Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    math_questions INTEGER DEFAULT 0,
                    mock_exams INTEGER DEFAULT 0,
                    notes TEXT
                )
            """)
            
            # Apply migration to add math_progress and paragraph_progress
            try:
                cursor.execute("ALTER TABLE daily_logs ADD COLUMN math_progress INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # already exists
            try:
                cursor.execute("ALTER TABLE daily_logs ADD COLUMN paragraph_progress INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # already exists
            
            # 3. Questions Table (Choppa Math Gym logs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    user_answer TEXT NOT NULL,
                    is_correct INTEGER NOT NULL
                )
            """)
            
            # 4. Mock Exams Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mock_exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    exam_type TEXT NOT NULL,
                    tr_correct INTEGER NOT NULL,
                    tr_wrong INTEGER NOT NULL,
                    soc_correct INTEGER NOT NULL,
                    soc_wrong INTEGER NOT NULL,
                    math_correct INTEGER NOT NULL,
                    math_wrong INTEGER NOT NULL,
                    sci_correct INTEGER NOT NULL,
                    sci_wrong INTEGER NOT NULL,
                    net REAL NOT NULL
                )
            """)
            
            # 5. Streaks Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS streaks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    count INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database init error: {e}")

    def export_to_json(self, filepath):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            tables = ["tasks", "daily_logs", "questions", "mock_exams", "streaks"]
            backup_data = {}
            
            for table in tables:
                c.execute(f"SELECT * FROM {table}")
                columns = [desc[0] for desc in c.description]
                rows = c.fetchall()
                backup_data[table] = [dict(zip(columns, row)) for row in rows]
                
            conn.close()
            
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=4)
            return True, "Yedekleme basariyla tamamlandi!"
        except Exception as e:
            return False, f"Disa aktarma hatasi: {str(e)}"

    def import_from_json(self, filepath):
        try:
            import json
            with open(filepath, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
                
            conn = self.get_connection()
            c = conn.cursor()
            
            tables = ["tasks", "daily_logs", "questions", "mock_exams", "streaks"]
            
            for table in tables:
                if table not in backup_data:
                    conn.close()
                    return False, f"Gecersiz yedek dosyasi: {table} tablosu bulunamadi."
                    
            for table in tables:
                c.execute(f"DELETE FROM {table}")
                rows = backup_data[table]
                if not rows:
                    continue
                    
                columns = list(rows[0].keys())
                placeholders = ", ".join(["?"] * len(columns))
                sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                
                for row in rows:
                    values = [row[col] for col in columns]
                    c.execute(sql, values)
                    
            conn.commit()
            conn.close()
            return True, "Veriler basariyla geri yuklendi!"
        except Exception as e:
            return False, f"Ice aktarma hatasi: {str(e)}"

    def setup_default_tasks_for_today(self):
        today = datetime.date.today().isoformat()
        try:
            conn = self.get_connection()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM tasks WHERE date = ?", (today,))
            count = c.fetchone()[0]
            if count == 0:
                defaults = [
                    "Pomodoro ile 25 dk Odaklan",
                    "Choppa Math Gym'de 15 Soru Coz",
                    "TYT/AYT Analiz Girisi Yap",
                    "Bugunun Ders Notlarini Gozden Gecir"
                ]
                for task in defaults:
                    c.execute("INSERT INTO tasks (task_name, is_completed, date) VALUES (?, 0, ?)", (task, today))
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to setup default tasks: {e}")

    def get_current_streak(self):
        today = datetime.date.today()
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            # Check today's streak entry
            c.execute("SELECT count FROM streaks WHERE date = ?", (today.isoformat(),))
            row = c.fetchone()
            if row:
                streak = row[0]
                conn.close()
                return streak, True
            
            # Check yesterday's streak entry
            yesterday = (today - datetime.timedelta(days=1)).isoformat()
            c.execute("SELECT count FROM streaks WHERE date = ?", (yesterday,))
            row = c.fetchone()
            if row:
                streak = row[0]
                conn.close()
                return streak, False
            
            conn.close()
            return 0, False
        except Exception as e:
            print(f"Error checking streak: {e}")
            return 0, False

    def check_and_update_streak(self):
        today = datetime.date.today().isoformat()
        try:
            conn = self.get_connection()
            c = conn.cursor()
            c.execute("SELECT is_completed FROM tasks WHERE date = ?", (today,))
            tasks = c.fetchall()
            
            if not tasks:
                conn.close()
                return 0, False
                
            total = len(tasks)
            completed = sum(1 for t in tasks if t[0] == 1)
            all_done = (completed == total)
            
            if all_done:
                c.execute("SELECT count FROM streaks WHERE date = ?", (today,))
                row = c.fetchone()
                if row:
                    streak_val = row[0]
                else:
                    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
                    c.execute("SELECT count FROM streaks WHERE date = ?", (yesterday,))
                    y_row = c.fetchone()
                    yesterday_streak = y_row[0] if y_row else 0
                    
                    streak_val = yesterday_streak + 1
                    c.execute("INSERT OR REPLACE INTO streaks (date, count) VALUES (?, ?)", (today, streak_val))
                    conn.commit()
            else:
                c.execute("DELETE FROM streaks WHERE date = ?", (today,))
                conn.commit()
                
                yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
                c.execute("SELECT count FROM streaks WHERE date = ?", (yesterday,))
                y_row = c.fetchone()
                streak_val = y_row[0] if y_row else 0
                
            conn.close()
            return streak_val, all_done
        except Exception as e:
            print(f"Error updating streak: {e}")
            return 0, False

# ==========================================
# KV LAYOUT DESIGN STRING
# ==========================================
KV_STR = """
#:import Window kivy.core.window.Window

<DrawingCanvas>:
    canvas.before:
        Color:
            rgba: 0.1, 0.1, 0.12, 1
        Rectangle:
            pos: self.pos
            size: self.size

<CanvasCard>:
    orientation: 'vertical'
    padding: "16dp"
    spacing: "8dp"
    radius: [16, 16, 16, 16]
    md_bg_color: 0.15, 0.15, 0.18, 1
    elevation: 3
    shadow_color: 0, 0, 0, 0.6
    line_color: 1, 1, 1, 0.05
    line_width: 1
    
    MDBoxLayout:
        size_hint_y: None
        height: "40dp"
        spacing: "10dp"
        padding: ["8dp", 0, "8dp", 0]
        
        MDLabel:
            text: "Karalama Defteri"
            font_style: "Subtitle1"
            bold: True
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
            pos_hint: {"center_y": 0.5}
            
        MDIconButton:
            id: upload_btn
            icon: "file-image-outline"
            theme_text_color: "Custom"
            text_color: app.theme_cls.primary_color
            pos_hint: {"center_y": 0.5}
            opacity: 1 if root.show_upload else 0
            disabled: not root.show_upload
            on_release: root.open_image_chooser()
            
        MDIconButton:
            icon: "eraser"
            theme_text_color: "Custom"
            text_color: app.theme_cls.primary_color
            pos_hint: {"center_y": 0.5}
            on_release: root.clear_canvas()
            
    RelativeLayout:
        Image:
            id: bg_image
            source: root.bg_source
            allow_stretch: True
            keep_ratio: True
            pos_hint: {"center_x": 0.5, "center_y": 0.5}
            
        DrawingCanvas:
            id: drawing_canvas

<TaskItem>:
    orientation: 'horizontal'
    size_hint_y: None
    height: "56dp"
    padding: ["16dp", "4dp", "16dp", "4dp"]
    spacing: "12dp"
    md_bg_color: 0.2, 0.18, 0.25, 0.4
    radius: [12, 12, 12, 12]
    line_color: 1, 1, 1, 0.08
    line_width: 1
    
    MDCheckbox:
        id: cb
        active: root.is_completed
        size_hint: None, None
        size: "48dp", "48dp"
        pos_hint: {"center_y": 0.5}
        on_active: root.on_checkbox_active(self, self.active)
        
    MDLabel:
        text: root.task_name
        theme_text_color: "Custom"
        text_color: (1, 1, 1, 1) if not root.is_completed else (0.5, 0.5, 0.5, 0.7)
        font_style: "Body1"
        pos_hint: {"center_y": 0.5}
        halign: "left"
        valign: "middle"

    MDIconButton:
        icon: "trash-can-outline"
        theme_text_color: "Custom"
        text_color: (0.9, 0.3, 0.3, 1)
        pos_hint: {"center_y": 0.5}
        on_release: root.delete_task()

<HistoryItem>:
    orientation: 'horizontal'
    size_hint_y: None
    height: "64dp"
    padding: ["16dp", "8dp", "16dp", "8dp"]
    spacing: "12dp"
    md_bg_color: 0.15, 0.15, 0.18, 0.5
    radius: [12, 12, 12, 12]
    line_color: 1, 1, 1, 0.05
    line_width: 1
    
    MDIcon:
        icon: "check-circle-outline" if root.is_correct else "close-circle-outline"
        theme_text_color: "Custom"
        text_color: (0.2, 0.8, 0.2, 1) if root.is_correct else (0.9, 0.3, 0.3, 1)
        pos_hint: {"center_y": 0.5}
        font_size: "24sp"
        
    MDBoxLayout:
        orientation: 'vertical'
        pos_hint: {"center_y": 0.5}
        MDLabel:
            text: root.question_text
            font_style: "Body1"
            bold: True
        MDLabel:
            text: "Cevabiniz: " + root.user_answer + " (Dogru: " + root.correct_answer + ")"
            font_style: "Caption"
            theme_text_color: "Secondary"

<ExamHistoryItem>:
    orientation: 'horizontal'
    size_hint_y: None
    height: "72dp"
    padding: ["16dp", "8dp", "16dp", "8dp"]
    spacing: "12dp"
    md_bg_color: 0.14, 0.14, 0.16, 1
    radius: [12, 12, 12, 12]
    line_color: 1, 1, 1, 0.05
    line_width: 1
    
    MDBoxLayout:
        orientation: 'vertical'
        size_hint_x: 0.8
        pos_hint: {"center_y": 0.5}
        MDLabel:
            text: root.exam_info
            font_style: "Body1"
            bold: True
        MDLabel:
            text: root.score_details
            font_style: "Caption"
            theme_text_color: "Secondary"
            
    MDBoxLayout:
        size_hint_x: 0.2
        spacing: "8dp"
        pos_hint: {"center_y": 0.5}
        MDLabel:
            text: root.net_text
            font_style: "Subtitle1"
            bold: True
            theme_text_color: "Custom"
            text_color: app.theme_cls.primary_color
            halign: "right"
            pos_hint: {"center_y": 0.5}
        MDIconButton:
            icon: "trash-can-outline"
            theme_text_color: "Custom"
            text_color: 0.9, 0.3, 0.3, 1
            pos_hint: {"center_y": 0.5}
            on_release: root.delete_exam()

MDBoxLayout:
    orientation: 'vertical'
    
    MDBottomNavigation:
        id: bottom_nav
        panel_color: 0.1, 0.08, 0.12, 1
        text_color_active: app.theme_cls.primary_color
        
        MDBottomNavigationItem:
            name: 'tasks_nav'
            text: 'Yapilacaklar'
            icon: 'checkbox-marked-circle-outline'
            TaskScreen:
                id: tasks_screen
                db: app.db
                
        MDBottomNavigationItem:
            name: 'pomodoro_nav'
            text: 'Pomodoro'
            icon: 'timer'
            PomodoroScreen:
                id: pomodoro_screen
                db: app.db
                
        MDBottomNavigationItem:
            name: 'math_nav'
            text: 'Math Gym'
            icon: 'sword-cross'
            MathGymScreen:
                id: math_screen
                db: app.db
                
        MDBottomNavigationItem:
            name: 'analysis_nav'
            text: 'Analiz'
            icon: 'chart-bar'
            AnalysisScreen:
                id: analysis_screen
                db: app.db

<TaskScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        
        ScrollView:
            id: scroll_view
            MDBoxLayout:
                id: main_layout
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: "16dp"
                spacing: "16dp"
                
                # Left/Top Card: Gorevler
                MDCard:
                    id: tasks_card
                    orientation: 'vertical'
                    padding: "20dp"
                    spacing: "16dp"
                    radius: [16, 16, 16, 16]
                    size_hint_y: None
                    height: "400dp"
                    md_bg_color: 0.15, 0.13, 0.22, 1
                    elevation: 3
                    shadow_color: 0, 0, 0, 0.6
                    line_color: 1, 1, 1, 0.05
                    line_width: 1
                    
                    MDBoxLayout:
                        size_hint_y: None
                        height: "40dp"
                        MDLabel:
                            text: "Bugunun Yapilacaklari"
                            font_style: "H6"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                        
                        MDBoxLayout:
                            size_hint_x: None
                            width: "120dp"
                            spacing: "6dp"
                            MDIcon:
                                id: streak_icon
                                icon: "fire"
                                theme_text_color: "Custom"
                                text_color: 0.5, 0.5, 0.5, 1
                                font_size: "24sp"
                                pos_hint: {"center_y": 0.5}
                            MDLabel:
                                id: streak_label
                                text: "Streak: 0"
                                font_style: "Subtitle2"
                                bold: True
                                theme_text_color: "Custom"
                                text_color: 1, 1, 1, 1
                                pos_hint: {"center_y": 0.5}

                    MDProgressBar:
                        id: task_progress
                        value: 0
                        max: 100
                        size_hint_y: None
                        height: "6dp"
                        
                    ScrollView:
                        MDList:
                            id: task_list
                            spacing: "8dp"
                            
                    MDBoxLayout:
                        size_hint_y: None
                        height: "56dp"
                        spacing: "10dp"
                        MDTextField:
                            id: new_task_input
                            hint_text: "Yeni gorev yazin..."
                            mode: "rectangle"
                            size_hint_y: None
                            height: "48dp"
                            pos_hint: {"center_y": 0.5}
                        MDIconButton:
                            icon: "plus"
                            theme_text_color: "Custom"
                            text_color: app.theme_cls.primary_color
                            pos_hint: {"center_y": 0.5}
                            on_release: root.add_custom_task()
                
                # Right/Bottom Card: Gunluk Log Girisi
                MDCard:
                    id: log_card
                    orientation: 'vertical'
                    padding: "20dp"
                    spacing: "12dp"
                    radius: [16, 16, 16, 16]
                    size_hint_y: None
                    height: "580dp"
                    md_bg_color: 0.12, 0.12, 0.14, 1
                    elevation: 3
                    shadow_color: 0, 0, 0, 0.6
                    line_color: 1, 1, 1, 0.05
                    line_width: 1
                    
                    MDLabel:
                        text: "Gunluk Istatistik Kaydi"
                        font_style: "H6"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1
                        size_hint_y: None
                        height: "28dp"
                        
                    MDTextField:
                        id: math_q_input
                        hint_text: "Antrenmanlarla Matematik Cozulen Soru"
                        mode: "rectangle"
                        input_filter: "int"
                        size_hint_y: None
                        height: "40dp"
                        
                    MDBoxLayout:
                        orientation: 'vertical'
                        size_hint_y: None
                        height: "56dp"
                        spacing: "2dp"
                        MDTextField:
                            id: math_progress_input
                            hint_text: "Antrenmanlarla Matematik Ilerlemesi (Hedef: 30)"
                            mode: "rectangle"
                            input_filter: "int"
                            size_hint_y: None
                            height: "40dp"
                            on_text: root.update_math_progress_bar(self.text)
                        MDProgressBar:
                            id: math_progress_bar
                            value: 0
                            max: 100
                            size_hint_y: None
                            height: "4dp"
                            
                    MDBoxLayout:
                        orientation: 'vertical'
                        size_hint_y: None
                        height: "56dp"
                        spacing: "2dp"
                        MDTextField:
                            id: paragraph_progress_input
                            hint_text: "Gunluk Paragraf Rutini (Hedef: 20 Soru)"
                            mode: "rectangle"
                            input_filter: "int"
                            size_hint_y: None
                            height: "40dp"
                            on_text: root.update_paragraph_progress_bar(self.text)
                        MDProgressBar:
                            id: paragraph_progress_bar
                            value: 0
                            max: 100
                            size_hint_y: None
                            height: "4dp"

                    MDTextField:
                        id: mock_count_input
                        hint_text: "Bugun Cozulen Deneme Sayisi"
                        mode: "rectangle"
                        input_filter: "int"
                        size_hint_y: None
                        height: "40dp"
                        
                    MDTextField:
                        id: notes_input
                        hint_text: "Gunluk Notlar ve Calisma Detaylari"
                        mode: "rectangle"
                        multiline: True
                        size_hint_y: 1.0
                        
                    MDFillRoundFlatButton:
                        text: "LOGU VERITABANINA KAYDET"
                        size_hint_x: 1.0
                        on_release: root.save_daily_log()

<PomodoroScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        
        ScrollView:
            id: scroll_view
            MDBoxLayout:
                id: main_layout
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: "16dp"
                spacing: "16dp"
                
                MDBoxLayout:
                    id: left_layout
                    orientation: 'vertical'
                    spacing: "16dp"
                    size_hint_y: None
                    height: self.minimum_height
                    
                    # Left/Top Card: Pomodoro Sayaci
                    MDCard:
                        id: timer_card
                        orientation: 'vertical'
                        padding: "24dp"
                        spacing: "16dp"
                        radius: [16, 16, 16, 16]
                        size_hint_y: None
                        height: "400dp"
                        md_bg_color: 0.12, 0.14, 0.16, 1
                        elevation: 3
                        shadow_color: 0, 0, 0, 0.6
                        line_color: 1, 1, 1, 0.05
                        line_width: 1
                        
                        MDLabel:
                            text: "Odaklan & Pomodoro"
                            font_style: "H6"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            halign: "center"
                            size_hint_y: None
                            height: "32dp"
                            
                        MDBoxLayout:
                            orientation: 'vertical'
                            size_hint_y: 1.0
                            spacing: "8dp"
                            valign: "middle"
                            
                            MDLabel:
                                id: timer_label
                                text: "25:00"
                                font_style: "H3"
                                bold: True
                                theme_text_color: "Custom"
                                text_color: app.theme_cls.primary_color
                                halign: "center"
                                valign: "middle"
                                
                            MDLabel:
                                id: timer_status_label
                                text: "HAZIR"
                                font_style: "Subtitle1"
                                theme_text_color: "Secondary"
                                halign: "center"
                                
                        MDProgressBar:
                            id: timer_progress
                            value: 100
                            max: 100
                            size_hint_y: None
                            height: "6dp"
                            
                        MDBoxLayout:
                            size_hint_y: None
                            height: "56dp"
                            spacing: "12dp"
                            pos_hint: {"center_x": 0.5}
                            
                            MDFillRoundFlatButton:
                                id: start_btn
                                text: "BASLAT"
                                size_hint_x: 0.33
                                on_release: root.start_timer()
                                
                            MDFillRoundFlatButton:
                                id: pause_btn
                                text: "DURAKLAT"
                                size_hint_x: 0.33
                                disabled: True
                                on_release: root.pause_timer()
                                
                            MDRoundFlatButton:
                                text: "SIFIRLA"
                                size_hint_x: 0.33
                                on_release: root.reset_timer()
                                
                    # Right/Bottom Card: Calisma Kaydi
                    MDCard:
                        id: log_card
                        orientation: 'vertical'
                        padding: "20dp"
                        spacing: "12dp"
                        radius: [16, 16, 16, 16]
                        size_hint_y: None
                        height: "400dp"
                        md_bg_color: 0.14, 0.12, 0.16, 1
                        elevation: 3
                        shadow_color: 0, 0, 0, 0.6
                        line_color: 1, 1, 1, 0.05
                        line_width: 1
                        
                        MDLabel:
                            text: "Calisma Seansini Gunluge Ekle"
                            font_style: "H6"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            size_hint_y: None
                            height: "32dp"
                            
                        MDRoundFlatButton:
                            id: lesson_btn
                            text: "Ders Sec: Matematik"
                            size_hint_x: 1.0
                            on_release: root.open_lesson_menu(self)
                            
                        MDTextField:
                            id: source_input
                            hint_text: "Kaynak Kitap / Konu Basligi"
                            mode: "rectangle"
                            size_hint_y: None
                            height: "48dp"
                            
                        MDTextField:
                            id: questions_input
                            hint_text: "Bu Seans Cozulen Soru Sayisi"
                            mode: "rectangle"
                            input_filter: "int"
                            size_hint_y: None
                            height: "48dp"
                            
                        MDFillRoundFlatButton:
                            text: "SEANSI BITIR VE KAYDET"
                            size_hint_x: 1.0
                            on_release: root.save_study_session()
                
                CanvasCard:
                    id: canvas_card
                    show_upload: False

<MathGymScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        
        ScrollView:
            id: scroll_view
            MDBoxLayout:
                id: main_layout
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: "16dp"
                spacing: "16dp"
                
                MDBoxLayout:
                    id: left_layout
                    orientation: 'vertical'
                    spacing: "16dp"
                    size_hint_y: None
                    height: self.minimum_height
                    
                    # Left/Top Card: Soru Arenasi
                    MDCard:
                        id: arena_card
                        orientation: 'vertical'
                        padding: "24dp"
                        spacing: "16dp"
                        radius: [16, 16, 16, 16]
                        size_hint_y: None
                        height: "400dp"
                        md_bg_color: 0.11, 0.15, 0.13, 1
                        elevation: 3
                        shadow_color: 0, 0, 0, 0.6
                        line_color: 1, 1, 1, 0.05
                        line_width: 1
                        
                        MDLabel:
                            text: "Choppa Math Gym"
                            font_style: "H6"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            halign: "center"
                            size_hint_y: None
                            height: "32dp"
                            
                        MDBoxLayout:
                            orientation: 'vertical'
                            size_hint_y: 1.0
                            valign: "middle"
                            
                            MDLabel:
                                id: question_label
                                text: "Baslamak icin 'YENI SORU' butonuna basin"
                                font_style: "H4"
                                bold: True
                                halign: "center"
                                valign: "middle"
                                theme_text_color: "Custom"
                                text_color: 1, 1, 1, 1
                                
                        MDTextField:
                            id: answer_input
                            hint_text: "Cevabiniz"
                            mode: "rectangle"
                            input_filter: "int"
                            size_hint_y: None
                            height: "48dp"
                            on_text_validate: root.check_answer()
                            
                        MDBoxLayout:
                            size_hint_y: None
                            height: "56dp"
                            spacing: "12dp"
                            
                            MDFillRoundFlatButton:
                                id: submit_btn
                                text: "CEVAPLA"
                                size_hint_x: 0.5
                                on_release: root.check_answer()
                                
                            MDRoundFlatButton:
                                text: "YENI SORU"
                                size_hint_x: 0.5
                                on_release: root.new_question()
                                
                        MDBoxLayout:
                            size_hint_y: None
                            height: "32dp"
                            spacing: "10dp"
                            MDCheckbox:
                                id: auto_next
                                active: True
                                size_hint: None, None
                                size: "24dp", "24dp"
                            MDLabel:
                                text: "Otomatik Yeni Soru (1.5 sn)"
                                font_style: "Caption"
                                theme_text_color: "Secondary"
                                valign: "middle"
                                
                    # Right/Bottom Card: Skor ve Gecmis
                    MDCard:
                        id: stats_card
                        orientation: 'vertical'
                        padding: "20dp"
                        spacing: "12dp"
                        radius: [16, 16, 16, 16]
                        size_hint_y: None
                        height: "400dp"
                        md_bg_color: 0.14, 0.12, 0.16, 1
                        elevation: 3
                        shadow_color: 0, 0, 0, 0.6
                        line_color: 1, 1, 1, 0.05
                        line_width: 1
                        
                        MDLabel:
                            text: "Gym Istatistikleri ve Gecmis"
                            font_style: "H6"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            size_hint_y: None
                            height: "32dp"
                            
                        MDGridLayout:
                            cols: 2
                            size_hint_y: None
                            height: "64dp"
                            spacing: "10dp"
                            
                            MDLabel:
                                id: correct_count_label
                                text: "Dogru: 0"
                                font_style: "Subtitle1"
                                bold: True
                                theme_text_color: "Custom"
                                text_color: 0.2, 0.8, 0.2, 1
                                
                            MDLabel:
                                id: wrong_count_label
                                text: "Yanlis: 0"
                                font_style: "Subtitle1"
                                bold: True
                                theme_text_color: "Custom"
                                text_color: 0.9, 0.3, 0.3, 1
                                
                        MDLabel:
                            text: "Son Cozulen Sorular:"
                            font_style: "Subtitle2"
                            bold: True
                            theme_text_color: "Secondary"
                            size_hint_y: None
                            height: "24dp"
                            
                        ScrollView:
                            MDList:
                                id: history_list
                                spacing: "8dp"
                
                CanvasCard:
                    id: canvas_card
                    show_upload: True

<AnalysisScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        
        ScrollView:
            id: scroll_view
            MDBoxLayout:
                id: main_layout
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: "16dp"
                spacing: "16dp"
                
                # Left/Top Card: Deneme Girisi
                MDCard:
                    id: entry_card
                    orientation: 'vertical'
                    padding: "24dp"
                    spacing: "16dp"
                    radius: [16, 16, 16, 16]
                    size_hint_y: None
                    height: "450dp"
                    md_bg_color: 0.12, 0.12, 0.15, 1
                    elevation: 3
                    shadow_color: 0, 0, 0, 0.6
                    line_color: 1, 1, 1, 0.05
                    line_width: 1
                    
                    MDBoxLayout:
                        size_hint_y: None
                        height: "40dp"
                        spacing: "10dp"
                        MDLabel:
                            text: "Deneme Sonucu Gir"
                            font_style: "H6"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                        
                        # Exam Type Selector
                        MDRoundFlatButton:
                            id: exam_type_btn
                            text: "Sinav: TYT"
                            on_release: root.toggle_exam_type()
                            
                    MDGridLayout:
                        cols: 3
                        spacing: "8dp"
                        size_hint_y: 1.0
                        
                        # Table Headers
                        MDLabel:
                            text: "Ders"
                            bold: True
                            font_style: "Caption"
                        MDLabel:
                            text: "Dogru"
                            bold: True
                            font_style: "Caption"
                        MDLabel:
                            text: "Yanlis"
                            bold: True
                            font_style: "Caption"
                            
                        # TR / Edeb
                        MDLabel:
                            id: tr_label
                            text: "Turkce (40S):"
                            font_style: "Body2"
                        MDTextField:
                            id: tr_c
                            text: "0"
                            input_filter: "int"
                            mode: "rectangle"
                            size_hint_y: None
                            height: "36dp"
                        MDTextField:
                            id: tr_w
                            text: "0"
                            input_filter: "int"
                            mode: "rectangle"
                            size_hint_y: None
                            height: "36dp"
                            
                        # Soc
                        MDLabel:
                            id: soc_label
                            text: "Sosyal (20S):"
                            font_style: "Body2"
                        MDTextField:
                            id: soc_c
                            text: "0"
                            input_filter: "int"
                            mode: "rectangle"
                            size_hint_y: None
                            height: "36dp"
                        MDTextField:
                            id: soc_w
                            text: "0"
                            input_filter: "int"
                            mode: "rectangle"
                            size_hint_y: None
                            height: "36dp"
                            
                        # Math
                        MDLabel:
                            id: math_label
                            text: "Matematik (40S):"
                            font_style: "Body2"
                        MDTextField:
                            id: math_c
                            text: "0"
                            input_filter: "int"
                            mode: "rectangle"
                            size_hint_y: None
                            height: "36dp"
                        MDTextField:
                            id: math_w
                            text: "0"
                            input_filter: "int"
                            mode: "rectangle"
                            size_hint_y: None
                            height: "36dp"
                            
                        # Sci
                        MDLabel:
                            id: sci_label
                            text: "Fen (20S):"
                            font_style: "Body2"
                        MDTextField:
                            id: sci_c
                            text: "0"
                            input_filter: "int"
                            mode: "rectangle"
                            size_hint_y: None
                            height: "36dp"
                        MDTextField:
                            id: sci_w
                            text: "0"
                            input_filter: "int"
                            mode: "rectangle"
                            size_hint_y: None
                            height: "36dp"
                            
                    MDFillRoundFlatButton:
                        text: "NET HESAPLA VE VERIYE EKLE"
                        size_hint_x: 1.0
                        on_release: root.calculate_and_save()
                        
                # Right/Bottom Card: Istatistikler ve Deneme Gecmisi
                MDCard:
                    id: stats_card
                    orientation: 'vertical'
                    padding: "24dp"
                    spacing: "16dp"
                    radius: [16, 16, 16, 16]
                    size_hint_y: None
                    height: "450dp"
                    md_bg_color: 0.13, 0.11, 0.15, 1
                    elevation: 3
                    shadow_color: 0, 0, 0, 0.6
                    line_color: 1, 1, 1, 0.05
                    line_width: 1
                    
                    MDLabel:
                        text: "Net Analizi ve Gecmis"
                        font_style: "H6"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1
                        size_hint_y: None
                        height: "32dp"
                        
                    MDGridLayout:
                        cols: 2
                        size_hint_y: None
                        height: "64dp"
                        spacing: "10dp"
                        
                        MDLabel:
                            id: avg_tyt_label
                            text: "TYT Ort: 0.00"
                            font_style: "Subtitle1"
                            bold: True
                            theme_text_color: "Primary"
                            
                        MDLabel:
                            id: avg_ayt_label
                            text: "AYT Ort: 0.00"
                            font_style: "Subtitle1"
                            bold: True
                            theme_text_color: "Primary"
                            
                    MDLabel:
                        text: "Deneme Gecmisi:"
                        font_style: "Subtitle2"
                        bold: True
                        theme_text_color: "Secondary"
                        size_hint_y: None
                        height: "24dp"
                        
                    ScrollView:
                        MDList:
                            id: exam_list
                            spacing: "8dp"
                            
                # Backup & Restore Card
                MDCard:
                    id: backup_card
                    orientation: 'vertical'
                    padding: "24dp"
                    spacing: "16dp"
                    radius: [16, 16, 16, 16]
                    size_hint_y: None
                    height: "180dp"
                    md_bg_color: 0.12, 0.14, 0.15, 1
                    elevation: 3
                    shadow_color: 0, 0, 0, 0.6
                    line_color: 1, 1, 1, 0.05
                    line_width: 1
                    
                    MDLabel:
                        text: "Veri Yedekleme ve Kurtarma (JSON)"
                        font_style: "H6"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1
                        size_hint_y: None
                        height: "32dp"
                        
                    MDBoxLayout:
                        spacing: "12dp"
                        size_hint_y: None
                        height: "56dp"
                        
                        MDFillRoundFlatButton:
                            text: "VERILERI DISA AKTAR"
                            size_hint_x: 0.5
                            on_release: root.export_backup()
                            
                        MDFillRoundFlatButton:
                            text: "VERILERI ICE AKTAR"
                            size_hint_x: 0.5
                            on_release: root.import_backup()
"""

# ==========================================
# DRAWING CANVAS AND STYLUS WIDGETS
# ==========================================
class DrawingCanvas(Widget):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            with self.canvas:
                Color(0.2, 0.6, 1.0, 1.0) # Neon blue brush
                touch.ud['line'] = Line(points=(touch.x, touch.y), width=2.5)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if 'line' in touch.ud and self.collide_point(*touch.pos):
                touch.ud['line'].points += [touch.x, touch.y]
                return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def clear_canvas(self):
        self.canvas.clear()

class ImageChooserDialog(MDDialog):
    def __init__(self, select_callback, **kwargs):
        self.select_callback = select_callback
        start_path = '/sdcard' if os.path.exists('/sdcard') else os.path.expanduser('~')
        
        self.file_chooser = FileChooserIconView(
            path=start_path,
            filters=['*.png', '*.jpg', '*.jpeg'],
            size_hint_y=None,
            height="320dp"
        )
        
        super().__init__(
            title="Soru Resmi Secin",
            type="custom",
            content_cls=self.file_chooser,
            buttons=[
                MDRoundFlatButton(
                    text="IPTAL",
                    on_release=lambda x: self.dismiss()
                ),
                MDFillRoundFlatButton(
                    text="SEC",
                    on_release=self.confirm_selection
                )
            ],
            **kwargs
        )
        
    def confirm_selection(self, *args):
        selection = self.file_chooser.selection
        if selection:
            self.select_callback(selection[0])
            self.dismiss()
        else:
            MDSnackbar(text="Lutfen bir resim dosyasi secin!").open()

class CanvasCard(MDCard):
    bg_source = StringProperty("")
    show_upload = BooleanProperty(False)
    
    def clear_canvas(self):
        self.ids.drawing_canvas.clear_canvas()
        
    def open_image_chooser(self):
        dialog = ImageChooserDialog(select_callback=self.set_bg_image)
        dialog.open()
        
    def set_bg_image(self, filepath):
        self.bg_source = filepath
        MDSnackbar(text="Soru resmi yuklendi! Karalamaya baslayabilirsiniz.").open()

# ==========================================
# CUSTOM WIDGET CLASSES FOR LIST ITEMS
# ==========================================
class TaskItem(MDBoxLayout):
    task_id = NumericProperty()
    task_name = StringProperty()
    is_completed = BooleanProperty()
    screen_ref = ObjectProperty(None, allownone=True)
    
    def __init__(self, **kwargs):
        self.is_loading = True
        super().__init__(**kwargs)
        Clock.schedule_once(self.finish_loading, 0.1)
        
    def finish_loading(self, dt):
        self.is_loading = False

    def on_checkbox_active(self, checkbox, value):
        if not self.is_loading and self.screen_ref:
            self.screen_ref.toggle_task(self.task_id, value)

    def delete_task(self):
        if self.screen_ref:
            self.screen_ref.delete_task(self.task_id)

class HistoryItem(MDBoxLayout):
    question_text = StringProperty()
    user_answer = StringProperty()
    correct_answer = StringProperty()
    is_correct = BooleanProperty()

class ExamHistoryItem(MDBoxLayout):
    exam_id = NumericProperty()
    exam_info = StringProperty()
    score_details = StringProperty()
    net_text = StringProperty()
    screen_ref = ObjectProperty(None, allownone=True)

    def delete_exam(self):
        if self.screen_ref:
            self.screen_ref.delete_exam(self.exam_id)

# ==========================================
# SCREEN IMPLEMENTATIONS (OOP & RESPONSIVE)
# ==========================================
class ResponsiveScreen(MDScreen):
    db = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_size=self.on_window_size)
        Clock.schedule_once(self.initial_resize, 0)
        
    def initial_resize(self, dt):
        self.on_window_size(Window, Window.width, Window.height)

    def on_window_size(self, window, width, height):
        pass

class TaskScreen(ResponsiveScreen):
    def on_window_size(self, window, width, height):
        if width > height:
            self.ids.main_layout.orientation = 'horizontal'
            self.ids.tasks_card.size_hint_x = 0.5
            self.ids.tasks_card.size_hint_y = None
            self.ids.tasks_card.height = "580dp"
            self.ids.log_card.size_hint_x = 0.5
            self.ids.log_card.size_hint_y = None
            self.ids.log_card.height = "580dp"
        else:
            self.ids.main_layout.orientation = 'vertical'
            self.ids.tasks_card.size_hint_x = 1.0
            self.ids.tasks_card.size_hint_y = None
            self.ids.tasks_card.height = "400dp"
            self.ids.log_card.size_hint_x = 1.0
            self.ids.log_card.size_hint_y = None
            self.ids.log_card.height = "580dp"
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1.0), 0.05)
            
    def on_enter(self):
        self.load_data()
        
    def load_data(self):
        if not self.db:
            return
            
        today = datetime.date.today().isoformat()
        self.db.setup_default_tasks_for_today()
        
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            c.execute("SELECT id, task_name, is_completed FROM tasks WHERE date = ?", (today,))
            rows = c.fetchall()
            
            self.ids.task_list.clear_widgets()
            total_tasks = len(rows)
            completed_tasks = 0
            
            for r in rows:
                t_id, name, is_done = r
                item = TaskItem(task_id=t_id, task_name=name, is_completed=bool(is_done))
                item.screen_ref = self
                self.ids.task_list.add_widget(item)
                if is_done:
                    completed_tasks += 1
                    
            if total_tasks > 0:
                progress = int((completed_tasks / total_tasks) * 100)
            else:
                progress = 0
            self.ids.task_progress.value = progress
            
            streak_count, all_done = self.db.get_current_streak()
            self.ids.streak_label.text = f"Streak: {streak_count}"
            
            if all_done and streak_count > 0:
                self.ids.streak_icon.text_color = (1, 0.5, 0, 1)  # Fire Orange
            else:
                self.ids.streak_icon.text_color = (0.5, 0.5, 0.5, 1)  # Greyed out
                
            c.execute("SELECT math_questions, mock_exams, notes, math_progress, paragraph_progress FROM daily_logs WHERE date = ?", (today,))
            log_row = c.fetchone()
            conn.close()
            
            if log_row:
                self.ids.math_q_input.text = str(log_row[0])
                self.ids.mock_count_input.text = str(log_row[1])
                self.ids.notes_input.text = log_row[2] or ""
                self.ids.math_progress_input.text = str(log_row[3])
                self.ids.paragraph_progress_input.text = str(log_row[4])
                self.update_math_progress_bar(str(log_row[3]))
                self.update_paragraph_progress_bar(str(log_row[4]))
            else:
                self.ids.math_q_input.text = "0"
                self.ids.mock_count_input.text = "0"
                self.ids.notes_input.text = ""
                self.ids.math_progress_input.text = "0"
                self.ids.paragraph_progress_input.text = "0"
                self.update_math_progress_bar("0")
                self.update_paragraph_progress_bar("0")
        except Exception as e:
            MDSnackbar(text=f"Veri yukleme hatasi: {str(e)}").open()

    def update_math_progress_bar(self, text):
        try:
            val = int(text) if text else 0
        except ValueError:
            val = 0
        # Target is 30 pages
        self.ids.math_progress_bar.value = min(100, int((val / 30.0) * 100))

    def update_paragraph_progress_bar(self, text):
        try:
            val = int(text) if text else 0
        except ValueError:
            val = 0
        # Target is 20 questions
        self.ids.paragraph_progress_bar.value = min(100, int((val / 20.0) * 100))

    def add_custom_task(self):
        task_text = self.ids.new_task_input.text.strip()
        if not task_text:
            MDSnackbar(text="Lutfen bir gorev yazin!").open()
            return
            
        today = datetime.date.today().isoformat()
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO tasks (task_name, is_completed, date) VALUES (?, 0, ?)", (task_text, today))
            conn.commit()
            conn.close()
            
            self.ids.new_task_input.text = ""
            self.db.check_and_update_streak()
            self.load_data()
            MDSnackbar(text="Yeni gorev basariyla eklendi!").open()
        except Exception as e:
            MDSnackbar(text=f"Gorev ekleme hatasi: {str(e)}").open()

    def toggle_task(self, task_id, is_completed):
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            c.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (1 if is_completed else 0, task_id))
            conn.commit()
            conn.close()
            
            self.db.check_and_update_streak()
            self.load_data()
        except Exception as e:
            MDSnackbar(text=f"Durum guncelleme hatasi: {str(e)}").open()

    def delete_task(self, task_id):
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
            
            self.db.check_and_update_streak()
            self.load_data()
            MDSnackbar(text="Gorev silindi!").open()
        except Exception as e:
            MDSnackbar(text=f"Silme hatasi: {str(e)}").open()

    def save_daily_log(self):
        math_q = self.ids.math_q_input.text.strip()
        mock_c = self.ids.mock_count_input.text.strip()
        notes = self.ids.notes_input.text.strip()
        math_p = self.ids.math_progress_input.text.strip()
        para_p = self.ids.paragraph_progress_input.text.strip()
        
        try:
            math_q_val = int(math_q) if math_q else 0
            mock_c_val = int(mock_c) if mock_c else 0
            math_p_val = int(math_p) if math_p else 0
            para_p_val = int(para_p) if para_p else 0
        except ValueError:
            MDSnackbar(text="Tum alanlar tam sayi olmalidir!").open()
            return
            
        today = datetime.date.today().isoformat()
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            c.execute("SELECT id FROM daily_logs WHERE date = ?", (today,))
            row = c.fetchone()
            if row:
                c.execute("UPDATE daily_logs SET math_questions = ?, mock_exams = ?, notes = ?, math_progress = ?, paragraph_progress = ? WHERE date = ?", 
                          (math_q_val, mock_c_val, notes, math_p_val, para_p_val, today))
            else:
                c.execute("INSERT INTO daily_logs (date, math_questions, mock_exams, notes, math_progress, paragraph_progress) VALUES (?, ?, ?, ?, ?, ?)", 
                          (today, math_q_val, mock_c_val, notes, math_p_val, para_p_val))
            conn.commit()
            conn.close()
            MDSnackbar(text="Gunluk log basariyla guncellendi!").open()
            self.load_data()
        except Exception as e:
            MDSnackbar(text=f"Log kaydetme hatasi: {str(e)}").open()

class PomodoroScreen(ResponsiveScreen):
    time_left = NumericProperty(1500)
    timer_state = StringProperty("idle")
    is_running = BooleanProperty(False)
    selected_lesson = StringProperty("Matematik")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.max_time = 1500
        self.menu = None
        Clock.schedule_interval(self.tick, 1.0)
        
    def on_window_size(self, window, width, height):
        if width > height:
            self.ids.main_layout.orientation = 'horizontal'
            self.ids.left_layout.size_hint_x = 0.4
            self.ids.left_layout.size_hint_y = None
            self.ids.left_layout.height = "820dp"
            
            self.ids.canvas_card.size_hint_x = 0.6
            self.ids.canvas_card.size_hint_y = None
            self.ids.canvas_card.height = "820dp"
            
            self.ids.timer_card.size_hint_y = None
            self.ids.timer_card.height = "400dp"
            self.ids.log_card.size_hint_y = None
            self.ids.log_card.height = "400dp"
        else:
            self.ids.main_layout.orientation = 'vertical'
            self.ids.left_layout.size_hint_x = 1.0
            self.ids.left_layout.size_hint_y = None
            self.ids.left_layout.height = "820dp"
            
            self.ids.canvas_card.size_hint_x = 1.0
            self.ids.canvas_card.size_hint_y = None
            self.ids.canvas_card.height = "400dp"
            
            self.ids.timer_card.size_hint_y = None
            self.ids.timer_card.height = "400dp"
            self.ids.log_card.size_hint_y = None
            self.ids.log_card.height = "400dp"
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1.0), 0.05)
            
    def start_timer(self):
        if self.timer_state == "idle":
            self.timer_state = "work"
            self.max_time = 1500
            self.time_left = 1500
            self.ids.timer_status_label.text = "CALISMA ZAMANI"
            
        self.is_running = True
        self.ids.start_btn.disabled = True
        self.ids.pause_btn.disabled = False
        
    def pause_timer(self):
        self.is_running = False
        self.ids.start_btn.disabled = False
        self.ids.pause_btn.disabled = True
        
    def reset_timer(self):
        self.is_running = False
        self.timer_state = "idle"
        self.max_time = 1500
        self.time_left = 1500
        self.ids.timer_label.text = "25:00"
        self.ids.timer_status_label.text = "HAZIR"
        self.ids.timer_progress.value = 100
        self.ids.start_btn.disabled = False
        self.ids.pause_btn.disabled = True
        
    def tick(self, dt):
        if not self.is_running:
            return
            
        self.time_left -= 1
        
        mins = self.time_left // 60
        secs = self.time_left % 60
        self.ids.timer_label.text = f"{mins:02d}:{secs:02d}"
        self.ids.timer_progress.value = (self.time_left / self.max_time) * 100
        
        if self.time_left <= 0:
            self.is_running = False
            self.ids.start_btn.disabled = False
            self.ids.pause_btn.disabled = True
            
            play_alert_sound()
            
            if self.timer_state == "work":
                self.timer_state = "break"
                self.max_time = 300
                self.time_left = 300
                self.ids.timer_label.text = "05:00"
                self.ids.timer_status_label.text = "MOLA ZAMANI"
                self.ids.timer_progress.value = 100
                
                send_local_notification(
                    "Pomodoro Seansi Tamamlandi!",
                    "25 dakikalik calisma bitti. 5 dakikalik mola zamani."
                )
                
                dialog = MDDialog(
                    title="Seans Tamamlandi!",
                    text="Harika! 25 dakikalik calisma bitti. 5 dakikalik mola zamani.\nCozdugunuz sorulari sagdaki formdan kaydedebilirsiniz.",
                    buttons=[
                        MDFillRoundFlatButton(
                            text="Tamam",
                            on_release=lambda x: dialog.dismiss()
                        )
                    ]
                )
                dialog.open()
                
            elif self.timer_state == "break":
                self.timer_state = "work"
                self.max_time = 1500
                self.time_left = 1500
                self.ids.timer_label.text = "25:00"
                self.ids.timer_status_label.text = "CALISMA ZAMANI"
                self.ids.timer_progress.value = 100
                
                send_local_notification(
                    "Mola Bitti!",
                    "Mola bitti! Yeni calisma seansina baslayabilirsiniz."
                )
                
                dialog = MDDialog(
                    title="Mola Bitti!",
                    text="Mola bitti! Yeni bir odaklanma seansina baslamaya hazir misin?",
                    buttons=[
                        MDFillRoundFlatButton(
                            text="Hadi Baslayalim",
                            on_release=lambda x: dialog.dismiss()
                        )
                    ]
                )
                dialog.open()

    def open_lesson_menu(self, button):
        lessons = ["Matematik", "Turkce", "Fizik", "Kimya", "Biyoloji", "Tarih", "Cografya", "Felsefe"]
        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": lesson,
                "on_release": lambda x=lesson: self.select_lesson(x),
            } for lesson in lessons
        ]
        self.menu = MDDropdownMenu(
            caller=button,
            items=menu_items,
            width_mult=4,
        )
        self.menu.open()
        
    def select_lesson(self, lesson_name):
        self.selected_lesson = lesson_name
        self.ids.lesson_btn.text = f"Ders: {lesson_name}"
        if self.menu:
            self.menu.dismiss()
            
    def save_study_session(self):
        source = self.ids.source_input.text.strip()
        q_text = self.ids.questions_input.text.strip()
        
        if not source:
            MDSnackbar(text="Luyen kaynak kitap veya konu giriniz!").open()
            return
            
        try:
            questions = int(q_text) if q_text else 0
        except ValueError:
            MDSnackbar(text="Lutfen soru sayisini sayi olarak giriniz!").open()
            return
            
        today = datetime.date.today().isoformat()
        
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            
            c.execute("SELECT math_questions, mock_exams, notes FROM daily_logs WHERE date = ?", (today,))
            row = c.fetchone()
            
            notes_addon = f"[{self.selected_lesson} - {source}: {questions} Soru]"
            
            if row:
                current_q = row[0]
                current_notes = row[2] or ""
                
                new_q = current_q + (questions if self.selected_lesson == "Matematik" else 0)
                new_notes = current_notes + "\n" + notes_addon if current_notes else notes_addon
                
                c.execute("UPDATE daily_logs SET math_questions = ?, notes = ? WHERE date = ?", (new_q, new_notes, today))
            else:
                new_q = questions if self.selected_lesson == "Matematik" else 0
                c.execute("INSERT INTO daily_logs (date, math_questions, mock_exams, notes) VALUES (?, ?, 0, ?)", 
                          (today, new_q, notes_addon))
                          
            conn.commit()
            conn.close()
            
            self.ids.source_input.text = ""
            self.ids.questions_input.text = ""
            
            MDSnackbar(text="Calisma seansi basariyla kaydedildi!").open()
            
            app = MDApp.get_running_app()
            if app:
                tasks_screen = app.root.ids.tasks_screen
                tasks_screen.load_data()
                
        except Exception as e:
            MDSnackbar(text=f"Kayit hatasi: {str(e)}").open()

class MathGymScreen(ResponsiveScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.correct_ans = ""
        self.session_correct = 0
        self.session_wrong = 0

    def on_window_size(self, window, width, height):
        if width > height:
            self.ids.main_layout.orientation = 'horizontal'
            self.ids.left_layout.size_hint_x = 0.4
            self.ids.left_layout.size_hint_y = None
            self.ids.left_layout.height = "820dp"
            
            self.ids.canvas_card.size_hint_x = 0.6
            self.ids.canvas_card.size_hint_y = None
            self.ids.canvas_card.height = "820dp"
            
            self.ids.arena_card.size_hint_y = None
            self.ids.arena_card.height = "400dp"
            self.ids.stats_card.size_hint_y = None
            self.ids.stats_card.height = "400dp"
        else:
            self.ids.main_layout.orientation = 'vertical'
            self.ids.left_layout.size_hint_x = 1.0
            self.ids.left_layout.size_hint_y = None
            self.ids.left_layout.height = "820dp"
            
            self.ids.canvas_card.size_hint_x = 1.0
            self.ids.canvas_card.size_hint_y = None
            self.ids.canvas_card.height = "400dp"
            
            self.ids.arena_card.size_hint_y = None
            self.ids.arena_card.height = "400dp"
            self.ids.stats_card.size_hint_y = None
            self.ids.stats_card.height = "400dp"
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1.0), 0.05)

    def on_enter(self):
        self.load_stats()
        if not self.ids.question_label.text or "Baslamak icin" in self.ids.question_label.text:
            self.new_question()

    def load_stats(self):
        if not self.db:
            return
            
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            
            c.execute("SELECT COUNT(*), SUM(is_correct) FROM questions")
            row = c.fetchone()
            total = row[0] if row else 0
            correct = row[1] if row and row[1] is not None else 0
            wrong = total - correct
            
            self.ids.correct_count_label.text = f"Toplam Dogru: {correct} (Bu Seans: {self.session_correct})"
            self.ids.wrong_count_label.text = f"Toplam Yanlis: {wrong} (Bu Seans: {self.session_wrong})"
            
            c.execute("SELECT question_text, user_answer, correct_answer, is_correct FROM questions ORDER BY id DESC LIMIT 5")
            rows = c.fetchall()
            conn.close()
            
            self.ids.history_list.clear_widgets()
            for r in rows:
                q_text, user_ans, corr_ans, is_corr = r
                item = HistoryItem(
                    question_text=q_text,
                    user_answer=user_ans,
                    correct_answer=corr_ans,
                    is_correct=bool(is_corr)
                )
                self.ids.history_list.add_widget(item)
        except Exception as e:
            print(f"Stats loading error: {e}")

    def new_question(self):
        ops = ['+', '-', '*', '/']
        op = random.choice(ops)
        
        if op == '+':
            a = random.randint(10, 99)
            b = random.randint(10, 99)
            self.ids.question_label.text = f"{a} + {b} = ?"
            self.correct_ans = str(a + b)
        elif op == '-':
            a = random.randint(20, 150)
            b = random.randint(10, a - 1)
            self.ids.question_label.text = f"{a} - {b} = ?"
            self.correct_ans = str(a - b)
        elif op == '*':
            a = random.randint(2, 15)
            b = random.randint(2, 15)
            self.ids.question_label.text = f"{a} x {b} = ?"
            self.correct_ans = str(a * b)
        else:  # '/'
            b = random.randint(2, 15)
            if random.choice([True, False]):
                q = random.randint(2, 15)
                a = b * q
                self.ids.question_label.text = f"{a} / {b} = ?"
                self.correct_ans = str(q)
            else:
                a = random.randint(20, 150)
                self.ids.question_label.text = f"{a} / {b} = ? (Bolum)"
                self.correct_ans = str(a // b)
                
        self.ids.answer_input.text = ""
        self.ids.answer_input.focus = True

    def check_answer(self):
        user_ans = self.ids.answer_input.text.strip()
        if not user_ans:
            MDSnackbar(text="Lutfen bir cevap girin!").open()
            return
            
        is_correct = (user_ans == self.correct_ans)
        
        if is_correct:
            self.session_correct += 1
            MDSnackbar(
                text="Harika! DOGRU CEVAP!", 
                bg_color=(0.2, 0.7, 0.2, 1)
            ).open()
        else:
            self.session_wrong += 1
            MDSnackbar(
                text=f"Yanlis! Dogru Cevap: {self.correct_ans}", 
                bg_color=(0.8, 0.2, 0.2, 1)
            ).open()
            
        today = datetime.date.today().isoformat()
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            c.execute(
                "INSERT INTO questions (date, question_text, correct_answer, user_answer, is_correct) VALUES (?, ?, ?, ?, ?)",
                (today, self.ids.question_label.text, self.correct_ans, user_ans, 1 if is_correct else 0)
            )
            
            c.execute("SELECT math_questions FROM daily_logs WHERE date = ?", (today,))
            row = c.fetchone()
            if row:
                c.execute("UPDATE daily_logs SET math_questions = ? WHERE date = ?", (row[0] + 1, today))
            else:
                c.execute("INSERT INTO daily_logs (date, math_questions, mock_exams, notes) VALUES (?, 1, 0, '')", (today,))
                
            conn.commit()
            conn.close()
            
            app = MDApp.get_running_app()
            if app:
                tasks_screen = app.root.ids.tasks_screen
                tasks_screen.load_data()
                
        except Exception as e:
            print(f"Db save error: {e}")
            
        self.load_stats()
        
        if self.ids.auto_next.active:
            Clock.schedule_once(lambda dt: self.new_question(), 1.5)

class AnalysisScreen(ResponsiveScreen):
    exam_type = StringProperty("TYT")
    
    def on_window_size(self, window, width, height):
        self.ids.main_layout.orientation = 'vertical'
        
        self.ids.entry_card.size_hint_x = 1.0
        self.ids.entry_card.size_hint_y = None
        self.ids.entry_card.height = "450dp"
        
        self.ids.stats_card.size_hint_x = 1.0
        self.ids.stats_card.size_hint_y = None
        self.ids.stats_card.height = "450dp"
        
        self.ids.backup_card.size_hint_x = 1.0
        self.ids.backup_card.size_hint_y = None
        self.ids.backup_card.height = "180dp"
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1.0), 0.05)
        
    def export_backup(self):
        success, message = self.db.export_to_json()
        if success:
            dialog = MDDialog(
                title="Yedekleme Basarili",
                text=f"Veritabani yedegi basariyla kaydedildi!\nYedek konumu:\n{message}",
                buttons=[
                    MDFillRoundFlatButton(
                        text="Tamam",
                        on_release=lambda x: dialog.dismiss()
                    )
                ]
            )
            dialog.open()
        else:
            MDSnackbar(text=f"Yedekleme hatasi: {message}").open()
            
    def import_backup(self):
        success, message = self.db.import_from_json()
        if success:
            dialog = MDDialog(
                title="Geri Yukleme Basarili",
                text="Veritabani yedegi basariyla yuklendi! Degisiklikleri gormek icin uygulama ekranlari yenilenecektir.",
                buttons=[
                    MDFillRoundFlatButton(
                        text="Tamam",
                        on_release=lambda x: [dialog.dismiss(), self.refresh_all_screens()]
                    )
                ]
            )
            dialog.open()
        else:
            MDSnackbar(text=f"Geri yukleme hatasi: {message}").open()
            
    def refresh_all_screens(self):
        self.load_data()
        app = MDApp.get_running_app()
        if app:
            app.root.ids.tasks_screen.load_data()
            app.root.ids.pomodoro_screen.reset_timer()
            app.root.ids.math_screen.load_stats()
            
    def on_enter(self):
        self.load_data()
        
    def toggle_exam_type(self):
        if self.exam_type == "TYT":
            self.exam_type = "AYT"
            self.ids.exam_type_btn.text = "Sinav: AYT"
            self.ids.tr_label.text = "Edeb-Sos1 (40S):"
            self.ids.soc_label.text = "Sosyal-2 (40S):"
            self.ids.math_label.text = "Matematik (40S):"
            self.ids.sci_label.text = "Fen (40S):"
        else:
            self.exam_type = "TYT"
            self.ids.exam_type_btn.text = "Sinav: TYT"
            self.ids.tr_label.text = "Turkce (40S):"
            self.ids.soc_label.text = "Sosyal (20S):"
            self.ids.math_label.text = "Matematik (40S):"
            self.ids.sci_label.text = "Fen (20S):"
            
    def load_data(self):
        if not self.db:
            return
            
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            
            c.execute("SELECT AVG(net) FROM mock_exams WHERE exam_type = 'TYT'")
            tyt_avg_row = c.fetchone()
            tyt_avg = tyt_avg_row[0] if tyt_avg_row and tyt_avg_row[0] is not None else 0.0
            
            c.execute("SELECT AVG(net) FROM mock_exams WHERE exam_type = 'AYT'")
            ayt_avg_row = c.fetchone()
            ayt_avg = ayt_avg_row[0] if ayt_avg_row and ayt_avg_row[0] is not None else 0.0
            
            self.ids.avg_tyt_label.text = f"TYT Ort: {tyt_avg:.2f}"
            self.ids.avg_ayt_label.text = f"AYT Ort: {ayt_avg:.2f}"
            
            c.execute("""
                SELECT id, date, exam_type, tr_correct, tr_wrong, soc_correct, soc_wrong, 
                       math_correct, math_wrong, sci_correct, sci_wrong, net 
                FROM mock_exams 
                ORDER BY id DESC
            """)
            rows = c.fetchall()
            conn.close()
            
            self.ids.exam_list.clear_widgets()
            for r in rows:
                e_id, dt, e_type, tc, tw, soc_c, soc_w, mc, mw, sc, sw, net = r
                
                score_str = f"T/Edb: {tc}D {tw}Y | Sos: {soc_c}D {soc_w}Y | Mat: {mc}D {mw}Y | Fen: {sc}D {sw}Y"
                
                item = ExamHistoryItem(
                    exam_id=e_id,
                    exam_info=f"{e_type} Denemesi - {dt}",
                    score_details=score_str,
                    net_text=f"{net:.2f} Net",
                )
                item.screen_ref = self
                self.ids.exam_list.add_widget(item)
                
        except Exception as e:
            print(f"Mock history load error: {e}")
            
    def calculate_and_save(self):
        try:
            tc = int(self.ids.tr_c.text.strip())
            tw = int(self.ids.tr_w.text.strip())
            soc_c = int(self.ids.soc_c.text.strip())
            soc_w = int(self.ids.soc_w.text.strip())
            mc = int(self.ids.math_c.text.strip())
            mw = int(self.ids.math_w.text.strip())
            sc = int(self.ids.sci_c.text.strip())
            sw = int(self.ids.sci_w.text.strip())
        except ValueError:
            MDSnackbar(text="Lutfen tum alanlara gecerli tam sayilar giriniz!").open()
            return
            
        tr_limit = 40
        soc_limit = 20 if self.exam_type == "TYT" else 40
        math_limit = 40
        sci_limit = 20 if self.exam_type == "TYT" else 40
        
        if tc < 0 or tw < 0 or soc_c < 0 or soc_w < 0 or mc < 0 or mw < 0 or sc < 0 or sw < 0:
            MDSnackbar(text="Cevap sayilari sifirdan kucuk olamaz!").open()
            return
            
        if (tc + tw > tr_limit) or (soc_c + soc_w > soc_limit) or (mc + mw > math_limit) or (sc + sw > sci_limit):
            MDSnackbar(text="Girdiginiz soru sayilari bolum limitlerini asmaktadir!").open()
            return
            
        tr_net = tc - (tw * 0.25)
        soc_net = soc_c - (soc_w * 0.25)
        math_net = mc - (mw * 0.25)
        sci_net = sc - (sw * 0.25)
        total_net = tr_net + soc_net + math_net + sci_net
        
        today = datetime.date.today().isoformat()
        
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO mock_exams 
                (date, exam_type, tr_correct, tr_wrong, soc_correct, soc_wrong, math_correct, math_wrong, sci_correct, sci_wrong, net) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (today, self.exam_type, tc, tw, soc_c, soc_w, mc, mw, sc, sw, total_net)
            )
            
            c.execute("SELECT mock_exams FROM daily_logs WHERE date = ?", (today,))
            row = c.fetchone()
            if row:
                c.execute("UPDATE daily_logs SET mock_exams = ? WHERE date = ?", (row[0] + 1, today))
            else:
                c.execute("INSERT INTO daily_logs (date, math_questions, mock_exams, notes) VALUES (?, 0, 1, '')", (today,))
                
            conn.commit()
            conn.close()
            
            self.ids.tr_c.text = "0"
            self.ids.tr_w.text = "0"
            self.ids.soc_c.text = "0"
            self.ids.soc_w.text = "0"
            self.ids.math_c.text = "0"
            self.ids.math_w.text = "0"
            self.ids.sci_c.text = "0"
            self.ids.sci_w.text = "0"
            
            MDSnackbar(text=f"Deneme basariyla kaydedildi! Net: {total_net:.2f}").open()
            self.load_data()
            
            app = MDApp.get_running_app()
            if app:
                tasks_screen = app.root.ids.tasks_screen
                tasks_screen.load_data()
                
        except Exception as e:
            MDSnackbar(text=f"Kayit hatasi: {str(e)}").open()
            
    def delete_exam(self, exam_id):
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            
            c.execute("SELECT date FROM mock_exams WHERE id = ?", (exam_id,))
            exam_row = c.fetchone()
            if exam_row:
                exam_date = exam_row[0]
                c.execute("DELETE FROM mock_exams WHERE id = ?", (exam_id,))
                
                c.execute("SELECT mock_exams FROM daily_logs WHERE date = ?", (exam_date,))
                row = c.fetchone()
                if row and row[0] > 0:
                    c.execute("UPDATE daily_logs SET mock_exams = ? WHERE date = ?", (row[0] - 1, exam_date))
                    
            conn.commit()
            conn.close()
            
            MDSnackbar(text="Deneme silindi!").open()
            self.load_data()
            
            app = MDApp.get_running_app()
            if app:
                tasks_screen = app.root.ids.tasks_screen
                tasks_screen.load_data()
                
        except Exception as e:
            MDSnackbar(text=f"Silme hatasi: {str(e)}").open()

# ==========================================
# APPLICATION CLASS
# ==========================================
class ChoppaYKSApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        
    def build(self):
        generate_beep_sound()
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.accent_palette = "Teal"
        return Builder.load_string(KV_STR)

if __name__ == '__main__':
    ChoppaYKSApp().run()
