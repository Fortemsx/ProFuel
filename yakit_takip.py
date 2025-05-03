import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from datetime import datetime
from tkinter import font as tkfont
import webbrowser
import os
import sys

class SiparisTakipUygulamasi:
    def __init__(self, root):
        self.root = root
        self.root.title("Sipariş Takip Uygulaması")
        self.root.geometry("1200x700")
        self.root.minsize(1000, 600)
        
        # Veritabanı bağlantısı
        self.veritabani_olustur()
        
        # Stil ayarları
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Renk paleti
        self.renkler = {
            'arkaplan': '#f5f5f5',
            'cerceve': '#e0e0e0',
            'buton': '#3a7ca5',
            'buton_hover': '#2f6690',
            'baslik': '#2c3e50',
            'tablo_baslik': '#3a5169',
            'tablo_satir1': '#ffffff',
            'tablo_satir2': '#f5f5f5',
            'uyari': '#e74c3c',
            'basari': '#27ae60',
            'vurgu': '#3498db'
        }
        
        # Font ayarları
        self.baslik_font = tkfont.Font(family='Segoe UI', size=14, weight='bold')
        self.normal_font = tkfont.Font(family='Segoe UI', size=11)
        self.buton_font = tkfont.Font(family='Segoe UI', size=11, weight='bold')
        self.tablo_font = tkfont.Font(family='Segoe UI', size=10)
        
        # Arayüz bileşenleri
        self.arayuz_olustur()
        
        # Siparişleri yükle
        self.siparisleri_yukle()
        
        # Menü çubuğu oluştur
        self.menu_cubugu_olustur()
    
    def veritabani_olustur(self):
        """Uygulamanın çalıştığı dizinde veritabanını oluşturur veya bağlanır"""
        # Uygulamanın çalıştığı dizini al
        uygulama_dizini = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        self.veritabani_yolu = os.path.join(uygulama_dizini, "siparisler.db")
        
        try:
            self.baglanti = sqlite3.connect(self.veritabani_yolu)
            self.cursor = self.baglanti.cursor()
            self.tablo_olustur()
        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası", f"Veritabanına bağlanırken hata oluştu:\n{str(e)}")
            self.root.destroy()
    
    def tablo_olustur(self):
        """Veritabanında siparişler tablosunu oluşturur veya günceller"""
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS siparisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            malzeme_adi TEXT NOT NULL,
            miktar REAL NOT NULL,
            birim TEXT NOT NULL,
            tedarikci TEXT,
            siparis_tarihi TEXT NOT NULL,
            teslim_tarihi TEXT NOT NULL,
            siparisi_veren TEXT NOT NULL,
            durum TEXT DEFAULT 'Sipariş gelmedi',
            aciklama TEXT,
            eklenme_tarihi TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Birimler tablosu
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS birimler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            birim_adi TEXT NOT NULL UNIQUE
        )
        """)
        
        # Varsayılan birimleri ekle
        varsayilan_birimler = ['Adet', 'Kg', 'Ton', 'Metre', 'Litre', 'Kutu', 'Teneke', 'Tır', 'Palet']
        for birim in varsayilan_birimler:
            try:
                self.cursor.execute("INSERT OR IGNORE INTO birimler (birim_adi) VALUES (?)", (birim,))
            except sqlite3.Error:
                pass
        
        self.baglanti.commit()
    
    def arayuz_olustur(self):
        """Uygulama arayüzünü oluşturur"""
        self.root.configure(bg=self.renkler['arkaplan'])
        
        # Ana çerçeveler
        self.ust_cerceve = tk.Frame(self.root, bg=self.renkler['cerceve'], padx=15, pady=15)
        self.ust_cerceve.pack(fill=tk.X)
        
        self.orta_cerceve = tk.Frame(self.root, bg=self.renkler['arkaplan'], padx=15, pady=10)
        self.orta_cerceve.pack(fill=tk.BOTH, expand=True)
        
        self.alt_cerceve = tk.Frame(self.root, bg=self.renkler['cerceve'], padx=15, pady=15)
        self.alt_cerceve.pack(fill=tk.X)
        
        # Üst çerçeve bileşenleri (filtreleme ve arama)
        tk.Label(self.ust_cerceve, text="Sipariş Takip Sistemi", 
                font=self.baslik_font, bg=self.renkler['cerceve'], fg=self.renkler['baslik']).grid(row=0, column=0, columnspan=3, pady=(0,10), sticky=tk.W)
        
        # Filtreleme
        tk.Label(self.ust_cerceve, text="Durum Filtresi:", 
                bg=self.renkler['cerceve'], font=self.normal_font).grid(row=1, column=0, padx=5, sticky=tk.W)
        
        self.filtre_secim = ttk.Combobox(self.ust_cerceve, values=["Tümü", "Sipariş gelmedi", "Kısmi teslimat", "Tamamı teslim alındı", "Gecikmiş"], 
                                        width=20, font=self.normal_font)
        self.filtre_secim.current(0)
        self.filtre_secim.grid(row=1, column=1, padx=5, sticky=tk.W)
        self.filtre_secim.bind("<<ComboboxSelected>>", self.siparisleri_yukle)
        
        # Tarih filtreleme
        tk.Label(self.ust_cerceve, text="Tarih Aralığı:", 
                bg=self.renkler['cerceve'], font=self.normal_font).grid(row=1, column=2, padx=5, sticky=tk.W)
        
        self.baslangic_tarih = tk.Entry(self.ust_cerceve, width=12, font=self.normal_font)
        self.baslangic_tarih.grid(row=1, column=3, padx=5, sticky=tk.W)
        self.baslangic_tarih.insert(0, "01.01.2023")
        
        tk.Label(self.ust_cerceve, text="-", 
                bg=self.renkler['cerceve'], font=self.normal_font).grid(row=1, column=4, padx=0, sticky=tk.W)
        
        self.bitis_tarih = tk.Entry(self.ust_cerceve, width=12, font=self.normal_font)
        self.bitis_tarih.grid(row=1, column=5, padx=5, sticky=tk.W)
        self.bitis_tarih.insert(0, datetime.now().strftime("%d.%m.%Y"))
        
        self.tarih_filtre_btn = tk.Button(self.ust_cerceve, text="Filtrele", command=self.siparisleri_yukle,
                                         bg=self.renkler['buton'], fg='white', font=self.buton_font,
                                         activebackground=self.renkler['buton_hover'], activeforeground='white')
        self.tarih_filtre_btn.grid(row=1, column=6, padx=5, sticky=tk.W)
        
        # Arama
        tk.Label(self.ust_cerceve, text="Ara:", 
                bg=self.renkler['cerceve'], font=self.normal_font).grid(row=1, column=7, padx=5, sticky=tk.W)
        
        self.ara_giris = tk.Entry(self.ust_cerceve, width=30, font=self.normal_font)
        self.ara_giris.grid(row=1, column=8, padx=5, sticky=tk.W)
        self.ara_giris.bind("<KeyRelease>", self.siparisleri_yukle)
        
        # Orta çerçeve (tablo)
        self.tablo_cerceve = tk.Frame(self.orta_cerceve, bg=self.renkler['arkaplan'])
        self.tablo_cerceve.pack(fill=tk.BOTH, expand=True)
        
        # Tablo
        self.tablo = ttk.Treeview(self.tablo_cerceve, columns=("siparis_no", "malzeme", "miktar_birim", "tedarikci", 
                                                             "siparis_tarihi", "teslim_tarihi", "siparisi_veren", "durum"), 
                                show="headings", style="Custom.Treeview")
        
        # Tablo sütun başlıkları
        self.tablo.heading("siparis_no", text="Sipariş No", anchor=tk.CENTER)
        self.tablo.heading("malzeme", text="Malzeme Adı", anchor=tk.CENTER)
        self.tablo.heading("miktar_birim", text="Miktar", anchor=tk.CENTER)
        self.tablo.heading("tedarikci", text="Tedarikçi", anchor=tk.CENTER)
        self.tablo.heading("siparis_tarihi", text="Sipariş Tarihi", anchor=tk.CENTER)
        self.tablo.heading("teslim_tarihi", text="Teslim Tarihi", anchor=tk.CENTER)
        self.tablo.heading("siparisi_veren", text="Siparişi Veren", anchor=tk.CENTER)
        self.tablo.heading("durum", text="Durum", anchor=tk.CENTER)
        
        # Sütun genişlikleri
        self.tablo.column("siparis_no", width=80, anchor=tk.CENTER)
        self.tablo.column("malzeme", width=180, anchor=tk.W)
        self.tablo.column("miktar_birim", width=100, anchor=tk.CENTER)
        self.tablo.column("tedarikci", width=150, anchor=tk.W)
        self.tablo.column("siparis_tarihi", width=100, anchor=tk.CENTER)
        self.tablo.column("teslim_tarihi", width=100, anchor=tk.CENTER)
        self.tablo.column("siparisi_veren", width=120, anchor=tk.CENTER)
        self.tablo.column("durum", width=150, anchor=tk.CENTER)
        
        # Tablo scrollbar
        y_scroll = ttk.Scrollbar(self.tablo_cerceve, orient=tk.VERTICAL, command=self.tablo.yview)
        self.tablo.configure(yscroll=y_scroll.set)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tablo.pack(fill=tk.BOTH, expand=True)
        
        # Tablo stil ayarları
        self.style.configure("Custom.Treeview", 
                           background=self.renkler['tablo_satir1'],
                           foreground="black",
                           rowheight=30,
                           fieldbackground=self.renkler['tablo_satir1'],
                           font=self.tablo_font,
                           bordercolor="#dddddd",
                           relief="flat")
        
        self.style.configure("Custom.Treeview.Heading", 
                           background=self.renkler['tablo_baslik'],
                           foreground="white",
                           font=self.buton_font,
                           padding=8,
                           relief="flat")
        
        self.style.map('Custom.Treeview', 
                      background=[('selected', self.renkler['vurgu'])],
                      foreground=[('selected', 'white')])
        
        # Izgara çizgileri
        self.style.configure("Custom.Treeview", rowheight=25)
        self.tablo['show'] = 'headings'
        
        # Alt çerçeve bileşenleri (butonlar)
        button_style = {'bg': self.renkler['buton'], 
                       'fg': 'white', 
                       'font': self.buton_font,
                       'activebackground': self.renkler['buton_hover'],
                       'activeforeground': 'white',
                       'relief': tk.RAISED,
                       'borderwidth': 2,
                       'padx': 12,
                       'pady': 8}
        
        self.ekle_buton = tk.Button(self.alt_cerceve, text="Yeni Sipariş Ekle", 
                                   command=self.siparis_ekle_penceresi, **button_style)
        self.ekle_buton.pack(side=tk.LEFT, padx=5)
        
        self.duzenle_buton = tk.Button(self.alt_cerceve, text="Düzenle", 
                                      command=self.siparis_duzenle, **button_style)
        self.duzenle_buton.pack(side=tk.LEFT, padx=5)
        
        self.sil_buton = tk.Button(self.alt_cerceve, text="Sil", 
                                  command=self.siparis_sil, **button_style)
        self.sil_buton.pack(side=tk.LEFT, padx=5)
        
        self.guncelle_buton = tk.Button(self.alt_cerceve, text="Durum Güncelle", 
                                       command=self.durum_guncelle_penceresi, **button_style)
        self.guncelle_buton.pack(side=tk.LEFT, padx=5)
        
        self.rapor_buton = tk.Button(self.alt_cerceve, text="Rapor Al", 
                                    command=self.rapor_al, **button_style)
        self.rapor_buton.pack(side=tk.LEFT, padx=5)
        
        self.yedek_buton = tk.Button(self.alt_cerceve, text="Yedek Al", 
                                    command=self.yedek_al, **button_style)
        self.yedek_buton.pack(side=tk.RIGHT, padx=5)
        
        self.geri_yukle_buton = tk.Button(self.alt_cerceve, text="Yedekten Geri Yükle", 
                                         command=self.yedekten_geri_yukle, **button_style)
        self.geri_yukle_buton.pack(side=tk.RIGHT, padx=5)
        
        self.cikis_buton = tk.Button(self.alt_cerceve, text="Çıkış", 
                                    command=self.root.quit, **button_style)
        self.cikis_buton.pack(side=tk.RIGHT, padx=5)
    
    def menu_cubugu_olustur(self):
        """Uygulama menü çubuğunu oluşturur"""
        menubar = tk.Menu(self.root)
        
        # Dosya menüsü
        dosya_menu = tk.Menu(menubar, tearoff=0, font=self.normal_font)
        dosya_menu.add_command(label="Yedek Al", command=self.yedek_al)
        dosya_menu.add_command(label="Yedekten Geri Yükle", command=self.yedekten_geri_yukle)
        dosya_menu.add_separator()
        dosya_menu.add_command(label="Çıkış", command=self.root.quit)
        menubar.add_cascade(label="Dosya", menu=dosya_menu)
        
        # Yardım menüsü
        yardim_menu = tk.Menu(menubar, tearoff=0, font=self.normal_font)
        yardim_menu.add_command(label="Kullanım Kılavuzu", command=self.kullanim_kilavuzu)
        yardim_menu.add_command(label="Hakkında", command=self.hakkinda)
        menubar.add_cascade(label="Yardım", menu=yardim_menu)
        
        self.root.config(menu=menubar)
    
    def siparisleri_yukle(self, event=None):
        """Veritabanından siparişleri yükler ve tabloya ekler"""
        # Tabloyu temizle
        for row in self.tablo.get_children():
            self.tablo.delete(row)
        
        # Filtreleme ve arama kriterleri
        filtre = self.filtre_secim.get()
        arama = self.ara_giris.get().lower()
        baslangic_tarih = self.baslangic_tarih.get()
        bitis_tarih = self.bitis_tarih.get()
        
        # SQL sorgusu oluştur
        sorgu = """SELECT id, malzeme_adi, miktar, birim, tedarikci, 
                  siparis_tarihi, teslim_tarihi, siparisi_veren, durum 
                  FROM siparisler"""
        kosullar = []
        
        if filtre != "Tümü":
            if filtre == "Gecikmiş":
                kosullar.append("(durum != 'Tamamı teslim alındı' AND date(teslim_tarihi) < date('now'))")
            else:
                kosullar.append(f"durum = '{filtre}'")
        
        if arama:
            kosullar.append(f"(malzeme_adi LIKE '%{arama}%' OR tedarikci LIKE '%{arama}%' OR siparisi_veren LIKE '%{arama}%')")
        
        try:
            # Tarih filtreleme
            baslangic_tarih_obj = datetime.strptime(baslangic_tarih, "%d.%m.%Y").strftime("%Y-%m-%d")
            bitis_tarih_obj = datetime.strptime(bitis_tarih, "%d.%m.%Y").strftime("%Y-%m-%d")
            kosullar.append(f"(date(siparis_tarihi) BETWEEN date('{baslangic_tarih_obj}') AND date('{bitis_tarih_obj}'))")
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz tarih formatı! Lütfen GG.AA.YYYY formatında girin.")
            return
        
        if kosullar:
            sorgu += " WHERE " + " AND ".join(kosullar)
        
        # Siparişleri veritabanından al ve tabloya ekle
        self.cursor.execute(sorgu)
        for i, siparis in enumerate(self.cursor.fetchall()):
            # Miktar ve birimi birleştir
            miktar_birim = f"{siparis[2]} {siparis[3]}"
            
            # Tarih formatını düzenle
            try:
                siparis_tarihi = datetime.strptime(siparis[5], "%Y-%m-%d").strftime("%d.%m.%Y")
                teslim_tarihi = datetime.strptime(siparis[6], "%Y-%m-%d").strftime("%d.%m.%Y")
            except:
                siparis_tarihi = siparis[5]
                teslim_tarihi = siparis[6]
            
            # Renk ayarları
            tags = ('evenrow',) if i % 2 == 0 else ('oddrow',)
            
            if siparis[8] == "Tamamı teslim alındı":
                tags += ('tamamlandi',)
            elif "Gecikmiş" in siparis[8]:
                tags += ('gecikmis',)
            elif siparis[8] == "Sipariş gelmedi":
                tags += ('gelmedi',)
            
            self.tablo.insert("", tk.END, values=(siparis[0], siparis[1], miktar_birim, siparis[4], 
                                                siparis_tarihi, teslim_tarihi, siparis[7], siparis[8]), 
                            tags=tags)
        
        # Tablo renklerini ayarla
        self.tablo.tag_configure('evenrow', background=self.renkler['tablo_satir1'])
        self.tablo.tag_configure('oddrow', background=self.renkler['tablo_satir2'])
        self.tablo.tag_configure('tamamlandi', foreground=self.renkler['basari'])
        self.tablo.tag_configure('gecikmis', foreground=self.renkler['uyari'])
        self.tablo.tag_configure('gelmedi', foreground='black')
    
    def siparis_ekle_penceresi(self):
        """Yeni sipariş ekleme penceresini açar"""
        self.ekle_penceresi = tk.Toplevel(self.root)
        self.ekle_penceresi.title("Yeni Sipariş Ekle")
        self.ekle_penceresi.geometry("500x550")
        self.ekle_penceresi.resizable(False, False)
        
        # Form bileşenleri
        tk.Label(self.ekle_penceresi, text="Sipariş Edilen Malzeme:", 
                font=self.normal_font).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.malzeme_giris = tk.Entry(self.ekle_penceresi, width=30, font=self.normal_font)
        self.malzeme_giris.grid(row=0, column=1, padx=10, pady=10)
        self.malzeme_giris.focus_set()
        
        tk.Label(self.ekle_penceresi, text="Miktar:", 
                font=self.normal_font).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        
        miktar_cerceve = tk.Frame(self.ekle_penceresi)
        miktar_cerceve.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
        
        self.miktar_giris = tk.Entry(miktar_cerceve, width=10, font=self.normal_font)
        self.miktar_giris.pack(side=tk.LEFT)
        
        # Birim seçimi
        self.birim_secim = ttk.Combobox(miktar_cerceve, width=8, font=self.normal_font)
        self.birim_secim['values'] = self.birimleri_getir()
        self.birim_secim.pack(side=tk.LEFT, padx=5)
        self.birim_secim.set('Adet')  # Varsayılan birim
        
        # Yeni birim ekle butonu
        tk.Button(miktar_cerceve, text="+", command=self.yeni_birim_ekle,
                 bg=self.renkler['buton'], fg='white', font=self.buton_font,
                 width=2).pack(side=tk.LEFT, padx=5)
        
        tk.Label(self.ekle_penceresi, text="Tedarikçi:", 
                font=self.normal_font).grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        self.tedarikci_giris = ttk.Combobox(self.ekle_penceresi, width=28, font=self.normal_font)
        self.tedarikci_giris['values'] = self.tedarikcileri_getir()
        self.tedarikci_giris.grid(row=2, column=1, padx=10, pady=10)
        
        tk.Label(self.ekle_penceresi, text="Sipariş Tarihi:", 
                font=self.normal_font).grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        self.siparis_tarihi_giris = tk.Entry(self.ekle_penceresi, width=30, font=self.normal_font)
        self.siparis_tarihi_giris.grid(row=3, column=1, padx=10, pady=10)
        self.siparis_tarihi_giris.insert(0, datetime.now().strftime("%d.%m.%Y"))
        
        tk.Label(self.ekle_penceresi, text="Teslim Edilmesi İstenen Tarih:", 
                font=self.normal_font).grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)
        self.teslim_tarihi_giris = tk.Entry(self.ekle_penceresi, width=30, font=self.normal_font)
        self.teslim_tarihi_giris.grid(row=4, column=1, padx=10, pady=10)
        self.teslim_tarihi_giris.insert(0, datetime.now().strftime("%d.%m.%Y"))
        
        tk.Label(self.ekle_penceresi, text="Siparişi Veren:", 
                font=self.normal_font).grid(row=5, column=0, padx=10, pady=10, sticky=tk.W)
        self.siparisi_veren_giris = ttk.Combobox(self.ekle_penceresi, width=28, font=self.normal_font)
        self.siparisi_veren_giris['values'] = self.siparis_verenleri_getir()
        self.siparisi_veren_giris.grid(row=5, column=1, padx=10, pady=10)
        
        tk.Label(self.ekle_penceresi, text="Açıklama:", 
                font=self.normal_font).grid(row=6, column=0, padx=10, pady=10, sticky=tk.W)
        self.aciklama_giris = tk.Text(self.ekle_penceresi, width=30, height=5, font=self.normal_font)
        self.aciklama_giris.grid(row=6, column=1, padx=10, pady=10)
        
        # Kaydet butonu
        tk.Button(self.ekle_penceresi, text="Kaydet", command=self.siparis_kaydet, 
                 bg=self.renkler['buton'], fg='white', font=self.buton_font,
                 activebackground=self.renkler['buton_hover'], activeforeground='white',
                 padx=20).grid(row=7, column=1, pady=15, sticky=tk.E)
    
    def birimleri_getir(self):
        """Veritabanındaki birim listesini getirir"""
        self.cursor.execute("SELECT birim_adi FROM birimler ORDER BY birim_adi")
        return [row[0] for row in self.cursor.fetchall()]
    
    def yeni_birim_ekle(self):
        """Yeni birim eklemek için küçük bir pencere açar"""
        birim_penceresi = tk.Toplevel(self.ekle_penceresi)
        birim_penceresi.title("Yeni Birim Ekle")
        birim_penceresi.geometry("300x100")
        
        tk.Label(birim_penceresi, text="Yeni Birim Adı:", font=self.normal_font).pack(pady=5)
        
        yeni_birim_giris = tk.Entry(birim_penceresi, width=20, font=self.normal_font)
        yeni_birim_giris.pack(pady=5)
        yeni_birim_giris.focus_set()
        
        def kaydet():
            yeni_birim = yeni_birim_giris.get().strip()
            if yeni_birim:
                try:
                    self.cursor.execute("INSERT INTO birimler (birim_adi) VALUES (?)", (yeni_birim,))
                    self.baglanti.commit()
                    self.birim_secim['values'] = self.birimleri_getir()
                    self.birim_secim.set(yeni_birim)
                    birim_penceresi.destroy()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Hata", "Bu birim zaten mevcut!")
        
        tk.Button(birim_penceresi, text="Kaydet", command=kaydet,
                 bg=self.renkler['buton'], fg='white', font=self.buton_font).pack(pady=5)
    
    def tedarikcileri_getir(self):
        """Veritabanındaki tedarikçi listesini getirir"""
        self.cursor.execute("SELECT DISTINCT tedarikci FROM siparisler WHERE tedarikci IS NOT NULL")
        return [row[0] for row in self.cursor.fetchall()]
    
    def siparis_verenleri_getir(self):
        """Veritabanındaki sipariş verenler listesini getirir"""
        self.cursor.execute("SELECT DISTINCT siparisi_veren FROM siparisler WHERE siparisi_veren IS NOT NULL")
        return [row[0] for row in self.cursor.fetchall()]
    
    def siparis_kaydet(self):
        """Yeni siparişi veritabanına kaydeder"""
        malzeme = self.malzeme_giris.get().strip()
        miktar = self.miktar_giris.get().strip()
        birim = self.birim_secim.get().strip()
        tedarikci = self.tedarikci_giris.get().strip()
        siparis_tarihi = self.siparis_tarihi_giris.get().strip()
        teslim_tarihi = self.teslim_tarihi_giris.get().strip()
        siparisi_veren = self.siparisi_veren_giris.get().strip()
        aciklama = self.aciklama_giris.get("1.0", tk.END).strip()
        
        # Zorunlu alan kontrolü
        if not malzeme or not miktar or not birim or not siparis_tarihi or not teslim_tarihi or not siparisi_veren:
            messagebox.showerror("Hata", "Lütfen zorunlu alanları doldurun!")
            return
        
        # Miktar kontrolü
        try:
            miktar = float(miktar)
            if miktar <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Hata", "Lütfen geçerli bir miktar girin!")
            return
        
        # Tarih kontrolü
        try:
            siparis_tarihi_obj = datetime.strptime(siparis_tarihi, "%d.%m.%Y")
            teslim_tarihi_obj = datetime.strptime(teslim_tarihi, "%d.%m.%Y")
            
            # Tarihleri veritabanı formatına çevir
            siparis_tarihi_db = siparis_tarihi_obj.strftime("%Y-%m-%d")
            teslim_tarihi_db = teslim_tarihi_obj.strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz tarih formatı! Lütfen GG.AA.YYYY formatında girin.")
            return
        
        try:
            self.cursor.execute("""
            INSERT INTO siparisler (malzeme_adi, miktar, birim, tedarikci, siparis_tarihi, teslim_tarihi, siparisi_veren, aciklama)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (malzeme, miktar, birim, tedarikci, siparis_tarihi_db, teslim_tarihi_db, siparisi_veren, aciklama))
            
            self.baglanti.commit()
            messagebox.showinfo("Başarılı", "Sipariş başarıyla eklendi!")
            self.ekle_penceresi.destroy()
            self.siparisleri_yukle()
        except Exception as e:
            messagebox.showerror("Hata", f"Sipariş eklenirken hata oluştu: {str(e)}")
    
    def siparis_duzenle(self):
        """Seçili siparişi düzenler"""
        secili = self.tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen düzenlemek istediğiniz siparişi seçin!")
            return
        
        siparis_id = self.tablo.item(secili[0])['values'][0]
        
        self.duzenle_penceresi = tk.Toplevel(self.root)
        self.duzenle_penceresi.title("Sipariş Düzenle")
        self.duzenle_penceresi.geometry("500x550")
        self.duzenle_penceresi.resizable(False, False)
        
        # Sipariş bilgilerini al
        self.cursor.execute("SELECT * FROM siparisler WHERE id=?", (siparis_id,))
        siparis = self.cursor.fetchone()
        
        # Miktar ve birimi ayır
        miktar = siparis[2]
        birim = siparis[3]
        
        # Tarih formatını düzenle
        try:
            siparis_tarihi = datetime.strptime(siparis[5], "%Y-%m-%d").strftime("%d.%m.%Y")
            teslim_tarihi = datetime.strptime(siparis[6], "%Y-%m-%d").strftime("%d.%m.%Y")
        except:
            siparis_tarihi = siparis[5]
            teslim_tarihi = siparis[6]
        
        # Form bileşenleri
        tk.Label(self.duzenle_penceresi, text="Sipariş Edilen Malzeme:", 
                font=self.normal_font).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.malzeme_giris_duzenle = tk.Entry(self.duzenle_penceresi, width=30, font=self.normal_font)
        self.malzeme_giris_duzenle.grid(row=0, column=1, padx=10, pady=10)
        self.malzeme_giris_duzenle.insert(0, siparis[1])
        
        tk.Label(self.duzenle_penceresi, text="Miktar:", 
                font=self.normal_font).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        
        miktar_cerceve = tk.Frame(self.duzenle_penceresi)
        miktar_cerceve.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
        
        self.miktar_giris_duzenle = tk.Entry(miktar_cerceve, width=10, font=self.normal_font)
        self.miktar_giris_duzenle.pack(side=tk.LEFT)
        self.miktar_giris_duzenle.insert(0, miktar)
        
        # Birim seçimi
        self.birim_secim_duzenle = ttk.Combobox(miktar_cerceve, width=8, font=self.normal_font)
        self.birim_secim_duzenle['values'] = self.birimleri_getir()
        self.birim_secim_duzenle.pack(side=tk.LEFT, padx=5)
        self.birim_secim_duzenle.set(birim)
        
        tk.Label(self.duzenle_penceresi, text="Tedarikçi:", 
                font=self.normal_font).grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        self.tedarikci_giris_duzenle = ttk.Combobox(self.duzenle_penceresi, width=28, font=self.normal_font)
        self.tedarikci_giris_duzenle['values'] = self.tedarikcileri_getir()
        self.tedarikci_giris_duzenle.grid(row=2, column=1, padx=10, pady=10)
        self.tedarikci_giris_duzenle.set(siparis[4] if siparis[4] else "")
        
        tk.Label(self.duzenle_penceresi, text="Sipariş Tarihi:", 
                font=self.normal_font).grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        self.siparis_tarihi_giris_duzenle = tk.Entry(self.duzenle_penceresi, width=30, font=self.normal_font)
        self.siparis_tarihi_giris_duzenle.grid(row=3, column=1, padx=10, pady=10)
        self.siparis_tarihi_giris_duzenle.insert(0, siparis_tarihi)
        
        tk.Label(self.duzenle_penceresi, text="Teslim Edilmesi İstenen Tarih:", 
                font=self.normal_font).grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)
        self.teslim_tarihi_giris_duzenle = tk.Entry(self.duzenle_penceresi, width=30, font=self.normal_font)
        self.teslim_tarihi_giris_duzenle.grid(row=4, column=1, padx=10, pady=10)
        self.teslim_tarihi_giris_duzenle.insert(0, teslim_tarihi)
        
        tk.Label(self.duzenle_penceresi, text="Siparişi Veren:", 
                font=self.normal_font).grid(row=5, column=0, padx=10, pady=10, sticky=tk.W)
        self.siparisi_veren_giris_duzenle = ttk.Combobox(self.duzenle_penceresi, width=28, font=self.normal_font)
        self.siparisi_veren_giris_duzenle['values'] = self.siparis_verenleri_getir()
        self.siparisi_veren_giris_duzenle.grid(row=5, column=1, padx=10, pady=10)
        self.siparisi_veren_giris_duzenle.set(siparis[7] if siparis[7] else "")
        
        tk.Label(self.duzenle_penceresi, text="Açıklama:", 
                font=self.normal_font).grid(row=6, column=0, padx=10, pady=10, sticky=tk.W)
        self.aciklama_giris_duzenle = tk.Text(self.duzenle_penceresi, width=30, height=5, font=self.normal_font)
        self.aciklama_giris_duzenle.grid(row=6, column=1, padx=10, pady=10)
        self.aciklama_giris_duzenle.insert(tk.END, siparis[9] if siparis[9] else "")
        
        # Kaydet butonu
        tk.Button(self.duzenle_penceresi, text="Güncelle", 
                 command=lambda: self.siparis_guncelle(siparis_id),
                 bg=self.renkler['buton'], fg='white', font=self.buton_font,
                 activebackground=self.renkler['buton_hover'], activeforeground='white',
                 padx=20).grid(row=7, column=1, pady=15, sticky=tk.E)
    
    def siparis_guncelle(self, siparis_id):
        """Sipariş bilgilerini günceller"""
        malzeme = self.malzeme_giris_duzenle.get().strip()
        miktar = self.miktar_giris_duzenle.get().strip()
        birim = self.birim_secim_duzenle.get().strip()
        tedarikci = self.tedarikci_giris_duzenle.get().strip()
        siparis_tarihi = self.siparis_tarihi_giris_duzenle.get().strip()
        teslim_tarihi = self.teslim_tarihi_giris_duzenle.get().strip()
        siparisi_veren = self.siparisi_veren_giris_duzenle.get().strip()
        aciklama = self.aciklama_giris_duzenle.get("1.0", tk.END).strip()
        
        # Zorunlu alan kontrolü
        if not malzeme or not miktar or not birim or not siparis_tarihi or not teslim_tarihi or not siparisi_veren:
            messagebox.showerror("Hata", "Lütfen zorunlu alanları doldurun!")
            return
        
        # Miktar kontrolü
        try:
            miktar = float(miktar)
            if miktar <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Hata", "Lütfen geçerli bir miktar girin!")
            return
        
        # Tarih kontrolü
        try:
            siparis_tarihi_obj = datetime.strptime(siparis_tarihi, "%d.%m.%Y")
            teslim_tarihi_obj = datetime.strptime(teslim_tarihi, "%d.%m.%Y")
            
            # Tarihleri veritabanı formatına çevir
            siparis_tarihi_db = siparis_tarihi_obj.strftime("%Y-%m-%d")
            teslim_tarihi_db = teslim_tarihi_obj.strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz tarih formatı! Lütfen GG.AA.YYYY formatında girin.")
            return
        
        try:
            self.cursor.execute("""
            UPDATE siparisler 
            SET malzeme_adi=?, miktar=?, birim=?, tedarikci=?, siparis_tarihi=?, 
                teslim_tarihi=?, siparisi_veren=?, aciklama=?
            WHERE id=?
            """, (malzeme, miktar, birim, tedarikci, siparis_tarihi_db, 
                 teslim_tarihi_db, siparisi_veren, aciklama, siparis_id))
            
            self.baglanti.commit()
            messagebox.showinfo("Başarılı", "Sipariş başarıyla güncellendi!")
            self.duzenle_penceresi.destroy()
            self.siparisleri_yukle()
        except Exception as e:
            messagebox.showerror("Hata", f"Sipariş güncellenirken hata oluştu: {str(e)}")
    
    def siparis_sil(self):
        """Seçili siparişi siler"""
        secili = self.tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz siparişi seçin!")
            return
        
        siparis_id = self.tablo.item(secili[0])['values'][0]
        malzeme_adi = self.tablo.item(secili[0])['values'][1]
        
        onay = messagebox.askyesno("Onay", f"'{malzeme_adi}' adlı siparişi silmek istediğinize emin misiniz?")
        if not onay:
            return
        
        try:
            self.cursor.execute("DELETE FROM siparisler WHERE id=?", (siparis_id,))
            self.baglanti.commit()
            messagebox.showinfo("Başarılı", "Sipariş başarıyla silindi!")
            self.siparisleri_yukle()
        except Exception as e:
            messagebox.showerror("Hata", f"Sipariş silinirken hata oluştu: {str(e)}")
    
    def durum_guncelle_penceresi(self):
        """Sipariş durumunu güncelleme penceresini açar"""
        secili = self.tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen durumunu güncellemek istediğiniz siparişi seçin!")
            return
        
        siparis = self.tablo.item(secili[0])['values']
        siparis_id = siparis[0]
        mevcut_durum = siparis[7]
        malzeme_adi = siparis[1]
        
        self.durum_penceresi = tk.Toplevel(self.root)
        self.durum_penceresi.title(f"Durum Güncelle - {malzeme_adi}")
        self.durum_penceresi.geometry("400x250")
        self.durum_penceresi.resizable(False, False)
        
        # Durum seçimi
        tk.Label(self.durum_penceresi, text="Yeni Durum:", font=self.normal_font).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.durum_secim = ttk.Combobox(self.durum_penceresi, 
                                      values=["Sipariş gelmedi", "Tamamı teslim alındı", "Kısmi teslimat", "Gecikmiş"],
                                      font=self.normal_font)
        self.durum_secim.grid(row=0, column=1, padx=10, pady=10)
        self.durum_secim.set(mevcut_durum)
        
        # Kısmi teslimat miktarı (gerekirse)
        self.kismi_miktar_etiketi = tk.Label(self.durum_penceresi, text="Teslim Edilen Miktar:", font=self.normal_font)
        self.kismi_miktar_giris = tk.Entry(self.durum_penceresi, width=15, font=self.normal_font)
        
        # Teslim tarihi (gerekirse)
        self.teslim_tarihi_etiketi = tk.Label(self.durum_penceresi, text="Teslim Tarihi:", font=self.normal_font)
        self.teslim_tarihi_giris = tk.Entry(self.durum_penceresi, width=15, font=self.normal_font)
        self.teslim_tarihi_giris.insert(0, datetime.now().strftime("%d.%m.%Y"))
        
        self.durum_secim.bind("<<ComboboxSelected>>", self.durum_secim_degisti)
        
        # Kaydet butonu
        tk.Button(self.durum_penceresi, text="Güncelle", 
                 command=lambda: self.durum_guncelle(siparis_id),
                 bg=self.renkler['buton'], fg='white', font=self.buton_font,
                 activebackground=self.renkler['buton_hover'], activeforeground='white',
                 padx=20).grid(row=3, column=1, pady=15, sticky=tk.E)
    
    def durum_secim_degisti(self, event):
        """Durum seçimine göre ek alanları gösterir/gizler"""
        if self.durum_secim.get() == "Kısmi teslimat":
            self.kismi_miktar_etiketi.grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
            self.kismi_miktar_giris.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
            self.teslim_tarihi_etiketi.grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
            self.teslim_tarihi_giris.grid(row=2, column=1, padx=10, pady=5, sticky=tk.W)
        elif self.durum_secim.get() == "Tamamı teslim alındı":
            self.kismi_miktar_etiketi.grid_remove()
            self.kismi_miktar_giris.grid_remove()
            self.teslim_tarihi_etiketi.grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
            self.teslim_tarihi_giris.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
        else:
            self.kismi_miktar_etiketi.grid_remove()
            self.kismi_miktar_giris.grid_remove()
            self.teslim_tarihi_etiketi.grid_remove()
            self.teslim_tarihi_giris.grid_remove()
    
    def durum_guncelle(self, siparis_id):
        """Sipariş durumunu günceller"""
        yeni_durum = self.durum_secim.get()
        teslim_tarihi = None
        
        if yeni_durum == "Kısmi teslimat":
            teslim_miktar = self.kismi_miktar_giris.get()
            teslim_tarihi = self.teslim_tarihi_giris.get()
            
            if not teslim_miktar:
                messagebox.showerror("Hata", "Lütfen teslim miktarını girin!")
                return
            
            try:
                teslim_miktar = float(teslim_miktar)
                if teslim_miktar <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Hata", "Lütfen geçerli bir miktar girin!")
                return
            
            yeni_durum = f"Kısmi teslimat ({teslim_miktar})"
        
        elif yeni_durum == "Tamamı teslim alındı":
            teslim_tarihi = self.teslim_tarihi_giris.get()
        
        # Tarih kontrolü
        try:
            teslim_tarihi_db = datetime.strptime(teslim_tarihi, "%d.%m.%Y").strftime("%Y-%m-%d") if teslim_tarihi else None
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz tarih formatı! Lütfen GG.AA.YYYY formatında girin.")
            return
        
        try:
            self.cursor.execute("UPDATE siparisler SET durum=?, teslim_tarihi=? WHERE id=?", 
                              (yeni_durum, teslim_tarihi_db, siparis_id))
            self.baglanti.commit()
            messagebox.showinfo("Başarılı", "Durum başarıyla güncellendi!")
            self.durum_penceresi.destroy()
            self.siparisleri_yukle()
        except Exception as e:
            messagebox.showerror("Hata", f"Durum güncellenirken hata oluştu: {str(e)}")
    
    def rapor_al(self):
        """Sipariş raporu oluşturur"""
        secili = self.tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen rapor almak istediğiniz siparişi seçin!")
            return
        
        siparis_id = self.tablo.item(secili[0])['values'][0]
        
        # Sipariş bilgilerini al
        self.cursor.execute("SELECT * FROM siparisler WHERE id=?", (siparis_id,))
        siparis = self.cursor.fetchone()
        
        # Tarih formatını düzenle
        try:
            siparis_tarihi = datetime.strptime(siparis[5], "%Y-%m-%d").strftime("%d.%m.%Y")
            teslim_tarihi = datetime.strptime(siparis[6], "%Y-%m-%d").strftime("%d.%m.%Y")
        except:
            siparis_tarihi = siparis[5]
            teslim_tarihi = siparis[6]
        
        # Rapor penceresi
        rapor_penceresi = tk.Toplevel(self.root)
        rapor_penceresi.title(f"Sipariş Raporu - ID: {siparis_id}")
        rapor_penceresi.geometry("600x500")
        
        # Rapor içeriği
        rapor_metni = f"""
        SIPARIŞ RAPORU
        ==============
        
        Sipariş No: {siparis[0]}
        Malzeme Adı: {siparis[1]}
        Miktar: {siparis[2]} {siparis[3]}
        Tedarikçi: {siparis[4] if siparis[4] else "Belirtilmemiş"}
        Sipariş Tarihi: {siparis_tarihi}
        Teslim Tarihi: {teslim_tarihi}
        Siparişi Veren: {siparis[7]}
        Durum: {siparis[8]}
        
        Açıklama:
        {siparis[9] if siparis[9] else "Açıklama girilmemiş"}
        """
        
        rapor_text = tk.Text(rapor_penceresi, wrap=tk.WORD, font=self.normal_font)
        rapor_text.insert(tk.END, rapor_metni)
        rapor_text.config(state=tk.DISABLED)
        rapor_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Butonlar
        buton_cerceve = tk.Frame(rapor_penceresi)
        buton_cerceve.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(buton_cerceve, text="Yazdır", 
                command=lambda: self.rapor_yazdir(rapor_metni),
                bg=self.renkler['buton'], fg='white', font=self.buton_font).pack(side=tk.LEFT, padx=5)
        
        tk.Button(buton_cerceve, text="Dosyaya Kaydet", 
                command=lambda: self.rapor_kaydet(rapor_metni),
                bg=self.renkler['buton'], fg='white', font=self.buton_font).pack(side=tk.LEFT, padx=5)
        
        tk.Button(buton_cerceve, text="Kapat", 
                command=rapor_penceresi.destroy,
                bg=self.renkler['buton'], fg='white', font=self.buton_font).pack(side=tk.RIGHT, padx=5)
    
    def rapor_yazdir(self, rapor_metni):
        """Raporu yazdırma işlemini simüle eder"""
        messagebox.showinfo("Yazdır", "Rapor yazdırma işlemi başlatıldı (simülasyon).")
    
    def rapor_kaydet(self, rapor_metni):
        """Raporu dosyaya kaydeder"""
        dosya_yolu = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text Dosyası", "*.txt"),
                                                            ("Tüm Dosyalar", "*.*")],
                                                 title="Raporu Kaydet")
        if dosya_yolu:
            try:
                with open(dosya_yolu, 'w', encoding='utf-8') as f:
                    f.write(rapor_metni)
                messagebox.showinfo("Başarılı", f"Rapor başarıyla kaydedildi:\n{dosya_yolu}")
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya kaydedilirken hata oluştu: {str(e)}")
    
    def yedek_al(self):
        """Veritabanı yedeği alır"""
        dosya_yolu = filedialog.asksaveasfilename(defaultextension=".db",
                                                 filetypes=[("Veritabanı Dosyası", "*.db"),
                                                            ("Tüm Dosyalar", "*.*")],
                                                 title="Yedek Dosyasını Kaydet")
        if dosya_yolu:
            try:
                # Mevcut veritabanını kopyala
                with open(self.veritabani_yolu, 'rb') as f:
                    veri = f.read()
                with open(dosya_yolu, 'wb') as f:
                    f.write(veri)
                messagebox.showinfo("Başarılı", f"Yedek başarıyla alındı:\n{dosya_yolu}")
            except Exception as e:
                messagebox.showerror("Hata", f"Yedek alınırken hata oluştu: {str(e)}")
    
    def yedekten_geri_yukle(self):
        """Yedekten geri yükleme yapar"""
        dosya_yolu = filedialog.askopenfilename(filetypes=[("Veritabanı Dosyası", "*.db"),
                                                         ("Tüm Dosyalar", "*.*")],
                                              title="Yedek Dosyasını Seçin")
        if dosya_yolu:
            onay = messagebox.askyesno("Onay", "Yedekten geri yükleme yapılacak. Mevcut verilerin üzerine yazılacak. Devam etmek istiyor musunuz?")
            if not onay:
                return
            
            try:
                # Önce mevcut veritabanını kapat
                self.baglanti.close()
                
                # Yedek dosyayı kopyala
                with open(dosya_yolu, 'rb') as f:
                    veri = f.read()
                with open(self.veritabani_yolu, 'wb') as f:
                    f.write(veri)
                
                # Veritabanını yeniden aç
                self.baglanti = sqlite3.connect(self.veritabani_yolu)
                self.cursor = self.baglanti.cursor()
                
                messagebox.showinfo("Başarılı", "Yedek başarıyla geri yüklendi!")
                self.siparisleri_yukle()
            except Exception as e:
                messagebox.showerror("Hata", f"Geri yükleme sırasında hata oluştu: {str(e)}")
                # Hata durumunda veritabanını yeniden açmaya çalış
                try:
                    self.baglanti = sqlite3.connect(self.veritabani_yolu)
                    self.cursor = self.baglanti.cursor()
                except:
                    messagebox.showerror("Kritik Hata", "Veritabanına bağlanılamadı. Uygulama kapatılacak.")
                    self.root.destroy()
    
    def kullanim_kilavuzu(self):
        """Kullanım kılavuzunu gösterir"""
        kilavuz_metni = """
        SIPARIŞ TAKİP UYGULAMASI KULLANIM KILAVUZU
        
        1. Yeni Sipariş Ekleme:
           - "Yeni Sipariş Ekle" butonuna tıklayın
           - Gerekli bilgileri doldurun
           - "Kaydet" butonuna basın
        
        2. Sipariş Düzenleme:
           - Tablodan bir sipariş seçin
           - "Düzenle" butonuna tıklayın
           - Bilgileri güncelleyin
           - "Güncelle" butonuna basın
        
        3. Sipariş Silme:
           - Tablodan bir sipariş seçin
           - "Sil" butonuna tıklayın
           - Onay verin
        
        4. Durum Güncelleme:
           - Tablodan bir sipariş seçin
           - "Durum Güncelle" butonuna tıklayın
           - Yeni durumu seçin
           - "Güncelle" butonuna basın
        
        5. Filtreleme ve Arama:
           - Üst kısımdaki filtre ve arama alanlarını kullanın
        
        6. Rapor Alma:
           - Tablodan bir sipariş seçin
           - "Rapor Al" butonuna tıklayın
           - Yazdırma veya kaydetme seçeneklerini kullanın
        
        7. Yedekleme:
           - "Yedek Al" butonu ile veritabanı yedeği alın
           - "Yedekten Geri Yükle" butonu ile yedekten geri yükleme yapın
        """
        
        kilavuz_penceresi = tk.Toplevel(self.root)
        kilavuz_penceresi.title("Kullanım Kılavuzu")
        kilavuz_penceresi.geometry("600x500")
        
        text = tk.Text(kilavuz_penceresi, wrap=tk.WORD, font=self.normal_font)
        text.insert(tk.END, kilavuz_metni)
        text.config(state=tk.DISABLED)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Button(kilavuz_penceresi, text="Kapat", command=kilavuz_penceresi.destroy,
                bg=self.renkler['buton'], fg='white', font=self.buton_font).pack(pady=10)
    
    def hakkinda(self):
        """Hakkında penceresini gösterir"""
        hakkinda_metni = """
        Sipariş Takip Uygulaması
        
        Versiyon: 2.0
        Geliştirici: XYZ Yazılım
        
        © 2023 Tüm hakları saklıdır.
        
        Bu uygulama, şirket içi sipariş takibi
        için geliştirilmiştir.
        """
        
        messagebox.showinfo("Hakkında", hakkinda_metni)

if __name__ == "__main__":
    root = tk.Tk()
    app = SiparisTakipUygulamasi(root)
    root.mainloop()
