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
import threading
import queue
import random
import tkinter as tk
from datetime import datetime
from pathlib import Path
import traceback

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

def fetch_repo_info(owner, repo):
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "EnpaiManage"}
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
    except Exception as e: return f"Analiz hatası: {str(e)}"

# ──────────────────────────────────────────
# GUI (CustomTkinter)
# ──────────────────────────────────────────

# Premium Night Blue Palette
COLOR_BG     = "#020617"
COLOR_SIDE   = "#0f172a"
COLOR_PANEL  = "#1e293b"
COLOR_ACCENT = "#38bdf8"
COLOR_TEXT   = "#f8fafc"
COLOR_BTN    = "#2563eb"
COLOR_DANGER = "#ef4444"
COLOR_SUCCESS= "#10b981"
COLOR_AI     = "#8b5cf6"

try:
    import customtkinter as ctk
    from tkinter import messagebox, filedialog
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    GUI_MODE = True
    GUI_ERROR = ""
except Exception as e:
    GUI_MODE = False
    GUI_ERROR = traceback.format_exc()

if GUI_MODE:
    class SnowBackground(tk.Canvas):
        def __init__(self, master, **kwargs):
            super().__init__(master, highlightthickness=0, bg=COLOR_BG, **kwargs)
            self.flakes = []
            self.after(100, self.animate)

        def add_flake(self):
            w = self.winfo_width()
            if w < 100: w = 1100
            x = random.randint(0, w)
            y = -10
            size = random.randint(1, 3)
            speed = random.uniform(1.0, 2.5)
            alpha = random.randint(100, 255)
            flake = self.create_oval(x, y, x+size, y+size, fill="#ffffff", outline="")
            self.flakes.append([flake, speed])

        def animate(self):
            if len(self.flakes) < 80:
                self.add_flake()
            for f in self.flakes[:]:
                self.move(f[0], 0, f[1])
                pos = self.coords(f[0])
                if pos and pos[1] > self.winfo_height():
                    self.delete(f[0])
                    self.flakes.remove(f)
            self.after(30, self.animate)

    class DetailsDialog(ctk.CTkToplevel):
        def __init__(self, master, repo_data, config, on_repo_changed):
            super().__init__(master)
            self.title("Repo Detayları")
            self.geometry("600x680")
            self.configure(fg_color=COLOR_BG)
            self.data = repo_data
            self.cfg = config
            self.on_repo_changed = on_repo_changed
            self.grab_set()
            self.init_ui()
            self.fetch_stats()

        def init_ui(self):
            self.main_frame = ctk.CTkFrame(self, fg_color=COLOR_SIDE, corner_radius=15)
            self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            self.lbl_title = ctk.CTkLabel(self.main_frame, text=self.data['name'], font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=COLOR_ACCENT)
            self.lbl_title.pack(anchor="w", padx=25, pady=(25, 5))
            
            s = format_size(get_folder_size(self.data['path']))
            self.lbl_info = ctk.CTkLabel(self.main_frame, text=f"📂 Kategori: {self.data['category']}  |  💾 Boyut: {s}", font=ctk.CTkFont(size=14), text_color="#94a3b8")
            self.lbl_info.pack(anchor="w", padx=25, pady=(0, 15))
            
            self.lbl_stats = ctk.CTkLabel(self.main_frame, text="📊 İstatistikler yükleniyor...", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLOR_TEXT, corner_radius=10, fg_color=COLOR_PANEL, justify="left")
            self.lbl_stats.pack(fill="x", padx=25, pady=(0, 15), ipady=12)
            
            self.txt_desc = ctk.CTkTextbox(self.main_frame, height=160, corner_radius=10, fg_color="#0f172a", border_color=COLOR_PANEL, border_width=1)
            self.txt_desc.pack(fill="both", expand=True, padx=25, pady=(0, 15))
            self.txt_desc.insert("0.0", self.data.get('description') or "Açıklama yok.")
            self.txt_desc.configure(state="disabled")
            
            if self.cfg.get("groq_key"):
                self.btn_ai = ctk.CTkButton(self.main_frame, text="🤖 Yapay Zeka Analizi", fg_color=COLOR_AI, hover_color="#7c3aed", font=ctk.CTkFont(weight="bold"), command=self.start_ai_analyze)
                self.btn_ai.pack(fill="x", padx=25, pady=(0, 12))
                
            btn_row1 = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            btn_row1.pack(fill="x", padx=25, pady=(0, 10))
            ctk.CTkButton(btn_row1, text="Klasörü Aç", fg_color="#334155", command=lambda: os.startfile(self.data['path'])).pack(side="left", expand=True, fill="x", padx=(0, 5))
            ctk.CTkButton(btn_row1, text="VS Code'da Aç", fg_color=COLOR_SUCCESS, font=ctk.CTkFont(weight="bold"), command=self.open_vscode).pack(side="left", expand=True, fill="x", padx=(5, 0))
            
            btn_row2 = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            btn_row2.pack(fill="x", padx=25, pady=(0, 20))
            ctk.CTkButton(btn_row2, text="Güncelle", fg_color="#f59e0b", command=self.update_repo).pack(side="left", expand=True, fill="x", padx=(0, 5))
            ctk.CTkButton(btn_row2, text="Sil", fg_color=COLOR_DANGER, command=self.delete_repo).pack(side="left", expand=True, fill="x", padx=(5, 0))
            
            dep_py = Path(self.data['path']) / "requirements.txt"
            dep_js = Path(self.data['path']) / "package.json"
            if dep_py.exists() or dep_js.exists():
                cmd = "python -m pip install -r requirements.txt" if dep_py.exists() else "npm install"
                self.btn_dep = ctk.CTkButton(self.main_frame, text=f"🛠️ Bağımlılıkları Kur ({'Python' if dep_py.exists() else 'Node'})", fg_color=COLOR_BTN, command=lambda c=cmd: self.install_deps(c))
                self.btn_dep.pack(fill="x", padx=25, pady=(0, 15))
            
            ctk.CTkButton(self.main_frame, text="Kapat", fg_color="transparent", border_width=1, border_color=COLOR_PANEL, command=self.destroy).pack(fill="x", padx=25, pady=(0, 25))

        def install_deps(self, cmd):
            self.btn_dep.configure(state="disabled", text="Kuruluyor...")
            def worker():
                try:
                    res = subprocess.run(cmd, cwd=self.data['path'], shell=True, capture_output=True, text=True)
                    if res.returncode == 0: self.after(0, lambda: messagebox.showinfo("Bilgi", "Kurulum Başarılı!"))
                    else: self.after(0, lambda: messagebox.showerror("Hata", f"Hata:\n{res.stderr}"))
                except Exception as e: self.after(0, lambda: messagebox.showerror("Hata", str(e)))
                finally: self.after(0, lambda: self.btn_dep.configure(state="normal", text=f"🛠️ Bağımlılıkları Kur"))
            threading.Thread(target=worker, daemon=True).start()

        def fetch_stats(self):
            def worker():
                try:
                    owner, repo = self.data['name'].split('/')[-2:]
                    info = fetch_repo_info(owner, repo)
                    self.after(0, lambda: self.update_stats(info))
                except: self.after(0, lambda: self.lbl_stats.configure(text="⚠️ İstatistikler okunamadı."))
            threading.Thread(target=worker, daemon=True).start()

        def update_stats(self, info):
            if "id" in info:
                stars, forks, watchers = info.get("stargazers_count", 0), info.get("forks_count", 0), info.get("watchers_count", 0)
                issues, lang = info.get("open_issues_count", 0), info.get("language", "Bilinmiyor")
                lic = info.get("license", {}).get("name", "Yok") if info.get("license") else "Yok"
                text = (f"⭐ Yıldız: {stars}  |  🍴 Fork: {forks}  |  👀 İzleyen: {watchers}\n"
                        f"🐛 Açık Issue: {issues}  |  💻 Dil: {lang}  |  📜 Lisans: {lic}")
                self.lbl_stats.configure(text=text, text_color=COLOR_TEXT)
            else: self.lbl_stats.configure(text="⚠️ İstatistikler çekilemedi.")

        def start_ai_analyze(self):
            self.btn_ai.configure(state="disabled", text="Analiz ediliyor...")
            self.txt_desc.configure(state="normal"); self.txt_desc.delete("0.0", "end")
            self.txt_desc.insert("0.0", "Analiz ediliyor, lütfen bekleyin...\n")
            self.txt_desc.configure(state="disabled")
            def worker():
                res = groq_analyze(self.data['path'], self.cfg['groq_key'])
                def on_done():
                    self.txt_desc.configure(state="normal"); self.txt_desc.delete("0.0", "end")
                    self.txt_desc.insert("0.0", res); self.txt_desc.configure(state="disabled")
                    self.btn_ai.configure(state="normal", text="🤖 Yapay Zeka Analizi")
                self.after(0, on_done)
            threading.Thread(target=worker, daemon=True).start()

        def open_vscode(self):
            try: subprocess.Popen(["code", self.data['path']], shell=True)
            except: messagebox.showwarning("Hata", "VS Code bulunamadı.")

        def update_repo(self):
            try:
                res = subprocess.run(["git", "pull"], cwd=self.data['path'], capture_output=True, text=True)
                if res.returncode == 0: messagebox.showinfo("Bilgi", "Başarıyla güncellendi.")
                else: messagebox.showerror("Hata", res.stderr)
            except Exception as e: messagebox.showerror("Hata", str(e))

        def delete_repo(self):
            if messagebox.askyesno("Onay", "Bu repo tamamen silinsin mi?"):
                if os.path.exists(self.data['path']): shutil.rmtree(self.data['path'], onerror=remove_readonly)
                r_dir = Path(self.cfg.get("repos_dir", str(Path.home() / "EnpaiRepos")))
                rec_file = r_dir / "repos.json"
                if rec_file.exists():
                    with open(rec_file, "r", encoding="utf-8") as f: recs = json.load(f)
                    with open(rec_file, "w", encoding="utf-8") as f: json.dump([r for r in recs if r['path']!=self.data['path']], f, indent=2, ensure_ascii=False)
                self.on_repo_changed(); self.destroy()

    class EnpaiGUI(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("EnpaiManage (Enpai Dev)")
            self.geometry("1150x850")
            self.configure(fg_color=COLOR_BG)
            self.cfg = load_config()
            self.records = []
            
            # Animation Background
            self.snow = SnowBackground(self)
            self.snow.place(relx=0, rely=0, relwidth=1, relheight=1)
            
            self.init_ui()
            self.load_repos()
            self.after(5000, self.auto_sync)

        def init_ui(self):
            self.grid_rowconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=1)
            
            # Sidebar
            self.sidebar = ctk.CTkFrame(self, corner_radius=0, width=240, fg_color=COLOR_SIDE)
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.sidebar.grid_propagate(False)
            
            self.lbl_logo = ctk.CTkLabel(self.sidebar, text="ENPAI DEV", font=ctk.CTkFont(family="Outfit", size=28, weight="bold"), text_color=COLOR_ACCENT)
            self.lbl_logo.pack(pady=(40, 50))
            
            self.btn_repos = ctk.CTkButton(self.sidebar, text="  📂 Repolar", fg_color="transparent", anchor="w", font=ctk.CTkFont(size=15), height=45, command=lambda: self.show_page(self.page_repos))
            self.btn_repos.pack(fill="x", padx=15, pady=5)
            
            self.btn_trend = ctk.CTkButton(self.sidebar, text="  🔥 Trend Keşfet", fg_color="transparent", anchor="w", font=ctk.CTkFont(size=15), height=45, command=lambda: self.show_page(self.page_trending))
            self.btn_trend.pack(fill="x", padx=15, pady=5)
            
            self.btn_settings = ctk.CTkButton(self.sidebar, text="  ⚙️ Ayarlar", fg_color="transparent", anchor="w", font=ctk.CTkFont(size=15), height=45, command=lambda: self.show_page(self.page_settings))
            self.btn_settings.pack(fill="x", padx=15, pady=5)
            
            ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True)
            
            self.btn_readme = ctk.CTkButton(self.sidebar, text="📝 Profil README", fg_color=COLOR_SUCCESS, hover_color="#059669", font=ctk.CTkFont(weight="bold"), height=40, command=self.gen_readme)
            self.btn_readme.pack(fill="x", padx=20, pady=(10, 5))
            
            self.lbl_author = ctk.CTkLabel(self.sidebar, text="By Enous", font=ctk.CTkFont(size=11), text_color="#4b5563")
            self.lbl_author.pack(pady=(0, 25))
            
            # Pages Container
            self.container = ctk.CTkFrame(self, fg_color="transparent")
            self.container.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
            self.container.grid_rowconfigure(0, weight=1)
            self.container.grid_columnconfigure(0, weight=1)
            
            self.page_repos = ctk.CTkFrame(self.container, fg_color="transparent")
            self.page_trending = ctk.CTkFrame(self.container, fg_color="transparent")
            self.page_settings = ctk.CTkFrame(self.container, fg_color="transparent")
            
            self.setup_repos_page()
            self.setup_trending_page()
            self.setup_settings_page()
            self.show_page(self.page_repos)

        def show_page(self, page):
            self.page_repos.grid_forget()
            self.page_trending.grid_forget()
            self.page_settings.grid_forget()
            page.grid(row=0, column=0, sticky="nsew")
            self.btn_repos.configure(fg_color=COLOR_PANEL if page==self.page_repos else "transparent")
            self.btn_trend.configure(fg_color=COLOR_PANEL if page==self.page_trending else "transparent")
            self.btn_settings.configure(fg_color=COLOR_PANEL if page==self.page_settings else "transparent")

        def setup_repos_page(self):
            # Header section
            self.url_frame = ctk.CTkFrame(self.page_repos, fg_color=COLOR_SIDE, corner_radius=15, border_width=1, border_color=COLOR_PANEL)
            self.url_frame.pack(fill="x", pady=(0, 25), padx=5)
            
            ctk.CTkLabel(self.url_frame, text="GitHub Linkleri (Satır Satır)", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
            self.url_in = ctk.CTkTextbox(self.url_frame, height=110, fg_color=COLOR_BG, border_width=0)
            self.url_in.pack(fill="x", padx=20, pady=(0, 15))
            
            btn_clone_frame = ctk.CTkFrame(self.url_frame, fg_color="transparent")
            btn_clone_frame.pack(fill="x", padx=20, pady=(0, 15))
            self.lbl_status = ctk.CTkLabel(btn_clone_frame, text="Hazır.", text_color="#94a3b8", font=ctk.CTkFont(size=12))
            self.lbl_status.pack(side="left")
            self.btn_clone = ctk.CTkButton(btn_clone_frame, text="🚀 İndirmeye Başla", fg_color=COLOR_BTN, font=ctk.CTkFont(weight="bold"), width=160, command=self.start_clone)
            self.btn_clone.pack(side="right")
            
            self.prog = ctk.CTkProgressBar(self.page_repos, progress_color=COLOR_ACCENT, height=10)
            self.prog.set(0)
            
            # List section
            self.list_header = ctk.CTkFrame(self.page_repos, fg_color="transparent")
            self.list_header.pack(fill="x", pady=(15, 10))
            ctk.CTkLabel(self.list_header, text="Repo Koleksiyonu", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
            
            self.cat_var = ctk.StringVar(value="Tümü")
            self.cb_cat = ctk.CTkOptionMenu(self.list_header, variable=self.cat_var, values=["Tümü", "AI-ML", "Security", "Web", "Tools", "Python", "Other"], fg_color=COLOR_PANEL, button_color=COLOR_PANEL, command=lambda e: self.filter_list())
            self.cb_cat.pack(side="right")
            
            self.ent_search = ctk.CTkEntry(self.page_repos, placeholder_text="İsim ile filtrele...", height=45, fg_color=COLOR_SIDE, border_color=COLOR_PANEL)
            self.ent_search.pack(fill="x", pady=(0, 15))
            self.ent_search.bind("<KeyRelease>", lambda e: self.filter_list())
            
            self.scroll_list = ctk.CTkScrollableFrame(self.page_repos, fg_color=COLOR_SIDE, corner_radius=15, border_width=1, border_color=COLOR_PANEL)
            self.scroll_list.pack(fill="both", expand=True)
            
            self.lbl_path = ctk.CTkLabel(self.page_repos, text="", text_color="#4b5563", font=ctk.CTkFont(size=11))
            self.lbl_path.pack(anchor="w", pady=(10, 0))

        def setup_trending_page(self):
            frame = ctk.CTkFrame(self.page_trending, fg_color=COLOR_SIDE, corner_radius=20, border_width=1, border_color=COLOR_PANEL)
            frame.pack(fill="both", expand=True, padx=20, pady=20)
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=40, pady=(40, 20))
            ctk.CTkLabel(header, text="🔥 GitHub Trendleri", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
            self.btn_refresh_t = ctk.CTkButton(header, text="Yenile", width=100, fg_color=COLOR_PANEL, command=self.load_trends)
            self.btn_refresh_t.pack(side="right")
            self.list_t = ctk.CTkScrollableFrame(frame, fg_color=COLOR_BG, corner_radius=15)
            self.list_t.pack(fill="both", expand=True, padx=40, pady=(0, 40))
            self.load_trends()

        def load_trends(self):
            for w in self.list_t.winfo_children(): w.destroy()
            ctk.CTkLabel(self.list_t, text="Yükleniyor... Lütfen bekleyin.", text_color="#94a3b8").pack(pady=50)
            self.btn_refresh_t.configure(state="disabled")
            def worker():
                try:
                    import datetime as dt
                    d = (dt.datetime.now() - dt.timedelta(days=7)).strftime("%Y-%m-%d")
                    url = f"https://api.github.com/search/repositories?q=created:>{d}&sort=stars&order=desc"
                    req = urllib.request.Request(url, headers={"User-Agent": "EnpaiManage"})
                    with urllib.request.urlopen(req) as resp:
                        data = json.loads(resp.read().decode())
                        self.after(0, lambda: self.disp_trends(data.get("items", [])[:20]))
                except Exception as e: self.after(0, lambda: self.disp_trends_err(str(e)))
            threading.Thread(target=worker, daemon=True).start()

        def disp_trends_err(self, e):
            for w in self.list_t.winfo_children(): w.destroy()
            ctk.CTkLabel(self.list_t, text=f"Hata: {e}", text_color=COLOR_DANGER).pack(pady=50)
            self.btn_refresh_t.configure(state="normal")

        def disp_trends(self, items):
            for w in self.list_t.winfo_children(): w.destroy()
            if not items: ctk.CTkLabel(self.list_t, text="Trend bulunamadı.", text_color="#94a3b8").pack(pady=50)
            for item in items:
                f = ctk.CTkFrame(self.list_t, fg_color=COLOR_PANEL, corner_radius=10)
                f.pack(fill="x", pady=5, padx=10, ipady=5)
                lbl = ctk.CTkLabel(f, text=f"🔥 {item['full_name']} (⭐ {item.get('stargazers_count')} | 💻 {item.get('language') or '?'})", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
                lbl.pack(side="left", padx=15)
                btn = ctk.CTkButton(f, text="İndir", width=80, fg_color=COLOR_BTN, command=lambda u=item['html_url']: self.clone_trend(u))
                btn.pack(side="right", padx=15)
            self.btn_refresh_t.configure(state="normal")

        def clone_trend(self, url):
            self.show_page(self.page_repos)
            self.url_in.delete("0.0", "end")
            self.url_in.insert("0.0", url)
            self.start_clone()

        def setup_settings_page(self):
            frame = ctk.CTkFrame(self.page_settings, fg_color=COLOR_SIDE, corner_radius=20, border_width=1, border_color=COLOR_PANEL)
            frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            ctk.CTkLabel(frame, text="⚙️ Uygulama Ayarları", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", padx=40, pady=(40, 30))
            
            self.g_ed = self.create_setting_field(frame, "Groq AI API Key", self.cfg.get("groq_key", ""), is_pass=True)
            
            ctk.CTkLabel(frame, text="Klonlama Ana Klasörü", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=40, pady=(0, 5))
            dir_frame = ctk.CTkFrame(frame, fg_color="transparent")
            dir_frame.pack(fill="x", padx=40, pady=(0, 30))
            self.d_ed = ctk.CTkEntry(dir_frame, height=45, fg_color=COLOR_BG, border_color=COLOR_PANEL)
            self.d_ed.insert(0, self.cfg.get("repos_dir", ""))
            self.d_ed.pack(side="left", fill="x", expand=True, padx=(0, 10))
            ctk.CTkButton(dir_frame, text="Klasör Seç", fg_color=COLOR_PANEL, width=110, height=45, command=self.browse).pack(side="left")
            
            ctk.CTkButton(frame, text="💾 Değişiklikleri Kaydet", fg_color=COLOR_BTN, font=ctk.CTkFont(weight="bold"), height=50, width=200, command=self.save_sets).pack(anchor="e", padx=40, pady=(10, 40))

        def create_setting_field(self, parent, label, value, is_pass=False):
            ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=40, pady=(0, 5))
            ent = ctk.CTkEntry(parent, height=45, fg_color=COLOR_BG, border_color=COLOR_PANEL, show="*" if is_pass else "")
            ent.insert(0, value)
            ent.pack(fill="x", padx=40, pady=(0, 20))
            return ent

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
            save_p = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown Files", "*.md")])
            if save_p:
                with open(save_p, "w", encoding="utf-8") as f: f.write(md)
                messagebox.showinfo("Başarılı", "Profil README dosyası oluşturuldu!")

        def browse(self):
            p = filedialog.askdirectory(initialdir=self.d_ed.get())
            if p: self.d_ed.delete(0, "end"); self.d_ed.insert(0, p)

        def save_sets(self):
            self.cfg["repos_dir"], self.cfg["groq_key"] = self.d_ed.get(), self.g_ed.get().strip()
            save_config(self.cfg); self.show_page(self.page_repos); self.load_repos()

        def load_repos(self):
            r_dir = Path(self.cfg.get("repos_dir", str(Path.home() / "EnpaiRepos")))
            self.lbl_path.configure(text=f"Aktif Klasör: {r_dir}")
            if (r_dir / "repos.json").exists():
                with open(r_dir / "repos.json", "r", encoding="utf-8") as f: self.records = json.load(f)
            else: self.records = []
            self.sync_with_fs(refresh=False); self.filter_list()

        def auto_sync(self):
            self.sync_with_fs(); self.after(5000, self.auto_sync)

        def sync_with_fs(self, refresh=True):
            if not self.records: return
            valid = [r for r in self.records if os.path.exists(r['path'])]
            if len(valid) != len(self.records):
                self.records = valid
                r_dir = Path(self.cfg.get("repos_dir", str(Path.home() / "EnpaiRepos")))
                with open(r_dir / "repos.json", "w", encoding="utf-8") as f: json.dump(self.records, f, indent=2, ensure_ascii=False)
                if refresh: self.filter_list()

        def filter_list(self):
            for widget in self.scroll_list.winfo_children(): widget.destroy()
            search, cat = self.ent_search.get().lower(), self.cat_var.get()
            for r in reversed(self.records):
                if (search in r['name'].lower()) and (cat == "Tümü" or r['category'] == cat): self.create_repo_item(r)

        def create_repo_item(self, repo_data):
            btn = ctk.CTkButton(self.scroll_list, text=f"  📦 {repo_data['name']}    |    📂 {repo_data['category']}    |    📅 {repo_data['date']}", 
                                fg_color=COLOR_BG, hover_color=COLOR_ACCENT, text_color=COLOR_TEXT, anchor="w", height=50, corner_radius=10, 
                                font=ctk.CTkFont(size=13), command=lambda r=repo_data: DetailsDialog(self, r, self.cfg, self.load_repos))
            btn.pack(fill="x", pady=4, padx=8)

        def start_clone(self):
            urls = [u for u in self.url_in.get("0.0", "end").split('\n') if u.strip()]
            if not urls: return
            self.prog.pack(fill="x", pady=(5, 15)); self.prog.set(0)
            q = queue.Queue()
            def worker():
                total, success = len(urls), 0
                base_dir = Path(self.cfg.get("repos_dir", str(Path.home() / "EnpaiRepos")))
                for i, url in enumerate(urls):
                    url = url.strip()
                    if not url: continue
                    q.put(("prog", f"({i+1}/{total}) {url}", (i/total)))
                    try:
                        match = re.search(r"github\.com[:/]([^/]+)/([^/\.]+)", url)
                        if not match: continue
                        owner, repo_name = match.groups(); repo_name = repo_name.replace(".git", "")
                        info = fetch_repo_info(owner, repo_name); cat = detect_category(info); target = base_dir / cat / repo_name
                        if target.exists(): continue
                        target.mkdir(parents=True, exist_ok=True); c_url = info.get("clone_url", url)
                        if subprocess.run(["git", "clone", "--depth", "1", c_url, str(target)], capture_output=True, text=True).returncode == 0:
                            success += 1; d = info.get('description') or "Açıklama yok."
                            with open(target / "info.txt", "w", encoding="utf-8") as f: f.write(f"Repo: {info.get('full_name')}\n{d}\n")
                            rec_file = base_dir / "repos.json"; recs = []
                            if rec_file.exists():
                                with open(rec_file, "r", encoding="utf-8") as f: recs = json.load(f)
                            recs.append({"name": info.get("full_name"), "category": cat, "path": str(target), "description": d, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
                            with open(rec_file, "w", encoding="utf-8") as f: json.dump(recs, f, indent=2, ensure_ascii=False)
                    except: pass
                q.put(("done", f"✨ İşlem tamamlandı! {success} repo indirildi.", 1.0))
            def check_queue():
                try:
                    while True:
                        msg = q.get_nowait()
                        if msg[0] == "prog": self.lbl_status.configure(text=msg[1]); self.prog.set(msg[2])
                        elif msg[0] == "done":
                            self.lbl_status.configure(text=msg[1], text_color=COLOR_SUCCESS); self.prog.pack_forget(); self.load_repos(); self.url_in.delete("0.0", "end"); return
                except queue.Empty: pass
                self.after(100, check_queue)
            threading.Thread(target=worker, daemon=True).start(); check_queue()

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def main():
    if not is_admin():
        script_path = os.path.abspath(sys.argv[0])
        work_dir = os.path.dirname(script_path)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script_path}"', work_dir, 1); sys.exit()
    if GUI_MODE:
        app = EnpaiGUI(); app.mainloop()
    else:
        print("\n[!] HATA: Arayuz baslatilamadi.")
        print("[!] Kutuphaneler eksik veya Python surumunuz (ornegin Python 3.14) desteklenmiyor olabilir.")
        print("-" * 50)
        print("HATA DETAYI:")
        print(GUI_ERROR)
        print("-" * 50)
        print("[!] Lutfen 'kurulum.bat' dosyasini yonetici olarak calistirin.\n")
        input("Cikmak icin ENTER'a basin...")

if __name__ == "__main__": main()
