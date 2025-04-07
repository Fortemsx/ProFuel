import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import sqlite3
import os
import sys
import matplotlib # type: ignore
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg # type: ignore
import matplotlib.pyplot as plt # type: ignore
from PIL import Image, ImageTk # type: ignore

# Opsiyonel modüller için try-except blokları
try:
    from openpyxl import Workbook # type: ignore
    from openpyxl.styles import Font # type: ignore
    HAS_EXCEL = True
except ImportError:
    HAS_EXCEL = False
    messagebox.showwarning("Uyarı", "Excel raporlama özelliği devre dışı (openpyxl kurulu değil)")

try:
    import sv_ttk # type: ignore
    HAS_SV_TTK = True
except ImportError:
    HAS_SV_TTK = False

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

class YakıtTakipUygulaması:
    def __init__(self, root):
        self.root = root
        self.setup_main_window()
        self.setup_database()
        self.create_tables()  # Tabloları önce oluştur
        self.initialize_database()  # Sonra verileri başlat
        self.setup_ui()
        self.load_initial_data()
        
        # Tema ayarı
        self.apply_theme("dark")

    def apply_theme(self, theme_name):
        """Tema uygular (sv_ttk yoksa standart tema kullanır)"""
        if HAS_SV_TTK:
            try:
                if theme_name == "light":
                    sv_ttk.use_light_theme()
                else:
                    sv_ttk.use_dark_theme()
            except Exception as e:
                print(f"Tema uygulanırken hata: {e}")
        else:
            # Standart Tkinter teması
            self.root.tk_setPalette(background='#f0f0f0' if theme_name == "light" else '#333333')

    def setup_main_window(self):
        """Ana pencere ayarlarını yapar"""
        self.root.title("Temelli Yakıt Takip Sistemi v1.0")
        self.root.geometry("1200x700")
        self.root.minsize(1000, 600)
        
        # DPI farkındalığı (Windows için)
        if sys.platform == 'win32':
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
            except:
                pass

    def setup_database(self):
        """Veritabanı bağlantısını kurar"""
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yakit_takip.db")
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası", f"Veritabanına bağlanılamadı: {str(e)}")
            sys.exit(1)

    def create_tables(self):
        """Gerekli tabloları oluşturur"""
        tables = [
            """CREATE TABLE IF NOT EXISTS araclar (
                arac_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plaka TEXT UNIQUE NOT NULL,
                model TEXT NOT NULL,
                mevcut_km INTEGER DEFAULT 0,
                model_yili INTEGER,
                muayene_tarihi TEXT,
                bakim_tarihi TEXT,
                arac_surucusu TEXT,
                eklenme_tarihi TEXT DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS yakit_kayitlari (
                kayit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                arac_id INTEGER NOT NULL,
                km INTEGER NOT NULL,
                yakit_miktari REAL NOT NULL,
                notlar TEXT,
                tarih TEXT NOT NULL,
                eklenme_tarihi TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (arac_id) REFERENCES araclar(arac_id)
            )""",
            """CREATE TABLE IF NOT EXISTS depo_dolumlari (
                dolum_id INTEGER PRIMARY KEY AUTOINCREMENT,
                miktar REAL NOT NULL,
                birim_fiyat REAL,
                toplam_tutar REAL,
                notlar TEXT,
                tarih TEXT NOT NULL,
                eklenme_tarihi TEXT DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS depo (
                depo_id INTEGER PRIMARY KEY DEFAULT 1,
                mevcut_yakit REAL DEFAULT 0,
                son_guncelleme TEXT DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS bakim_tamirat (
                kayit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                arac_id INTEGER NOT NULL,
                tarih TEXT NOT NULL,
                saat TEXT,
                tespit_edilen_ariza TEXT,
                yapilan_islem TEXT,
                parca_ucreti REAL DEFAULT 0,
                iscilik_ucreti REAL DEFAULT 0,
                toplam_tutar REAL DEFAULT 0,
                notlar TEXT,
                eklenme_tarihi TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (arac_id) REFERENCES araclar(arac_id)
            )"""
        ]

        for table_query in tables:
            try:
                self.cursor.execute(table_query)
                self.conn.commit()
            except sqlite3.Error as e:
                self.show_error(f"Tablo oluşturulamadı: {str(e)}")

    def initialize_database(self):
        """Temel verileri ekler"""
        try:
            self.cursor.execute("INSERT OR IGNORE INTO depo (depo_id, mevcut_yakit) VALUES (1, 0)")
            self.conn.commit()
        except sqlite3.Error as e:
            self.show_error(f"Veritabanı başlatma hatası: {str(e)}")
            self.conn.rollback()

    def setup_ui(self):
        """Arayüzü oluşturur"""
        self.create_main_frame()
        self.create_menu()
        self.create_notebook()
        self.create_status_bar()
        self.play_sound("SystemStart")

    def create_main_frame(self):
        """Ana frame'i oluşturur"""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Başlık çubuğu
        header = ttk.Frame(self.main_frame)
        header.pack(fill=tk.X, pady=5)
        
        self.title_label = ttk.Label(
            header, 
            text="TEMELLİ YAKIT TAKİP SİSTEMİ", 
            font=('Helvetica', 14, 'bold')
        )
        self.title_label.pack(side=tk.LEFT)

    def create_menu(self):
        """Menü çubuğunu oluşturur"""
        menubar = tk.Menu(self.root)
        
        # Dosya menüsü
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Yedek Al", command=self.backup_database)
        if HAS_EXCEL:
            file_menu.add_command(label="Excel Raporu", command=self.generate_excel_report)
        file_menu.add_separator()
        file_menu.add_command(label="Çıkış", command=self.on_closing)
        menubar.add_cascade(label="Dosya", menu=file_menu)
        
        # Araçlar menüsü
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Veri Analizi", command=self.show_data_analysis)
        if HAS_SV_TTK:
            tools_menu.add_command(label="Light Tema", command=lambda: self.apply_theme("light"))
            tools_menu.add_command(label="Dark Tema", command=lambda: self.apply_theme("dark"))
        menubar.add_cascade(label="Araçlar", menu=tools_menu)
        
        # Yardım menüsü
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Yardım", command=self.show_help)
        help_menu.add_command(label="Hakkında", command=self.show_about)
        menubar.add_cascade(label="Yardım", menu=help_menu)
        
        self.root.config(menu=menubar)

    def create_notebook(self):
        """Notebook (sekmeler) oluşturur"""
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Sekmeler
        self.arac_frame = ttk.Frame(self.notebook)
        self.yakit_frame = ttk.Frame(self.notebook)
        self.depo_frame = ttk.Frame(self.notebook)
        self.rapor_frame = ttk.Frame(self.notebook)
        self.arac_detay_frame = ttk.Frame(self.notebook)  # Yeni araç detay sekmesi
        self.bakim_tamirat_frame = ttk.Frame(self.notebook)  # Yeni bakım tamirat sekmesi
        
        self.notebook.add(self.arac_frame, text="Araç Yönetimi")
        self.notebook.add(self.yakit_frame, text="Yakıt İşlemleri")
        self.notebook.add(self.depo_frame, text="Depo Yönetimi")
        self.notebook.add(self.rapor_frame, text="Raporlar")
        self.notebook.add(self.arac_detay_frame, text="Araç Detayları")
        self.notebook.add(self.bakim_tamirat_frame, text="Bakım ve Tamirat")  # Yeni sekme eklendi
        
        self.setup_arac_tab()
        self.setup_yakit_tab()
        self.setup_depo_tab()
        self.setup_rapor_tab()
        self.setup_arac_detay_tab()
        self.setup_bakim_tamirat_tab()  # Yeni sekme kurulumu

    def setup_arac_tab(self):
        """Araç yönetimi sekmesini kurar"""
        # Araç ekleme frame
        frame = ttk.LabelFrame(self.arac_frame, text="Araç İşlemleri", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Plaka
        ttk.Label(frame, text="Plaka:").grid(row=0, column=0, sticky="w", pady=5)
        self.plaka_entry = ttk.Entry(frame)
        self.plaka_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Model
        ttk.Label(frame, text="Model:").grid(row=1, column=0, sticky="w", pady=5)
        self.model_entry = ttk.Entry(frame)
        self.model_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # KM
        ttk.Label(frame, text="Mevcut KM:").grid(row=2, column=0, sticky="w", pady=5)
        self.km_entry = ttk.Entry(frame)
        self.km_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # Model Yılı
        ttk.Label(frame, text="Model Yılı:").grid(row=0, column=2, sticky="w", pady=5)
        self.model_yili_entry = ttk.Entry(frame)
        self.model_yili_entry.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
        
        # Muayene Tarihi
        ttk.Label(frame, text="Muayene Tarihi:").grid(row=1, column=2, sticky="w", pady=5)
        self.muayene_tarihi_entry = ttk.Entry(frame)
        self.muayene_tarihi_entry.grid(row=1, column=3, padx=10, pady=5, sticky="ew")
        
        # Bakım Tarihi
        ttk.Label(frame, text="Bakım Tarihi:").grid(row=2, column=2, sticky="w", pady=5)
        self.bakim_tarihi_entry = ttk.Entry(frame)
        self.bakim_tarihi_entry.grid(row=2, column=3, padx=10, pady=5, sticky="ew")
        
        # Şoför
        ttk.Label(frame, text="Aracın Şoförü:").grid(row=3, column=0, sticky="w", pady=5)
        self.arac_surucusu_entry = ttk.Entry(frame)
        self.arac_surucusu_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        # Butonlar
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=4, pady=10)
        
        ttk.Button(btn_frame, text="Araç Ekle", command=self.arac_ekle).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Araç Sil", command=self.arac_sil).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Detayları Gör", command=self.arac_detay_goster).pack(side=tk.LEFT, padx=5)
        
        # Araç listesi
        tree_frame = ttk.Frame(self.arac_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("Plaka", "Model", "KM", "Model Yılı", "Şoför")
        self.arac_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        for col in columns:
            self.arac_tree.heading(col, text=col)
            self.arac_tree.column(col, width=100, anchor='center')
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.arac_tree.yview)
        self.arac_tree.configure(yscrollcommand=scrollbar.set)
        
        self.arac_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_yakit_tab(self):
        """Yakıt işlemleri sekmesini kurar"""
        # Yakıt ekleme frame
        frame = ttk.LabelFrame(self.yakit_frame, text="Yakıt İşlemleri", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Araç seçimi
        ttk.Label(frame, text="Araç:").grid(row=0, column=0, sticky="w", pady=5)
        self.yakit_arac_combobox = ttk.Combobox(frame, state="readonly")
        self.yakit_arac_combobox.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # KM
        ttk.Label(frame, text="KM:").grid(row=1, column=0, sticky="w", pady=5)
        self.yakit_km_entry = ttk.Entry(frame)
        self.yakit_km_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Yakıt miktarı
        ttk.Label(frame, text="Yakıt Miktarı (L):").grid(row=2, column=0, sticky="w", pady=5)
        self.yakit_miktar_entry = ttk.Entry(frame)
        self.yakit_miktar_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # Tarih
        ttk.Label(frame, text="Tarih:").grid(row=3, column=0, sticky="w", pady=5)
        self.yakit_tarih_entry = ttk.Entry(frame)
        self.yakit_tarih_entry.insert(0, datetime.now().strftime("%d-%m-%Y %H:%M"))
        self.yakit_tarih_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        # Notlar
        ttk.Label(frame, text="Notlar:").grid(row=4, column=0, sticky="w", pady=5)
        self.yakit_not_entry = ttk.Entry(frame)
        self.yakit_not_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        # Butonlar
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="Yakıt Ekle", command=self.yakit_ekle).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Kayıt Sil", command=self.yakit_kaydi_sil).pack(side=tk.LEFT, padx=5)
        
        # Yakıt kayıtları listesi
        tree_frame = ttk.Frame(self.yakit_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("Tarih", "Plaka", "KM", "Miktar", "Not")
        self.yakit_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        for col in columns:
            self.yakit_tree.heading(col, text=col)
            self.yakit_tree.column(col, width=100, anchor='center')
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.yakit_tree.yview)
        self.yakit_tree.configure(yscrollcommand=scrollbar.set)
        
        self.yakit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_depo_tab(self):
        """Depo yönetimi sekmesini kurar"""
        # Depo dolum frame
        frame = ttk.LabelFrame(self.depo_frame, text="Depo İşlemleri", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Miktar
        ttk.Label(frame, text="Miktar (L):").grid(row=0, column=0, sticky="w", pady=5)
        self.depo_miktar_entry = ttk.Entry(frame)
        self.depo_miktar_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Tarih
        ttk.Label(frame, text="Tarih:").grid(row=1, column=0, sticky="w", pady=5)
        self.depo_tarih_entry = ttk.Entry(frame)
        self.depo_tarih_entry.insert(0, datetime.now().strftime("%d-%m-%Y %H:%M"))
        self.depo_tarih_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Notlar
        ttk.Label(frame, text="Notlar:").grid(row=2, column=0, sticky="w", pady=5)
        self.depo_not_entry = ttk.Entry(frame)
        self.depo_not_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # Butonlar
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="Depo Doldur", command=self.depo_doldur).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Kayıt Sil", command=self.depo_dolum_sil).pack(side=tk.LEFT, padx=5)
        
        # Depo durumu
        self.depo_durum_label = ttk.Label(
            frame, 
            text="Depo Durumu: Yükleniyor...", 
            font=('Helvetica', 10, 'bold')
        )
        self.depo_durum_label.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Depo dolum kayıtları
        tree_frame = ttk.Frame(self.depo_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("Tarih", "Miktar", "Not")
        self.depo_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        for col in columns:
            self.depo_tree.heading(col, text=col)
            self.depo_tree.column(col, width=120, anchor='center')
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.depo_tree.yview)
        self.depo_tree.configure(yscrollcommand=scrollbar.set)
        
        self.depo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_rapor_tab(self):
        """Raporlar sekmesini kurar"""
        # Filtreleme frame
        filter_frame = ttk.Frame(self.rapor_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Araç filtresi
        ttk.Label(filter_frame, text="Araç:").pack(side=tk.LEFT)
        self.rapor_arac_combobox = ttk.Combobox(filter_frame, state="readonly")
        self.rapor_arac_combobox.pack(side=tk.LEFT, padx=5)
        
        # Ay filtresi
        ttk.Label(filter_frame, text="Ay:").pack(side=tk.LEFT)
        self.rapor_ay_combobox = ttk.Combobox(filter_frame)
        self.rapor_ay_combobox.pack(side=tk.LEFT, padx=5)
        
        # Filtrele butonu
        ttk.Button(filter_frame, text="Filtrele", command=self.filtrele).pack(side=tk.LEFT, padx=5)
        
        # Grafik butonları
        ttk.Button(filter_frame, text="Grafik Oluştur", command=self.show_data_analysis).pack(side=tk.RIGHT)
        
        # İstatistikler frame
        stats_frame = ttk.Frame(self.rapor_frame)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.ortalama_tuketim_label = ttk.Label(
            stats_frame, 
            text="Genel Ortalama (L/100km): -", 
            font=('Helvetica', 9)
        )
        self.ortalama_tuketim_label.pack(side=tk.LEFT, padx=10)
        
        self.aylik_ortalama_label = ttk.Label(
            stats_frame, 
            text="Aylık Ortalama (L/100km): -", 
            font=('Helvetica', 9)
        )
        self.aylik_ortalama_label.pack(side=tk.LEFT, padx=10)
        
        self.yillik_ortalama_label = ttk.Label(
            stats_frame, 
            text="Yıllık Ortalama (L/100km): -", 
            font=('Helvetica', 9)
        )
        self.yillik_ortalama_label.pack(side=tk.LEFT, padx=10)
        
        # Rapor tablosu
        tree_frame = ttk.Frame(self.rapor_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("Tarih", "Plaka", "KM", "Miktar", "Not")
        self.rapor_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        for col in columns:
            self.rapor_tree.heading(col, text=col)
            self.rapor_tree.column(col, width=100, anchor='center')
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.rapor_tree.yview)
        self.rapor_tree.configure(yscrollcommand=scrollbar.set)
        
        self.rapor_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_arac_detay_tab(self):
        """Araç detayları sekmesini kurar"""
        # Sol frame - Araç seçimi ve bilgileri
        left_frame = ttk.Frame(self.arac_detay_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        # Araç seçimi
        ttk.Label(left_frame, text="Araç Seçin:").pack(pady=5)
        self.arac_detay_combobox = ttk.Combobox(left_frame, state="readonly")
        self.arac_detay_combobox.pack(fill=tk.X, pady=5)
        ttk.Button(left_frame, text="Araç Bilgilerini Getir", command=self.arac_detay_getir).pack(pady=10)
        
        # Araç bilgileri
        info_frame = ttk.LabelFrame(left_frame, text="Araç Bilgileri", padding=10)
        info_frame.pack(fill=tk.X, pady=10)
        
        self.arac_detay_labels = {}
        fields = [
            ("Plaka", "plaka"),
            ("Model", "model"),
            ("KM", "mevcut_km"),
            ("Model Yılı", "model_yili"),
            ("Muayene Tarihi", "muayene_tarihi"),
            ("Bakım Tarihi", "bakim_tarihi"),
            ("Şoför", "arac_surucusu")
        ]
        
        for text, key in fields:
            frame = ttk.Frame(info_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{text}:", width=12).pack(side=tk.LEFT)
            self.arac_detay_labels[key] = ttk.Label(frame, text="-", font=('Helvetica', 9, 'bold'))
            self.arac_detay_labels[key].pack(side=tk.LEFT)
        
        # Uyarılar
        warning_frame = ttk.LabelFrame(left_frame, text="Uyarılar", padding=10)
        warning_frame.pack(fill=tk.X, pady=10)
        
        self.uyari_label = ttk.Label(
            warning_frame, 
            text="Araç seçiniz...", 
            font=('Helvetica', 9),
            wraplength=250
        )
        self.uyari_label.pack(fill=tk.X)
        
        # Sağ frame - Araç detayları güncelleme
        right_frame = ttk.Frame(self.arac_detay_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        update_frame = ttk.LabelFrame(right_frame, text="Araç Bilgilerini Güncelle", padding=10)
        update_frame.pack(fill=tk.X, pady=10)
        
        # Güncelleme formu
        self.update_entries = {}
        row = 0
        for text, key in fields[3:]:  # Model yılı ve sonrası
            ttk.Label(update_frame, text=text).grid(row=row, column=0, sticky="w", pady=5)
            self.update_entries[key] = ttk.Entry(update_frame)
            self.update_entries[key].grid(row=row, column=1, padx=10, pady=5, sticky="ew")
            row += 1
        
        # Güncelleme butonu
        ttk.Button(
            update_frame, 
            text="Bilgileri Güncelle", 
            command=self.arac_detay_guncelle
        ).grid(row=row, column=0, columnspan=2, pady=10)
        
        # Yakıt kayıtları
        fuel_frame = ttk.LabelFrame(right_frame, text="Son Yakıt Kayıtları", padding=10)
        fuel_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ("Tarih", "KM", "Miktar", "Not")
        self.arac_yakit_tree = ttk.Treeview(fuel_frame, columns=columns, show="headings")
        
        for col in columns:
            self.arac_yakit_tree.heading(col, text=col)
            self.arac_yakit_tree.column(col, width=100, anchor='center')
        
        scrollbar = ttk.Scrollbar(fuel_frame, orient="vertical", command=self.arac_yakit_tree.yview)
        self.arac_yakit_tree.configure(yscrollcommand=scrollbar.set)
        
        self.arac_yakit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_bakim_tamirat_tab(self):
        """Bakım ve tamirat sekmesini kurar"""
        # Sol frame - Araç seçimi ve bakım kayıtları
        left_frame = ttk.Frame(self.bakim_tamirat_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        # Araç seçimi
        ttk.Label(left_frame, text="Araç Seçin:").pack(pady=5)
        self.bakim_arac_combobox = ttk.Combobox(left_frame, state="readonly")
        self.bakim_arac_combobox.pack(fill=tk.X, pady=5)
        ttk.Button(left_frame, text="Bakım Kayıtlarını Getir", command=self.bakim_kayitlarini_getir).pack(pady=10)
        
        # Bakım kayıtları listesi
        tree_frame = ttk.LabelFrame(left_frame, text="Bakım Kayıtları", padding=10)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ("Tarih", "Arıza", "İşlem", "Toplam Tutar")
        self.bakim_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        for col in columns:
            self.bakim_tree.heading(col, text=col)
            self.bakim_tree.column(col, width=100, anchor='center')
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.bakim_tree.yview)
        self.bakim_tree.configure(yscrollcommand=scrollbar.set)
        
        self.bakim_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Butonlar
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="Kayıt Sil", command=self.bakim_kaydi_sil).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Kayıt Düzenle", command=self.bakim_kaydi_duzenle).pack(side=tk.LEFT, padx=5)
        
        # Sağ frame - Yeni bakım kaydı ekleme
        right_frame = ttk.Frame(self.bakim_tamirat_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        form_frame = ttk.LabelFrame(right_frame, text="Yeni Bakım/Tamirat Kaydı", padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Form alanları
        ttk.Label(form_frame, text="Tarih:").grid(row=0, column=0, sticky="w", pady=5)
        self.bakim_tarih_entry = ttk.Entry(form_frame)
        self.bakim_tarih_entry.insert(0, datetime.now().strftime("%d-%m-%Y"))
        self.bakim_tarih_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        ttk.Label(form_frame, text="Saat:").grid(row=1, column=0, sticky="w", pady=5)
        self.bakim_saat_entry = ttk.Entry(form_frame)
        self.bakim_saat_entry.insert(0, datetime.now().strftime("%H:%M"))
        self.bakim_saat_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        ttk.Label(form_frame, text="Tespit Edilen Arıza:").grid(row=2, column=0, sticky="w", pady=5)
        self.bakim_ariza_entry = ttk.Entry(form_frame)
        self.bakim_ariza_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        ttk.Label(form_frame, text="Yapılan İşlem:").grid(row=3, column=0, sticky="w", pady=5)
        self.bakim_islem_entry = ttk.Entry(form_frame)
        self.bakim_islem_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        ttk.Label(form_frame, text="Parça Ücreti:").grid(row=4, column=0, sticky="w", pady=5)
        self.bakim_parca_ucreti_entry = ttk.Entry(form_frame)
        self.bakim_parca_ucreti_entry.insert(0, "0")
        self.bakim_parca_ucreti_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        ttk.Label(form_frame, text="İşçilik Ücreti:").grid(row=5, column=0, sticky="w", pady=5)
        self.bakim_iscilik_ucreti_entry = ttk.Entry(form_frame)
        self.bakim_iscilik_ucreti_entry.insert(0, "0")
        self.bakim_iscilik_ucreti_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        
        ttk.Label(form_frame, text="Toplam Tutar:").grid(row=6, column=0, sticky="w", pady=5)
        self.bakim_toplam_tutar_entry = ttk.Entry(form_frame, state="readonly")
        self.bakim_toplam_tutar_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")
        
        ttk.Label(form_frame, text="Güncel KM:").grid(row=7, column=0, sticky="w", pady=5)
        self.bakim_notlar_entry = ttk.Entry(form_frame)
        self.bakim_notlar_entry.grid(row=7, column=1, padx=10, pady=5, sticky="ew")
        
        # Toplam tutarı hesapla butonu
        ttk.Button(
            form_frame, 
            text="Toplamı Hesapla", 
            command=self.bakim_toplam_hesapla
        ).grid(row=8, column=0, columnspan=2, pady=5)
        
        # Kaydet butonu
        ttk.Button(
            form_frame, 
            text="Kaydet", 
            command=self.bakim_kaydi_ekle
        ).grid(row=9, column=0, columnspan=2, pady=10)
        
        # Ücret alanlarına değişiklik izleme ekle
        self.bakim_parca_ucreti_entry.bind("<KeyRelease>", lambda e: self.bakim_toplam_hesapla())
        self.bakim_iscilik_ucreti_entry.bind("<KeyRelease>", lambda e: self.bakim_toplam_hesapla())

    def create_status_bar(self):
        """Durum çubuğunu oluşturur"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(self.status_bar, text=f"Veritabanı: {os.path.basename(self.db_path)}").pack(side=tk.LEFT)
        
        self.status_message = ttk.Label(self.status_bar, text="Hazır")
        self.status_message.pack(side=tk.LEFT, padx=20)
        
        ttk.Label(
            self.status_bar, 
            text=f"Son Güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        ).pack(side=tk.RIGHT)

    def load_initial_data(self):
        """Başlangıç verilerini yükler"""
        try:
            self.arac_listesini_guncelle()
            self.depo_durumunu_guncelle()
            self.yakit_kayitlarini_yukle()
            self.depo_kayitlarini_yukle()
            self.rapor_arac_combobox_guncelle()
            self.rapor_ay_combobox_guncelle()
            self.arac_detay_combobox_guncelle()
            self.bakim_arac_combobox_guncelle()
        except Exception as e:
            self.show_error(f"Başlangıç verileri yüklenirken hata: {str(e)}")

    def arac_listesini_guncelle(self):
        """Araç listesini yeniler"""
        for row in self.arac_tree.get_children():
            self.arac_tree.delete(row)
        
        try:
            self.cursor.execute("SELECT plaka, model, mevcut_km, model_yili, arac_surucusu FROM araclar ORDER BY plaka")
            for row in self.cursor.fetchall():
                self.arac_tree.insert("", tk.END, values=row)
            
            self.yakit_arac_combobox_guncelle()
        except Exception as e:
            self.show_error(f"Araç listesi güncellenirken hata: {str(e)}")

    def yakit_arac_combobox_guncelle(self):
        """Yakıt aracı combobox'ını günceller"""
        try:
            self.cursor.execute("SELECT arac_id, plaka FROM araclar ORDER BY plaka")
            araclar = [f"{plaka} (ID:{arac_id})" for arac_id, plaka in self.cursor.fetchall()]
            self.yakit_arac_combobox['values'] = araclar
            if araclar:
                self.yakit_arac_combobox.current(0)
        except Exception as e:
            self.show_error(f"Araç combobox güncellenirken hata: {str(e)}")

    def rapor_arac_combobox_guncelle(self):
        """Rapor aracı combobox'ını günceller"""
        try:
            self.cursor.execute("SELECT arac_id, plaka FROM araclar ORDER BY plaka")
            araclar = ["Tüm Araçlar"] + [f"{plaka} (ID:{arac_id})" for arac_id, plaka in self.cursor.fetchall()]
            self.rapor_arac_combobox['values'] = araclar
            if araclar:
                self.rapor_arac_combobox.current(0)
        except Exception as e:
            self.show_error(f"Rapor aracı combobox güncellenirken hata: {str(e)}")

    def arac_detay_combobox_guncelle(self):
        """Araç detay combobox'ını günceller"""
        try:
            self.cursor.execute("SELECT arac_id, plaka FROM araclar ORDER BY plaka")
            araclar = [f"{plaka} (ID:{arac_id})" for arac_id, plaka in self.cursor.fetchall()]
            self.arac_detay_combobox['values'] = araclar
            if araclar:
                self.arac_detay_combobox.current(0)
        except Exception as e:
            self.show_error(f"Araç detay combobox güncellenirken hata: {str(e)}")

    def bakim_arac_combobox_guncelle(self):
        """Bakım aracı combobox'ını günceller"""
        try:
            self.cursor.execute("SELECT arac_id, plaka FROM araclar ORDER BY plaka")
            araclar = [f"{plaka} (ID:{arac_id})" for arac_id, plaka in self.cursor.fetchall()]
            self.bakim_arac_combobox['values'] = araclar
            if araclar:
                self.bakim_arac_combobox.current(0)
        except Exception as e:
            self.show_error(f"Bakım aracı combobox güncellenirken hata: {str(e)}")

    def rapor_ay_combobox_guncelle(self):
        """Rapor ay combobox'ını günceller"""
        try:
            self.cursor.execute("SELECT DISTINCT strftime('%m-%Y', tarih) FROM yakit_kayitlari ORDER BY tarih DESC")
            aylar = ["Tüm Aylar"] + [ay[0] for ay in self.cursor.fetchall()]
            self.rapor_ay_combobox['values'] = aylar
            if aylar:
                self.rapor_ay_combobox.current(0)
        except Exception as e:
            self.show_error(f"Ay combobox güncellenirken hata: {str(e)}")

    def yakit_kayitlarini_yukle(self):
        """Yakıt kayıtlarını yükler"""
        for row in self.yakit_tree.get_children():
            self.yakit_tree.delete(row)
        
        try:
            self.cursor.execute('''
            SELECT y.tarih, a.plaka, y.km, y.yakit_miktari, y.notlar
            FROM yakit_kayitlari y
            JOIN araclar a ON y.arac_id = a.arac_id
            ORDER BY y.tarih DESC
            LIMIT 500
            ''')
            
            for row in self.cursor.fetchall():
                self.yakit_tree.insert("", tk.END, values=row)
        except Exception as e:
            self.show_error(f"Yakıt kayıtları yüklenirken hata: {str(e)}")

    def depo_kayitlarini_yukle(self):
        """Depo dolum kayıtlarını yükler"""
        for row in self.depo_tree.get_children():
            self.depo_tree.delete(row)
        
        try:
            self.cursor.execute("""
            SELECT tarih, miktar, notlar 
            FROM depo_dolumlari 
            ORDER BY tarih DESC
            LIMIT 500
            """)
            
            for row in self.cursor.fetchall():
                self.depo_tree.insert("", tk.END, values=row)
        except Exception as e:
            self.show_error(f"Depo kayıtları yüklenirken hata: {str(e)}")

    def depo_durumunu_guncelle(self):
        """Depo durumunu günceller"""
        try:
            self.cursor.execute("SELECT mevcut_yakit FROM depo WHERE depo_id = 1")
            result = self.cursor.fetchone()
            if result:
                mevcut_yakit = result[0]
                self.depo_durum_label.config(text=f"Depo Durumu: {mevcut_yakit:.2f} Litre")
            else:
                self.depo_durum_label.config(text="Depo Durumu: Bilinmiyor")
        except Exception as e:
            self.show_error(f"Depo durumu güncellenirken hata: {str(e)}")

    def bakim_kayitlarini_getir(self):
        """Seçili aracın bakım kayıtlarını getirir"""
        arac = self.bakim_arac_combobox.get()
        if not arac:
            return
            
        try:
            arac_id = int(arac.split("ID:")[1].rstrip(")"))
            
            # Bakım kayıtlarını temizle
            for row in self.bakim_tree.get_children():
                self.bakim_tree.delete(row)
                
            # Bakım kayıtlarını getir
            self.cursor.execute('''
            SELECT tarih, tespit_edilen_ariza, yapilan_islem, toplam_tutar
            FROM bakim_tamirat
            WHERE arac_id = ?
            ORDER BY tarih DESC
            ''', (arac_id,))
            
            for row in self.cursor.fetchall():
                self.bakim_tree.insert("", tk.END, values=row)
                
        except Exception as e:
            self.show_error(f"Bakım kayıtları getirilirken hata: {str(e)}")

    def bakim_toplam_hesapla(self):
        """Bakım kaydı için toplam tutarı hesaplar"""
        try:
            parca_ucreti = float(self.bakim_parca_ucreti_entry.get() or 0)
            iscilik_ucreti = float(self.bakim_iscilik_ucreti_entry.get() or 0)
            toplam = parca_ucreti + iscilik_ucreti
            self.bakim_toplam_tutar_entry.config(state="normal")
            self.bakim_toplam_tutar_entry.delete(0, tk.END)
            self.bakim_toplam_tutar_entry.insert(0, f"{toplam:.2f}")
            self.bakim_toplam_tutar_entry.config(state="readonly")
        except ValueError:
            self.bakim_toplam_tutar_entry.config(state="normal")
            self.bakim_toplam_tutar_entry.delete(0, tk.END)
            self.bakim_toplam_tutar_entry.insert(0, "0.00")
            self.bakim_toplam_tutar_entry.config(state="readonly")

    def bakim_kaydi_ekle(self):
        """Yeni bakım kaydı ekler"""
        arac = self.bakim_arac_combobox.get()
        tarih = self.bakim_tarih_entry.get().strip()
        saat = self.bakim_saat_entry.get().strip()
        ariza = self.bakim_ariza_entry.get().strip()
        islem = self.bakim_islem_entry.get().strip()
        parca_ucreti = self.bakim_parca_ucreti_entry.get().strip()
        iscilik_ucreti = self.bakim_iscilik_ucreti_entry.get().strip()
        toplam_tutar = self.bakim_toplam_tutar_entry.get().strip()
        notlar = self.bakim_notlar_entry.get().strip()
        
        if not arac:
            self.show_error("Lütfen bir araç seçin!")
            return
            
        try:
            arac_id = int(arac.split("ID:")[1].rstrip(")"))
            
            # Tarih kontrolü
            try:
                datetime.strptime(tarih, "%d-%m-%Y")
            except ValueError:
                raise ValueError("Tarih formatı yanlış! Örnek: 2023-01-15")
                
            # Saat kontrolü
            try:
                datetime.strptime(saat, "%H:%M")
            except ValueError:
                raise ValueError("Saat formatı yanlış! Örnek: 14:30")
                
            # Ücretler
            parca_ucreti = float(parca_ucreti) if parca_ucreti else 0
            iscilik_ucreti = float(iscilik_ucreti) if iscilik_ucreti else 0
            toplam_tutar = float(toplam_tutar) if toplam_tutar else 0
            
            # Bakım kaydını ekle
            self.cursor.execute('''
            INSERT INTO bakim_tamirat (
                arac_id, tarih, saat, tespit_edilen_ariza, yapilan_islem,
                parca_ucreti, iscilik_ucreti, toplam_tutar, notlar
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                arac_id, tarih, saat, ariza, islem,
                parca_ucreti, iscilik_ucreti, toplam_tutar, notlar
            ))
            
            self.conn.commit()
            self.show_success("Bakım kaydı başarıyla eklendi!")
            
            # Formu temizle
            self.bakim_tarih_entry.delete(0, tk.END)
            self.bakim_tarih_entry.insert(0, datetime.now().strftime("%d-%m-%Y"))
            self.bakim_saat_entry.delete(0, tk.END)
            self.bakim_saat_entry.insert(0, datetime.now().strftime("%H:%M"))
            self.bakim_ariza_entry.delete(0, tk.END)
            self.bakim_islem_entry.delete(0, tk.END)
            self.bakim_parca_ucreti_entry.delete(0, tk.END)
            self.bakim_parca_ucreti_entry.insert(0, "0")
            self.bakim_iscilik_ucreti_entry.delete(0, tk.END)
            self.bakim_iscilik_ucreti_entry.insert(0, "0")
            self.bakim_toplam_tutar_entry.config(state="normal")
            self.bakim_toplam_tutar_entry.delete(0, tk.END)
            self.bakim_toplam_tutar_entry.insert(0, "0.00")
            self.bakim_toplam_tutar_entry.config(state="readonly")
            self.bakim_notlar_entry.delete(0, tk.END)
            
            # Bakım kayıtlarını yenile
            self.bakim_kayitlarini_getir()
            
        except ValueError as ve:
            self.show_error(f"Geçersiz değer: {str(ve)}")
        except Exception as e:
            self.show_error(f"Bakım kaydı eklenirken hata: {str(e)}")
            self.conn.rollback()

    def bakim_kaydi_sil(self):
        """Seçili bakım kaydını siler"""
        selected = self.bakim_tree.selection()
        if not selected:
            self.show_error("Lütfen silmek için bir kayıt seçin!")
            return
            
        kayit = self.bakim_tree.item(selected[0])['values']
        tarih, ariza, islem, tutar = kayit
        
        if not messagebox.askyesno(
            "Onay", 
            f"{tarih} tarihli bakım kaydını silmek istediğinize emin misiniz?\nArıza: {ariza}\nİşlem: {islem}\nTutar: {tutar}"
        ):
            return
            
        try:
            arac = self.bakim_arac_combobox.get()
            arac_id = int(arac.split("ID:")[1].rstrip(")"))
            
            self.cursor.execute('''
            DELETE FROM bakim_tamirat 
            WHERE arac_id = ? AND tarih = ? AND tespit_edilen_ariza = ?
            ''', (arac_id, tarih, ariza))
            
            self.conn.commit()
            self.show_success("Bakım kaydı başarıyla silindi!")
            
            self.bakim_kayitlarini_getir()
            
        except Exception as e:
            self.show_error(f"Bakım kaydı silinirken hata: {str(e)}")
            self.conn.rollback()

    def bakim_kaydi_duzenle(self):
        """Seçili bakım kaydını düzenler"""
        selected = self.bakim_tree.selection()
        if not selected:
            self.show_error("Lütfen düzenlemek için bir kayıt seçin!")
            return
            
        kayit = self.bakim_tree.item(selected[0])['values']
        tarih, ariza, islem, tutar = kayit
        
        try:
            arac = self.bakim_arac_combobox.get()
            arac_id = int(arac.split("ID:")[1].rstrip(")"))
            
            # Kaydın detaylarını getir
            self.cursor.execute('''
            SELECT tarih, saat, tespit_edilen_ariza, yapilan_islem, 
                   parca_ucreti, iscilik_ucreti, toplam_tutar, notlar
            FROM bakim_tamirat
            WHERE arac_id = ? AND tarih = ? AND tespit_edilen_ariza = ?
            ''', (arac_id, tarih, ariza))
            
            kayit_detay = self.cursor.fetchone()
            if not kayit_detay:
                self.show_error("Kayıt bulunamadı!")
                return
                
            # Formu doldur
            self.bakim_tarih_entry.delete(0, tk.END)
            self.bakim_tarih_entry.insert(0, kayit_detay[0])
            
            self.bakim_saat_entry.delete(0, tk.END)
            self.bakim_saat_entry.insert(0, kayit_detay[1])
            
            self.bakim_ariza_entry.delete(0, tk.END)
            self.bakim_ariza_entry.insert(0, kayit_detay[2])
            
            self.bakim_islem_entry.delete(0, tk.END)
            self.bakim_islem_entry.insert(0, kayit_detay[3])
            
            self.bakim_parca_ucreti_entry.delete(0, tk.END)
            self.bakim_parca_ucreti_entry.insert(0, str(kayit_detay[4]))
            
            self.bakim_iscilik_ucreti_entry.delete(0, tk.END)
            self.bakim_iscilik_ucreti_entry.insert(0, str(kayit_detay[5]))
            
            self.bakim_toplam_tutar_entry.config(state="normal")
            self.bakim_toplam_tutar_entry.delete(0, tk.END)
            self.bakim_toplam_tutar_entry.insert(0, str(kayit_detay[6]))
            self.bakim_toplam_tutar_entry.config(state="readonly")
            
            self.bakim_notlar_entry.delete(0, tk.END)
            self.bakim_notlar_entry.insert(0, kayit_detay[7] if kayit_detay[7] else "")
            
            # Önce kaydı sil
            self.cursor.execute('''
            DELETE FROM bakim_tamirat 
            WHERE arac_id = ? AND tarih = ? AND tespit_edilen_ariza = ?
            ''', (arac_id, tarih, ariza))
            
            self.conn.commit()
            
            # Bakım kayıtlarını yenile
            self.bakim_kayitlarini_getir()
            
        except Exception as e:
            self.show_error(f"Bakım kaydı düzenlenirken hata: {str(e)}")
            self.conn.rollback()

    def arac_ekle(self):
        """Yeni araç ekler"""
        plaka = self.plaka_entry.get().strip().upper()
        model = self.model_entry.get().strip()
        km = self.km_entry.get().strip()
        model_yili = self.model_yili_entry.get().strip()
        muayene_tarihi = self.muayene_tarihi_entry.get().strip()
        bakim_tarihi = self.bakim_tarihi_entry.get().strip()
        arac_surucusu = self.arac_surucusu_entry.get().strip()
        
        if not plaka or not model or not km:
            self.show_error("Lütfen zorunlu alanları doldurun (Plaka, Model, KM)!")
            return
        
        try:
            km = int(km)
            if km < 0:
                raise ValueError("KM negatif olamaz")
            
            model_yili = int(model_yili) if model_yili else None
                
            self.cursor.execute(
                """INSERT INTO araclar 
                (plaka, model, mevcut_km, model_yili, muayene_tarihi, bakim_tarihi, arac_surucusu) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                (plaka, model, km, model_yili, muayene_tarihi, bakim_tarihi, arac_surucusu)
            )
            self.conn.commit()
            
            self.show_success(f"{plaka} plakalı araç başarıyla eklendi!")
            self.plaka_entry.delete(0, tk.END)
            self.model_entry.delete(0, tk.END)
            self.km_entry.delete(0, tk.END)
            self.model_yili_entry.delete(0, tk.END)
            self.muayene_tarihi_entry.delete(0, tk.END)
            self.bakim_tarihi_entry.delete(0, tk.END)
            self.arac_surucusu_entry.delete(0, tk.END)
            
            self.arac_listesini_guncelle()
            self.rapor_arac_combobox_guncelle()
            self.arac_detay_combobox_guncelle()
            self.bakim_arac_combobox_guncelle()
            
        except ValueError as ve:
            self.show_error(f"Geçersiz KM değeri: {str(ve)}")
        except sqlite3.IntegrityError:
            self.show_error("Bu plaka zaten kayıtlı!")
        except Exception as e:
            self.show_error(f"Araç eklenirken hata: {str(e)}")
            self.conn.rollback()

    def arac_sil(self):
        """Seçili aracı siler"""
        selected = self.arac_tree.selection()
        if not selected:
            self.show_error("Lütfen silmek için bir araç seçin!")
            return
        
        plaka = self.arac_tree.item(selected[0])['values'][0]
        
        if not messagebox.askyesno(
            "Onay", 
            f"{plaka} plakalı aracı ve tüm yakıt kayıtlarını silmek istediğinize emin misiniz?\nBu işlem geri alınamaz!"
        ):
            return
        
        try:
            # Önce aracın ID'sini al
            self.cursor.execute("SELECT arac_id FROM araclar WHERE plaka = ?", (plaka,))
            result = self.cursor.fetchone()
            
            if not result:
                self.show_error("Araç bulunamadı!")
                return
                
            arac_id = result[0]
            
            # Yakıt kayıtlarını sil
            self.cursor.execute("DELETE FROM yakit_kayitlari WHERE arac_id = ?", (arac_id,))
            
            # Bakım kayıtlarını sil
            self.cursor.execute("DELETE FROM bakim_tamirat WHERE arac_id = ?", (arac_id,))
            
            # Aracı sil
            self.cursor.execute("DELETE FROM araclar WHERE arac_id = ?", (arac_id,))
            
            self.conn.commit()
            self.show_success(f"{plaka} plakalı araç ve tüm kayıtları silindi!")
            
            self.arac_listesini_guncelle()
            self.yakit_kayitlarini_yukle()
            self.rapor_arac_combobox_guncelle()
            self.arac_detay_combobox_guncelle()
            self.bakim_arac_combobox_guncelle()
            
        except Exception as e:
            self.show_error(f"Araç silinirken hata: {str(e)}")
            self.conn.rollback()

    def arac_detay_goster(self):
        """Araç detaylarını gösterir"""
        selected = self.arac_tree.selection()
        if not selected:
            self.show_error("Lütfen detaylarını görmek için bir araç seçin!")
            return
        
        plaka = self.arac_tree.item(selected[0])['values'][0]
        
        # Araç detay sekmesine geç
        self.notebook.select(self.arac_detay_frame)
        
        # Combobox'ta seçili aracı bul
        for i, item in enumerate(self.arac_detay_combobox['values']):
            if plaka in item:
                self.arac_detay_combobox.current(i)
                self.arac_detay_getir()
                break

    def arac_detay_getir(self):
        """Seçili aracın detaylarını getirir"""
        arac = self.arac_detay_combobox.get()
        if not arac:
            return
            
        try:
            arac_id = int(arac.split("ID:")[1].rstrip(")"))
            
            # Araç bilgilerini al
            self.cursor.execute("""
            SELECT plaka, model, mevcut_km, model_yili, muayene_tarihi, bakim_tarihi, arac_surucusu 
            FROM araclar 
            WHERE arac_id = ?
            """, (arac_id,))
            
            result = self.cursor.fetchone()
            if not result:
                self.show_error("Araç bulunamadı!")
                return
                
            plaka, model, km, model_yili, muayene_tarihi, bakim_tarihi, arac_surucusu = result
            
            # Bilgileri göster
            self.arac_detay_labels['plaka'].config(text=plaka)
            self.arac_detay_labels['model'].config(text=model)
            self.arac_detay_labels['mevcut_km'].config(text=f"{km:,} km")
            self.arac_detay_labels['model_yili'].config(text=model_yili if model_yili else "-")
            self.arac_detay_labels['muayene_tarihi'].config(text=muayene_tarihi if muayene_tarihi else "-")
            self.arac_detay_labels['bakim_tarihi'].config(text=bakim_tarihi if bakim_tarihi else "-")
            self.arac_detay_labels['arac_surucusu'].config(text=arac_surucusu if arac_surucusu else "-")
            
            # Güncelleme formunu doldur
            self.update_entries['model_yili'].delete(0, tk.END)
            self.update_entries['model_yili'].insert(0, str(model_yili) if model_yili else "")
            
            self.update_entries['muayene_tarihi'].delete(0, tk.END)
            self.update_entries['muayene_tarihi'].insert(0, muayene_tarihi) if muayene_tarihi else ""
            
            self.update_entries['bakim_tarihi'].delete(0, tk.END)
            self.update_entries['bakim_tarihi'].insert(0, bakim_tarihi) if bakim_tarihi else ""
            
            self.update_entries['arac_surucusu'].delete(0, tk.END)
            self.update_entries['arac_surucusu'].insert(0, arac_surucusu) if arac_surucusu else ""
            
            # Uyarıları kontrol et
            uyarilar = []
            today = datetime.now().date()
            
            if muayene_tarihi:
                try:
                    muayene_tarihi_dt = datetime.strptime(muayene_tarihi, "%d-%m-%Y").date()
                    if muayene_tarihi_dt < today:
                        uyarilar.append(f"Muayene tarihi geçmiş: {muayene_tarihi}")
                    elif (muayene_tarihi_dt - today).days <= 30:
                        uyarilar.append(f"Muayene tarihi yaklaşıyor: {muayene_tarihi} (Kalan gün: {(muayene_tarihi_dt - today).days})")
                except ValueError:
                    pass
                    
            if bakim_tarihi:
                try:
                    bakim_tarihi_dt = datetime.strptime(bakim_tarihi, "%d-%m-%Y").date()
                    if bakim_tarihi_dt < today:
                        uyarilar.append(f"Bakım tarihi geçmiş: {bakim_tarihi}")
                    elif (bakim_tarihi_dt - today).days <= 30:
                        uyarilar.append(f"Bakım tarihi yaklaşıyor: {bakim_tarihi} (Kalan gün: {(bakim_tarihi_dt - today).days})")
                except ValueError:
                    pass
            
            if uyarilar:
                self.uyari_label.config(text="\n".join(uyarilar), foreground="red")
            else:
                self.uyari_label.config(text="Herhangi bir uyarı yok.", foreground="green")
            
            # Yakıt kayıtlarını getir
            for row in self.arac_yakit_tree.get_children():
                self.arac_yakit_tree.delete(row)
                
            self.cursor.execute('''
            SELECT tarih, km, yakit_miktari, notlar
            FROM yakit_kayitlari
            WHERE arac_id = ?
            ORDER BY tarih DESC
            LIMIT 50
            ''', (arac_id,))
            
            for row in self.cursor.fetchall():
                self.arac_yakit_tree.insert("", tk.END, values=row)
                
        except Exception as e:
            self.show_error(f"Araç detayları getirilirken hata: {str(e)}")

    def arac_detay_guncelle(self):
        """Araç detaylarını günceller"""
        arac = self.arac_detay_combobox.get()
        if not arac:
            self.show_error("Lütfen bir araç seçin!")
            return
            
        try:
            arac_id = int(arac.split("ID:")[1].rstrip(")"))
            
            model_yili = self.update_entries['model_yili'].get().strip()
            muayene_tarihi = self.update_entries['muayene_tarihi'].get().strip()
            bakim_tarihi = self.update_entries['bakim_tarihi'].get().strip()
            arac_surucusu = self.update_entries['arac_surucusu'].get().strip()
            
            # Tarih formatlarını kontrol et
            if muayene_tarihi:
                try:
                    datetime.strptime(muayene_tarihi, "%d-%m-%Y")
                except ValueError:
                    raise ValueError("Muayene tarihi formatı yanlış! Örnek: 15-01-2025")
                    
            if bakim_tarihi:
                try:
                    datetime.strptime(bakim_tarihi, "%d-%m-%Y")
                except ValueError:
                    raise ValueError("Bakım tarihi formatı yanlış! Örnek: 15-01-2025")
            
            # Model yılını kontrol et
            model_yili = int(model_yili) if model_yili else None
            
            # Veritabanını güncelle
            self.cursor.execute('''
            UPDATE araclar 
            SET model_yili = ?, muayene_tarihi = ?, bakim_tarihi = ?, arac_surucusu = ?
            WHERE arac_id = ?
            ''', (model_yili, muayene_tarihi, bakim_tarihi, arac_surucusu, arac_id))
            
            self.conn.commit()
            self.show_success("Araç bilgileri başarıyla güncellendi!")
            
            # Bilgileri yenile
            self.arac_detay_getir()
            self.arac_listesini_guncelle()
            
        except ValueError as ve:
            self.show_error(f"Geçersiz değer: {str(ve)}")
        except Exception as e:
            self.show_error(f"Güncelleme sırasında hata: {str(e)}")
            self.conn.rollback()

    def yakit_ekle(self):
        """Yeni yakıt kaydı ekler"""
        arac = self.yakit_arac_combobox.get()
        km = self.yakit_km_entry.get().strip()
        miktar = self.yakit_miktar_entry.get().strip()
        tarih = self.yakit_tarih_entry.get().strip()
        notlar = self.yakit_not_entry.get().strip()
        
        if not arac or not km or not miktar or not tarih:
            self.show_error("Lütfen zorunlu alanları doldurun!")
            return
        
        try:
            # Araç ID'sini al
            arac_id = int(arac.split("ID:")[1].rstrip(")"))
            
            # KM ve miktarı kontrol et
            km = int(km)
            miktar = float(miktar)
            
            if km < 0 or miktar <= 0:
                raise ValueError("KM ve miktar pozitif olmalıdır")
            
            # Tarih formatını kontrol et
            try:
                datetime.strptime(tarih, "%d-%m-%Y %H:%M")
            except ValueError:
                raise ValueError("Tarih formatı yanlış! Örnek: 2023-01-15 14:30")
            
            # Yakıt ekle
            self.cursor.execute(
                "INSERT INTO yakit_kayitlari (arac_id, km, yakit_miktari, notlar, tarih) VALUES (?, ?, ?, ?, ?)",
                (arac_id, km, miktar, notlar, tarih)
            )
            
            # Aracın mevcut km'sini güncelle
            self.cursor.execute(
                "UPDATE araclar SET mevcut_km = ? WHERE arac_id = ?",
                (km, arac_id)
            )
            
            # Depodan yakıt düş (varsayılan depo ID=1)
            self.cursor.execute(
                "UPDATE depo SET mevcut_yakit = mevcut_yakit - ?, son_guncelleme = datetime('now') WHERE depo_id = 1",
                (miktar,)
            )
            
            self.conn.commit()
            self.show_success("Yakıt kaydı başarıyla eklendi!")
            
            # Alanları temizle
            self.yakit_km_entry.delete(0, tk.END)
            self.yakit_miktar_entry.delete(0, tk.END)
            self.yakit_not_entry.delete(0, tk.END)
            self.yakit_tarih_entry.delete(0, tk.END)
            self.yakit_tarih_entry.insert(0, datetime.now().strftime("%d-%m-%Y %H:%M"))
            
            # Listeleri güncelle
            self.yakit_kayitlarini_yukle()
            self.arac_listesini_guncelle()
            self.depo_durumunu_guncelle()
            
            # Araç detay sekmesindeki bilgileri güncelle
            if hasattr(self, 'arac_detay_combobox'):
                current_arac = self.arac_detay_combobox.get()
                if current_arac and str(arac_id) in current_arac:
                    self.arac_detay_getir()
            
        except ValueError as ve:
            self.show_error(f"Geçersiz değer: {str(ve)}")
        except Exception as e:
            self.show_error(f"Yakıt eklenirken hata: {str(e)}")
            self.conn.rollback()

    def yakit_kaydi_sil(self):
        """Seçili yakıt kaydını siler"""
        selected = self.yakit_tree.selection()
        if not selected:
            self.show_error("Lütfen silmek için bir kayıt seçin!")
            return
        
        kayit = self.yakit_tree.item(selected[0])['values']
        tarih, plaka, km, miktar, notlar = kayit
        
        if not messagebox.askyesno(
            "Onay", 
            f"{tarih} tarihli {plaka} aracına ait {miktar}L yakıt kaydını silmek istediğinize emin misiniz?\nBu işlem geri alınamaz!"
        ):
            return
        
        try:
            # Önce aracın ID'sini al
            self.cursor.execute("SELECT arac_id FROM araclar WHERE plaka = ?", (plaka,))
            result = self.cursor.fetchone()
            
            if not result:
                self.show_error("Araç bulunamadı!")
                return
                
            arac_id = result[0]
            
            # Yakıt kaydını sil
            self.cursor.execute(
                "DELETE FROM yakit_kayitlari WHERE arac_id = ? AND tarih = ? AND km = ?",
                (arac_id, tarih, km)
            )
            
            # Depoya yakıt ekle (silinen kayıt geri eklendi)
            self.cursor.execute(
                "UPDATE depo SET mevcut_yakit = mevcut_yakit + ?, son_guncelleme = datetime('now') WHERE depo_id = 1",
                (float(miktar),)
            )
            
            self.conn.commit()
            self.show_success("Yakıt kaydı başarıyla silindi!")
            
            self.yakit_kayitlarini_yukle()
            self.depo_durumunu_guncelle()
            
            # Araç detay sekmesindeki bilgileri güncelle
            if hasattr(self, 'arac_detay_combobox'):
                current_arac = self.arac_detay_combobox.get()
                if current_arac and str(arac_id) in current_arac:
                    self.arac_detay_getir()
            
        except Exception as e:
            self.show_error(f"Yakıt kaydı silinirken hata: {str(e)}")
            self.conn.rollback()

    def depo_doldur(self):
        """Depo dolum kaydı ekler"""
        miktar = self.depo_miktar_entry.get().strip()
        tarih = self.depo_tarih_entry.get().strip()
        notlar = self.depo_not_entry.get().strip()
        
        if not miktar or not tarih:
            self.show_error("Lütfen zorunlu alanları doldurun!")
            return
        
        try:
            miktar = float(miktar)
            
            if miktar <= 0:
                raise ValueError("Miktar pozitif olmalıdır")
            
            # Tarih formatını kontrol et
            try:
                datetime.strptime(tarih, "%d-%m-%Y %H:%M")
            except ValueError:
                raise ValueError("Tarih formatı yanlış! Örnek: 2023-01-15 14:30")
            
            # Depo dolum kaydı ekle
            self.cursor.execute(
                "INSERT INTO depo_dolumlari (miktar, notlar, tarih) VALUES (?, ?, ?)",
                (miktar, notlar, tarih)
            )
            
            # Depo durumunu güncelle
            self.cursor.execute(
                "UPDATE depo SET mevcut_yakit = mevcut_yakit + ?, son_guncelleme = datetime('now') WHERE depo_id = 1",
                (miktar,)
            )
            
            self.conn.commit()
            self.show_success(f"Depo başarıyla {miktar}L dolduruldu!")
            
            # Alanları temizle
            self.depo_miktar_entry.delete(0, tk.END)
            self.depo_not_entry.delete(0, tk.END)
            self.depo_tarih_entry.delete(0, tk.END)
            self.depo_tarih_entry.insert(0, datetime.now().strftime("%d-%m-%Y %H:%M"))
            
            # Listeleri güncelle
            self.depo_kayitlarini_yukle()
            self.depo_durumunu_guncelle()
            
        except ValueError as ve:
            self.show_error(f"Geçersiz değer: {str(ve)}")
        except Exception as e:
            self.show_error(f"Depo doldurulurken hata: {str(e)}")
            self.conn.rollback()

    def depo_dolum_sil(self):
        """Seçili depo dolum kaydını siler"""
        selected = self.depo_tree.selection()
        if not selected:
            self.show_error("Lütfen silmek için bir kayıt seçin!")
            return
        
        kayit = self.depo_tree.item(selected[0])['values']
        tarih, miktar, notlar = kayit
        
        if not messagebox.askyesno(
            "Onay", 
            f"{tarih} tarihli {miktar}L depo dolum kaydını silmek istediğinize emin misiniz?\nBu işlem geri alınamaz!"
        ):
            return
        
        try:
            miktar = float(miktar)
            
            # Depo durumunu güncelle (miktarı çıkar)
            self.cursor.execute(
                "UPDATE depo SET mevcut_yakit = mevcut_yakit - ?, son_guncelleme = datetime('now') WHERE depo_id = 1",
                (miktar,)
            )
            
            # Kaydı sil
            self.cursor.execute(
                "DELETE FROM depo_dolumlari WHERE tarih = ? AND miktar = ?",
                (tarih, miktar)
            )
            
            self.conn.commit()
            self.show_success("Depo dolum kaydı başarıyla silindi!")
            
            self.depo_kayitlarini_yukle()
            self.depo_durumunu_guncelle()
            
        except Exception as e:
            self.show_error(f"Depo kaydı silinirken hata: {str(e)}")
            self.conn.rollback()

    def filtrele(self):
        """Raporları filtreler"""
        arac = self.rapor_arac_combobox.get()
        ay = self.rapor_ay_combobox.get()
        
        # Aracı filtrele
        arac_kosulu = ""
        if arac and arac != "Tüm Araçlar":
            try:
                arac_id = int(arac.split("ID:")[1].rstrip(")"))
                arac_kosulu = f"AND y.arac_id = {arac_id}"
            except:
                self.show_error("Geçersiz araç seçimi!")
                return
        
        # Ayı filtrele
        ay_kosulu = ""
        if ay and ay != "Tüm Aylar":
            ay_kosulu = f"AND strftime('%m-%Y', y.tarih) = '{ay}'"
        
        try:
            # Rapor tablosunu güncelle
            for row in self.rapor_tree.get_children():
                self.rapor_tree.delete(row)
            
            query = f'''
            SELECT y.tarih, a.plaka, y.km, y.yakit_miktari, y.notlar
            FROM yakit_kayitlari y
            JOIN araclar a ON y.arac_id = a.arac_id
            WHERE 1=1 {arac_kosulu} {ay_kosulu}
            ORDER BY y.tarih DESC
            LIMIT 500
            '''
            
            self.cursor.execute(query)
            for row in self.cursor.fetchall():
                self.rapor_tree.insert("", tk.END, values=row)
            
            # İstatistikleri hesapla
            self.yakit_istatistiklerini_hesapla()
            
        except Exception as e:
            self.show_error(f"Filtreleme sırasında hata: {str(e)}")

    def yakit_istatistiklerini_hesapla(self):
        """Yakıt tüketim istatistiklerini hesaplar (L/100km cinsinden)"""
        try:
            arac = self.rapor_arac_combobox.get()
            
            if not arac or arac == "Tüm Araçlar":
                self.ortalama_tuketim_label.config(text="Genel Ortalama (L/100km): -")
                self.aylik_ortalama_label.config(text="Aylık Ortalama (L/100km): -")
                self.yillik_ortalama_label.config(text="Yıllık Ortalama (L/100km): -")
                return
                
            arac_id = int(arac.split("ID:")[1].rstrip(")"))
            
            # 1. GENEL ORTALAMA (L/100km)
            self.cursor.execute('''
            SELECT MIN(km), MAX(km), SUM(yakit_miktari) 
            FROM yakit_kayitlari 
            WHERE arac_id = ?
            ''', (arac_id,))
            
            min_km, max_km, toplam_yakit = self.cursor.fetchone()
            
            if min_km is None or max_km is None:
                self.ortalama_tuketim_label.config(text="Genel Ortalama (L/100km): Veri yok")
            else:
                toplam_km = max_km - min_km
                if toplam_km > 0:
                    ortalama = (toplam_yakit / toplam_km) * 100
                    self.ortalama_tuketim_label.config(
                        text=f"Genel Ortalama: {ortalama:.2f} L/100km"
                    )
                else:
                    self.ortalama_tuketim_label.config(text="Genel Ortalama (L/100km): KM hatası")

            # 2. AYLIK ORTALAMALAR (L/100km)
            self.cursor.execute('''
            SELECT strftime('%m-%Y', tarih) as ay,
                   MIN(km) as bas_km,
                   MAX(km) as son_km,
                   SUM(yakit_miktari) as yakit
            FROM yakit_kayitlari
            WHERE arac_id = ?
            GROUP BY ay
            HAVING son_km > bas_km AND COUNT(*) > 1
            ORDER BY ay
            ''', (arac_id,))
            
            aylik_veriler = self.cursor.fetchall()
            
            if aylik_veriler:
                aylik_ortalama = sum(
                    (yakit/(son_km-bas_km)*100) 
                    for ay, bas_km, son_km, yakit in aylik_veriler
                ) / len(aylik_veriler)
                
                self.aylik_ortalama_label.config(
                    text=f"Aylık Ortalama: {aylik_ortalama:.2f} L/100km"
                )
            else:
                self.aylik_ortalama_label.config(text="Aylık Ortalama (L/100km): Veri yok")

            # 3. YILLIK ORTALAMALAR (L/100km)
            self.cursor.execute('''
            SELECT strftime('%Y', tarih) as yil,
                   MIN(km) as bas_km,
                   MAX(km) as son_km,
                   SUM(yakit_miktari) as yakit
            FROM yakit_kayitlari
            WHERE arac_id = ?
            GROUP BY yil
            HAVING son_km > bas_km AND COUNT(*) > 1
            ORDER BY yil
            ''', (arac_id,))
            
            yillik_veriler = self.cursor.fetchall()
            
            if yillik_veriler:
                yillik_ortalama = sum(
                    (yakit/(son_km-bas_km)*100) 
                    for yil, bas_km, son_km, yakit in yillik_veriler
                ) / len(yillik_veriler)
                
                self.yillik_ortalama_label.config(
                    text=f"Yıllık Ortalama: {yillik_ortalama:.2f} L/100km"
                )
            else:
                self.yillik_ortalama_label.config(text="Yıllık Ortalama (L/100km): Veri yok")

        except Exception as e:
            self.show_error(f"İstatistik hesaplanırken hata: {str(e)}")

    def show_data_analysis(self):
        """Yakıt tüketim grafiğini gösterir"""
        arac = self.rapor_arac_combobox.get()
        
        if not arac or arac == "Tüm Araçlar":
            self.show_error("Lütfen bir araç seçin!")
            return
            
        arac_id = int(arac.split("ID:")[1].rstrip(")"))
        
        try:
            self.cursor.execute('''
            SELECT y.tarih, y.km, y.yakit_miktari
            FROM yakit_kayitlari y
            WHERE y.arac_id = ?
            ORDER BY y.tarih
            ''', (arac_id,))
            
            veriler = self.cursor.fetchall()
            
            if len(veriler) < 2:
                self.show_error("Grafik oluşturmak için yeterli veri yok!")
                return
            
            # Verileri işle
            tarihler = [datetime.strptime(row[0], "%d-%m-%Y %H:%M") for row in veriler]
            kmler = [row[1] for row in veriler]
            yakitlar = [row[2] for row in veriler]
            
            # Tüketim hesapla (L/100km)
            tuketimler = []
            for i in range(1, len(veriler)):
                km_fark = kmler[i] - kmler[i-1]
                if km_fark > 0:
                    tuketim = (yakitlar[i] / km_fark) * 100
                    tuketimler.append(tuketim)
                else:
                    tuketimler.append(0)
            
            # Grafik penceresi oluştur
            graph_window = tk.Toplevel(self.root)
            graph_window.title(f"{arac} Yakıt Tüketim Grafiği")
            graph_window.geometry("900x600")
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6))
            fig.suptitle(f"{arac} Yakıt Tüketim Analizi", fontsize=12)
            
            # KM grafiği
            ax1.plot(tarihler, kmler, 'b-', marker='o', label='Kilometre')
            ax1.set_title('Kilometre Takibi')
            ax1.set_ylabel('KM')
            ax1.grid(True)
            ax1.legend()
            
            # Tüketim grafiği
            ax2.plot(tarihler[1:], tuketimler, 'r-', marker='o', label='Tüketim (L/100km)')
            ax2.set_title('Yakıt Tüketimi')
            ax2.set_ylabel('L/100km')
            ax2.grid(True)
            ax2.legend()
            
            plt.tight_layout()
            
            # Grafiği Tkinter'a göm
            canvas = FigureCanvasTkAgg(fig, master=graph_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Kapatma butonu
            ttk.Button(
                graph_window, 
                text="Kapat", 
                command=graph_window.destroy
            ).pack(pady=5)
            
        except Exception as e:
            self.show_error(f"Grafik oluşturulurken hata: {str(e)}")

    def backup_database(self):
        """Veritabanı yedeği alır"""
        try:
            if not os.path.exists(self.db_path):
                self.show_error("Veritabanı dosyası bulunamadı!")
                return

            backup_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(backup_dir):
                backup_dir = os.path.dirname(self.db_path)
            
            backup_path = filedialog.asksaveasfilename(
                initialdir=backup_dir,
                defaultextension=".db",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")],
                title="Yedek Dosyasını Kaydet",
                initialfile=f"yakit_takip_backup_{datetime.now().strftime('%d%m%Y_%H%M%S')}.db"
            )
            
            if not backup_path:
                return

            # Veritabanı bağlantısını kapat
            self.conn.close()
            
            try:
                # Dosyayı kopyala
                with open(self.db_path, 'rb') as f_source:
                    with open(backup_path, 'wb') as f_target:
                        while True:
                            chunk = f_source.read(1024*1024)  # 1MB'lık parçalar halinde
                            if not chunk:
                                break
                            f_target.write(chunk)
                
                self.show_success(f"Veritabanı yedeği başarıyla alındı:\n{backup_path}")
                
            except PermissionError:
                self.show_error("Dosya yazma izni reddedildi! Lütfen farklı bir konum seçin.")
            except Exception as e:
                self.show_error(f"Yedek alınırken hata oluştu: {str(e)}")
            
            # Veritabanına yeniden bağlan
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
        except Exception as e:
            self.show_error(f"Yedekleme işlemi sırasında hata: {str(e)}")
            try:
                self.conn = sqlite3.connect(self.db_path)
                self.cursor = self.conn.cursor()
            except:
                self.show_error("Veritabanına yeniden bağlanılamadı! Programı yeniden başlatın.")

    def generate_excel_report(self):
        """Excel raporu oluşturur"""
        if not HAS_EXCEL:
            self.show_error("Excel raporlama özelliği devre dışı (openpyxl kurulu değil)")
            return
            
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Yakıt Raporu"
            
            # Başlıklar
            headers = ["Tarih", "Plaka", "KM", "Yakıt Miktarı (L)", "Notlar"]
            ws.append(headers)
            
            # Başlık stilini ayarla
            bold_font = Font(bold=True)
            for cell in ws[1]:
                cell.font = bold_font
            
            # Verileri al
            self.cursor.execute('''
            SELECT y.tarih, a.plaka, y.km, y.yakit_miktari, y.notlar
            FROM yakit_kayitlari y
            JOIN araclar a ON y.arac_id = a.arac_id
            ORDER BY y.tarih DESC
            ''')
            
            # Satırları ekle
            for row in self.cursor.fetchall():
                ws.append(row)
            
            # Sütun genişliklerini ayarla
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                
                for cell in col:
                    try:
                        value = str(cell.value) if cell.value else ""
                        if len(value) > max_length:
                            max_length = len(value)
                    except:
                        pass
                
                adjusted_width = (max_length + 2) * 1.2
                ws.column_dimensions[column].width = adjusted_width
            
            # Kaydetme iletişim kutusu
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop_path):
                desktop_path = os.path.dirname(self.db_path)
            
            file_path = filedialog.asksaveasfilename(
                initialdir=desktop_path,
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Raporu Kaydet",
                initialfile=f"yakit_raporu_{datetime.now().strftime('%d%m%Y_%H%M%S')}.xlsx"
            )
            
            if file_path:
                wb.save(file_path)
                self.show_success(f"Excel raporu başarıyla oluşturuldu:\n{file_path}")
                
                # Raporu aç (Windows için)
                if sys.platform == "win32":
                    try:
                        os.startfile(file_path)
                    except:
                        pass
                
        except Exception as e:
            self.show_error(f"Rapor oluşturulurken hata: {str(e)}")

    def show_help(self):
        """Yardım bilgisi gösterir"""
        help_text = """
        Temelli Yakıt Takip Sistemi Kullanım Kılavuzu

        Araç Yönetimi:
        - Yeni araç eklemek için plaka, model ve mevcut KM bilgilerini girin
        - Araç silmek için listeden seçim yapın
        - Araç detaylarını görüntülemek için "Detayları Gör" butonunu kullanın

        Yakıt İşlemleri:
        - Yakıt eklemek için araç seçin ve diğer bilgileri girin
        - Yakıt kaydı silmek için listeden seçim yapın

        Depo Yönetimi:
        - Depo dolumu yapmak için miktar ve tarih bilgilerini girin
        - Dolum kaydı silmek için listeden seçim yapın

        Raporlar:
        - Filtreleme yaparak istatistikleri görüntüleyin
        - Grafik oluşturarak tüketim analizi yapın
        - Excel raporu oluşturup dışa aktarın

        Araç Detayları:
        - Araç bilgilerini görüntüleyin ve güncelleyin
        - Muayene ve bakım tarihleri için uyarıları görüntüleyin
        - Araç yakıt kayıtlarını listeleyin

        Bakım ve Tamirat:
        - Araç bakım ve tamirat kayıtlarını ekleyin/düzenleyin/silin
        - Parça ve işçilik ücretlerini takip edin
        - Toplam maliyetleri hesaplayın

        Tema:
        - Light/Dark tema arasında geçiş yapabilirsiniz
        """
        messagebox.showinfo("Yardım", help_text.strip())

    def show_about(self):
        """Hakkında bilgisi gösterir"""
        about_text = f"""
        Temelli Yakıt Takip Sistemi

        Sürüm: 1.0
        Son Güncelleme: {datetime.now().strftime('%d.%m.%Y')}
        

        Özellikler:
        - Araç ve yakıt takibi
        - Depo yönetimi
        - Detaylı raporlama
        - Grafiksel analizler
        - Excel'e aktarım
        - Çoklu tema desteği
        - Araç detay yönetimi (muayene, bakım, şoför bilgileri)
        - Bakım ve tamirat takibi

        Veritabanı Konumu:
        {self.db_path}
        """
        messagebox.showinfo("Hakkında", about_text.strip())

    def play_sound(self, sound_type):
        """Ses efekti çalar"""
        if not HAS_SOUND:
            return
            
        try:
            if sound_type == "success":
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            elif sound_type == "error":
                winsound.MessageBeep(winsound.MB_ICONHAND)
            elif sound_type == "SystemStart":
                winsound.PlaySound("SystemStart", winsound.SND_ALIAS)
        except:
            pass

    def show_success(self, message):
        """Başarı mesajı gösterir"""
        messagebox.showinfo("Başarılı", message)
        self.status_message.config(text=message)
        self.play_sound("success")

    def show_error(self, message):
        """Hata mesajı gösterir"""
        messagebox.showerror("Hata", message)
        self.status_message.config(text=message)
        self.play_sound("error")

    def on_closing(self):
        """Uygulamayı kapatır"""
        if messagebox.askokcancel("Çıkış", "Uygulamadan çıkmak istediğinize emin misiniz?"):
            try:
                self.conn.close()
            except:
                pass
            finally:
                self.root.destroy()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = YakıtTakipUygulaması(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Başlatma Hatası", f"Uygulama başlatılamadı: {str(e)}")
