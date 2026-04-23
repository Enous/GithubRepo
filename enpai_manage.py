#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EnpaiManage - GitHub Repo Yöneticisi
Developed by Enous (Enpai Dev)
"""

import sys
import os
import json
import subprocess
import re
import argparse
import io
import urllib.request
import urllib.error
import shutil
import ctypes
import stat
from datetime import datetime
from pathlib import Path

# Windows UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ──────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────

CONFIG_DIR  = Path.home() / ".config" / "enpaimanage"
CONFIG_FILE = CONFIG_DIR / "config.json"

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(cfg, f, ensure_ascii=False, indent=2)

# ──────────────────────────────────────────
# HELPERS & AI LOGIC
# ──────────────────────────────────────────

def fetch_repo_info(owner, repo, token=None):
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "EnpaiManage"}
    if token and token.strip(): headers["Authorization"] = f"token {token.strip()}"
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
        with urllib.request.urlopen(req) as resp: return json.loads(resp.read().decode())
    except:
        return {"full_name": f"{owner}/{repo}", "description": None, "clone_url": f"https://github.com/{owner}/{repo}.git"}

def detect_category(info):
    rules = {
        "AI-ML": ["machine-learning", "deep-learning", "neural", "llm", "ai", "gpt"],
        "Security": ["security", "pentest", "hacking", "exploit", "osint"],
        "Web": ["javascript", "typescript", "react", "vue", "html", "css", "web"],
        "Tools": ["tool", "cli", "automation", "script"],
        "Python": ["python", "django", "flask"],
    }
    desc = (info.get("description") or "").lower()
    lang = (info.get("language") or "").lower()
    text = desc + " " + lang
    for cat, kws in rules.items():
        if any(kw in text for kw in kws): return cat
    return "Other"

def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE); func(path)

def get_folder_size(path):
    total = 0
    try:
        p = Path(path)
        if not p.exists(): return 0
        for f in p.rglob('*'):
            if f.is_file(): total += f.stat().size
    except: pass
    return total

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024: return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

def groq_analyze(path, api_key):
    """Analyze repo content using Groq AI."""
    try:
        files_summary = []
        important_files = ["README.md", "main.py", "app.py", "index.js", "package.json", "requirements.txt", "enpai_manage.py"]
        total_chars = 0
        max_chars = 8000
        for f_name in important_files:
            f_path = Path(path) / f_name
            if f_path.exists() and total_chars < max_chars:
                with open(f_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(1500); total_chars += len(content)
                    files_summary.append(f"--- {f_name} ---\n{content}")
        if not files_summary:
            all_files = [f.name for f in Path(path).glob("*") if f.is_file()][:10]
            files_summary.append("Dosya Listesi: " + ", ".join(all_files))
        prompt = f"Aşağıdaki GitHub reposunu analiz et ve ne işe yaradığını, hangi teknolojileri kullandığını kısaca Türkçe olarak açıkla:\n\n" + "\n".join(files_summary)
        data = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
        req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        try: body = e.read().decode("utf-8"); error_msg = json.loads(body).get("error", {}).get("message", body)
        except: error_msg = str(e)
        return f"Analiz hatası: {error_msg}"
    except Exception as e: return f"Analiz hatası: {str(e)}"

# ──────────────────────────────────────────
# GUI (PyQt6)
# ──────────────────────────────────────────

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                 QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem, 
                                 QFileDialog, QStackedWidget, QProgressBar, QDialog, QTextEdit, 
                                 QMessageBox, QPlainTextEdit, QComboBox)
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt6.QtGui import QColor, QFont

    STYLE = """
    QMainWindow { background-color: #020617; }
    QWidget#Sidebar { background-color: #0f172a; border-right: 1px solid #1e293b; }
    QLabel { color: #f8fafc; font-family: 'Segoe UI'; }
    QLineEdit, QPlainTextEdit, QTextEdit, QComboBox { 
        background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; 
        color: white; padding: 10px; font-size: 13px;
    }
    QComboBox QAbstractItemView { background-color: #1e293b; color: white; selection-background-color: #38bdf8; }
    QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #38bdf8; }
    QPushButton { background-color: #0ea5e9; color: white; border-radius: 8px; padding: 10px; font-weight: bold; }
    QPushButton:hover { background-color: #0284c7; }
    QPushButton#Danger { background-color: #ef4444; }
    QPushButton#Secondary { background-color: #334155; }
    QPushButton#Action { background-color: #10b981; }
    QPushButton#AI { background-color: #8b5cf6; }
    
    QListWidget { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; }
    QListWidget::item { background-color: #1e293b; border-radius: 10px; padding: 15px; margin: 5px; }
    QProgressBar { border: 1px solid #334155; border-radius: 6px; text-align: center; color: white; font-weight: bold; }
    QProgressBar::chunk { background-color: #38bdf8; border-radius: 4px; }
    """

    class StatsWorker(QThread):
        stats_ready = pyqtSignal(dict)
        def __init__(self, owner, repo, token):
            super().__init__()
            self.owner, self.repo, self.token = owner, repo, token
        def run(self):
            info = fetch_repo_info(self.owner, self.repo, self.token)
            self.stats_ready.emit(info)

    class DetailsDialog(QDialog):
        repoChanged = pyqtSignal()
        def __init__(self, repo_data, config, parent=None):
            super().__init__(parent); self.setWindowTitle("Repo Detayları"); self.setFixedSize(550, 700); self.setStyleSheet(STYLE)
            self.data, self.cfg = repo_data, config; self.init_ui()
        def init_ui(self):
            layout = QVBoxLayout(self)
            header = QLabel(self.data['name']); header.setStyleSheet("font-size: 20px; font-weight: bold; color: #38bdf8;"); layout.addWidget(header)
            s = format_size(get_folder_size(self.data['path']))
            layout.addWidget(QLabel(f"📂 Kategori: {self.data['category']}  |  💾 Boyut: {s}"))
            
            self.stats_lbl = QLabel("📊 İstatistikler yükleniyor...")
            self.stats_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: bold; background-color: #1e293b; padding: 10px; border-radius: 8px;")
            self.stats_lbl.setWordWrap(True)
            layout.addWidget(self.stats_lbl)
            
            self.desc = QTextEdit(); self.desc.setReadOnly(True); self.desc.setText(self.data.get('description') or "Açıklama yok."); layout.addWidget(self.desc)
            
            # Fetch stats
            try:
                owner, repo = self.data['name'].split('/')[-2:]
                self.stats_worker = StatsWorker(owner, repo, self.cfg.get("token"))
                self.stats_worker.stats_ready.connect(self.update_stats)
                self.stats_worker.start()
            except Exception as e:
                self.stats_lbl.setText("⚠️ Depo bilgisi okunamadı.")

            if self.cfg.get("groq_key"):
                self.btn_ai = QPushButton("🤖 Yapay Zeka ile Analiz Et (Groq)"); self.btn_ai.setObjectName("AI"); self.btn_ai.clicked.connect(self.start_ai_analyze); layout.addWidget(self.btn_ai)
            row1 = QHBoxLayout()
            b_open = QPushButton("Klasörü Aç"); b_open.clicked.connect(lambda: os.startfile(self.data['path'])); row1.addWidget(b_open)
            b_code = QPushButton("VS Code'da Aç"); b_code.setObjectName("Action"); b_code.clicked.connect(self.open_vscode); row1.addWidget(b_code); layout.addLayout(row1)
            row2 = QHBoxLayout()
            b_up = QPushButton("Güncelle (Git Pull)"); b_up.clicked.connect(self.update_repo); row2.addWidget(b_up)
            b_del = QPushButton("Sil"); b_del.setObjectName("Danger"); b_del.clicked.connect(self.delete_repo); row2.addWidget(b_del); layout.addLayout(row2)
            b_c = QPushButton("Kapat"); b_c.setObjectName("Secondary"); b_c.clicked.connect(self.close); layout.addWidget(b_c)
            
        def update_stats(self, info):
            if "id" in info:
                stars = info.get("stargazers_count", 0)
                forks = info.get("forks_count", 0)
                watchers = info.get("watchers_count", 0)
                issues = info.get("open_issues_count", 0)
                lang = info.get("language", "Bilinmiyor")
                lic = info.get("license", {}).get("name", "Yok") if info.get("license") else "Yok"
                
                text = (f"⭐ Yıldız: {stars}  |  🍴 Fork: {forks}  |  👀 İzleyen: {watchers}\n"
                        f"🐛 Açık Issue: {issues}  |  💻 Dil: {lang}  |  📜 Lisans: {lic}")
                self.stats_lbl.setText(text)
                self.stats_lbl.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: bold; background-color: #0f172a; border: 1px solid #334155; padding: 10px; border-radius: 8px;")
            else:
                self.stats_lbl.setText("⚠️ İstatistikler çekilemedi (API Sınırı veya Gizli Repo)")
                
        def start_ai_analyze(self):
            self.desc.setText("Analiz ediliyor..."); self.btn_ai.setEnabled(False); QApplication.processEvents()
            self.desc.setText(groq_analyze(self.data['path'], self.cfg['groq_key'])); self.btn_ai.setEnabled(True)
        def open_vscode(self):
            try: subprocess.Popen(["code", self.data['path']], shell=True)
            except: QMessageBox.warning(self, "Hata", "VS Code bulunamadı.")
        def update_repo(self):
            try:
                res = subprocess.run(["git", "pull"], cwd=self.data['path'], capture_output=True, text=True)
                QMessageBox.information(self, "Bilgi", "Başarılı" if res.returncode==0 else res.stderr)
            except Exception as e: QMessageBox.critical(self, "Hata", str(e))
        def delete_repo(self):
            if QMessageBox.question(self, "Onay", "Silinsin mi?", QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                if os.path.exists(self.data['path']): shutil.rmtree(self.data['path'], onerror=remove_readonly)
                r_dir = Path(self.cfg.get("repos_dir", str(Path.home() / "EnpaiRepos")))
                rec_file = r_dir / "repos.json"
                if rec_file.exists():
                    with open(rec_file, "r", encoding="utf-8") as f: recs = json.load(f)
                    with open(rec_file, "w", encoding="utf-8") as f: json.dump([r for r in recs if r['path']!=self.data['path']], f, indent=2, ensure_ascii=False)
                self.repoChanged.emit(); self.close()

    class MultiWorker(QThread):
        finished = pyqtSignal(bool, str); progress = pyqtSignal(str); percent = pyqtSignal(int)
        def __init__(self, urls, token, base_dir):
            super().__init__(); self.urls, self.token, self.base_dir = urls, token, Path(base_dir)
        def run(self):
            total = len(self.urls); success = 0
            for i, url in enumerate(self.urls):
                url = url.strip(); 
                if not url: continue
                self.progress.emit(f"({i+1}/{total}) {url}"); self.percent.emit(int((i/total)*100))
                try:
                    match = re.search(r"github\.com[:/]([^/]+)/([^/\.]+)", url)
                    if not match: continue
                    owner, repo_name = match.groups(); repo_name = repo_name.replace(".git", "")
                    info = fetch_repo_info(owner, repo_name, self.token); cat = detect_category(info); target = self.base_dir / cat / repo_name
                    if target.exists(): continue
                    target.mkdir(parents=True, exist_ok=True)
                    c_url = info.get("clone_url", url)
                    if self.token: c_url = c_url.replace("https://", f"https://{self.token.strip()}@")
                    if subprocess.run(["git", "clone", "--depth", "1", c_url, str(target)], capture_output=True, text=True).returncode == 0:
                        success += 1; d = info.get('description') or "Açıklama yok."
                        with open(target / "info.txt", "w", encoding="utf-8") as f: f.write(f"Repo: {info.get('full_name')}\n{d}\n")
                        rec_file = self.base_dir / "repos.json"; recs = []
                        if rec_file.exists():
                            with open(rec_file, "r", encoding="utf-8") as f: recs = json.load(f)
                        recs.append({"name": info.get("full_name"), "category": cat, "path": str(target), "description": d, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
                        with open(rec_file, "w", encoding="utf-8") as f: json.dump(recs, f, indent=2, ensure_ascii=False)
                except: pass
            self.percent.emit(100); self.finished.emit(True, f"{success} repo indirildi.")

    class EnpaiGUI(QMainWindow):
        def __init__(self):
            super().__init__(); self.setWindowTitle("EnpaiManage (Enpai Dev)"); self.resize(1100, 800); self.setStyleSheet(STYLE)
            self.cfg = load_config(); self.records = []; self.init_ui(); self.load_repos()
            self.timer = QTimer(); self.timer.timeout.connect(self.sync_with_fs); self.timer.start(5000)

        def init_ui(self):
            central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)
            sidebar = QWidget(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(220); side_lay = QVBoxLayout(sidebar)
            logo = QLabel("ENPAI DEV"); logo.setStyleSheet("font-size: 24px; font-weight: bold; color: #38bdf8; margin: 25px;"); side_lay.addWidget(logo)
            b1 = QPushButton("📂 Repolar"); b1.clicked.connect(lambda: self.stack.setCurrentIndex(0)); side_lay.addWidget(b1)
            b2 = QPushButton("⚙️ Ayarlar"); b2.clicked.connect(lambda: self.stack.setCurrentIndex(1)); side_lay.addWidget(b2)
            side_lay.addStretch()
            b_gen = QPushButton("📝 Profil README"); b_gen.setObjectName("Action"); b_gen.clicked.connect(self.gen_readme); side_lay.addWidget(b_gen)
            side_lay.addWidget(QLabel("By Enous")); layout.addWidget(sidebar)
            self.stack = QStackedWidget(); layout.addWidget(self.stack)
            # P1
            p1 = QWidget(); p1_lay = QVBoxLayout(p1); p1_lay.setContentsMargins(40,40,40,40)
            p1_lay.addWidget(QLabel("GitHub Linkleri")); self.url_in = QPlainTextEdit(); self.url_in.setFixedHeight(100); p1_lay.addWidget(self.url_in)
            btn = QPushButton("İndir"); btn.clicked.connect(self.start_clone); p1_lay.addWidget(btn)
            self.status = QLabel("Hazır."); p1_lay.addWidget(self.status)
            self.prog = QProgressBar(); self.prog.setVisible(False); p1_lay.addWidget(self.prog)
            p1_lay.addSpacing(20); p1_lay.addWidget(QLabel("Repo Koleksiyonu"))
            search_lay = QHBoxLayout(); self.search_in = QLineEdit(); self.search_in.setPlaceholderText("İsme göre ara..."); self.search_in.textChanged.connect(self.filter_list); search_lay.addWidget(self.search_in)
            self.cat_filter = QComboBox(); self.cat_filter.addItems(["Tümü", "AI-ML", "Security", "Web", "Tools", "Python", "Other"]); self.cat_filter.currentTextChanged.connect(self.filter_list); search_lay.addWidget(self.cat_filter)
            p1_lay.addLayout(search_lay)
            self.list = QListWidget(); self.list.itemClicked.connect(self.show_details); p1_lay.addWidget(self.list)
            self.path_lbl = QLabel(""); self.path_lbl.setStyleSheet("color: #64748b; font-size: 11px;"); p1_lay.addWidget(self.path_lbl)
            self.stack.addWidget(p1)
            # P2
            p2 = QWidget(); p2_lay = QVBoxLayout(p2); p2_lay.setContentsMargins(40,40,40,40)
            p2_lay.addWidget(QLabel("GitHub Token")); self.t_ed = QLineEdit(); self.t_ed.setEchoMode(QLineEdit.EchoMode.Password); self.t_ed.setText(self.cfg.get("token","")); p2_lay.addWidget(self.t_ed)
            p2_lay.addWidget(QLabel("Groq API Key")); self.g_ed = QLineEdit(); self.g_ed.setEchoMode(QLineEdit.EchoMode.Password); self.g_ed.setText(self.cfg.get("groq_key","")); p2_lay.addWidget(self.g_ed)
            p2_lay.addWidget(QLabel("Klasör")); d_box = QHBoxLayout(); self.d_ed = QLineEdit(); self.d_ed.setText(self.cfg.get("repos_dir","")); d_box.addWidget(self.d_ed)
            b_br = QPushButton("Seç"); b_br.setObjectName("Secondary"); b_br.clicked.connect(self.browse); d_box.addWidget(b_br); p2_lay.addLayout(d_box)
            b_sv = QPushButton("Kaydet"); b_sv.clicked.connect(self.save_sets); p2_lay.addWidget(b_sv); p2_lay.addStretch(); self.stack.addWidget(p2)

        def gen_readme(self):
            if not self.records: return
            md = "# 🌌 My Repository Collection\n\nGenerated by Enous / Enpai Dev\n\n"
            cats = {}
            for r in self.records:
                c = r['category']
                if c not in cats: cats[c] = []
                cats[c].append(r)
            for c, rs in cats.items():
                md += f"### 📂 {c}\n"
                for r in rs: md += f"- **[{r['name']}](https://github.com/{r['name']})**: {r.get('description','No description')}\n"
                md += "\n"
            save_p, _ = QFileDialog.getSaveFileName(self, "README Kaydet", "", "Markdown Files (*.md)")
            if save_p:
                with open(save_p, "w", encoding="utf-8") as f: f.write(md)
                QMessageBox.information(self, "Başarılı", "Profil README dosyası oluşturuldu!")

        def browse(self):
            p = QFileDialog.getExistingDirectory(self, "Klasör Seç", self.d_ed.text())
            if p: self.d_ed.setText(p)

        def save_sets(self):
            self.cfg["token"], self.cfg["repos_dir"], self.cfg["groq_key"] = self.t_ed.text().strip(), self.d_ed.text(), self.g_ed.text().strip(); save_config(self.cfg); self.stack.setCurrentIndex(0); self.load_repos()

        def load_repos(self):
            r_dir = Path(self.cfg.get("repos_dir", str(Path.home() / "EnpaiRepos")))
            self.path_lbl.setText(f"Aktif Klasör: {r_dir}")
            if (r_dir / "repos.json").exists():
                with open(r_dir / "repos.json", "r", encoding="utf-8") as f: self.records = json.load(f)
            else: self.records = []
            self.sync_with_fs(refresh=False); self.filter_list()

        def sync_with_fs(self, refresh=True):
            if not self.records: return
            valid = [r for r in self.records if os.path.exists(r['path'])]
            if len(valid) != len(self.records):
                self.records = valid
                r_dir = Path(self.cfg.get("repos_dir", str(Path.home() / "EnpaiRepos")))
                with open(r_dir / "repos.json", "w", encoding="utf-8") as f: json.dump(self.records, f, indent=2, ensure_ascii=False)
                if refresh: self.filter_list()

        def filter_list(self):
            self.list.clear(); search = self.search_in.text().lower(); cat = self.cat_filter.currentText()
            for r in reversed(self.records):
                if (search in r['name'].lower()) and (cat == "Tümü" or r['category'] == cat):
                    it = QListWidgetItem(f"📦 {r['name']}\n📁 {r['category']}  |  📅 {r['date']}"); it.setData(Qt.ItemDataRole.UserRole, r); self.list.addItem(it)

        def show_details(self, it):
            d = DetailsDialog(it.data(Qt.ItemDataRole.UserRole), self.cfg, self); d.repoChanged.connect(self.load_repos); d.exec()

        def start_clone(self):
            urls = [u for u in self.url_in.toPlainText().split('\n') if u.strip()]
            if not urls: return
            self.prog.setVisible(True); self.worker = MultiWorker(urls, self.cfg.get("token"), self.cfg.get("repos_dir"))
            self.worker.progress.connect(self.status.setText); self.worker.percent.connect(self.prog.setValue)
            self.worker.finished.connect(self.on_done); self.worker.start()

        def on_done(self, s, m): self.prog.setVisible(False); self.status.setText(m); self.load_repos(); self.url_in.clear()

    GUI_MODE = True
    GUI_ERROR = ""
except Exception as e:
    import traceback
    GUI_MODE = False
    GUI_ERROR = traceback.format_exc()

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def main():
    if not is_admin():
        script_path = os.path.abspath(sys.argv[0])
        work_dir = os.path.dirname(script_path)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script_path}"', work_dir, 1)
        sys.exit()
        
    if GUI_MODE:
        app = QApplication(sys.argv); win = EnpaiGUI(); win.show(); sys.exit(app.exec())
    else:
        print("\n[!] HATA: Arayuz baslatilamadi.")
        print("[!] PyQt6 kutuphanesi eksik veya hatalı kurulmus olabilir.")
        print("-" * 50)
        print("HATA DETAYI:")
        print(GUI_ERROR)
        print("-" * 50)
        print("[!] Olası Neden: Python 3.14 gibi deneysel bir surum kullaniyorsaniz PyQt6 desteklenmiyor olabilir.")
        print("[!] Cozum: Python 3.11 veya 3.12 surumunu kurmayi deneyin.\n")
        input("Cikmak icin ENTER'a basin...")

if __name__ == "__main__": main()
