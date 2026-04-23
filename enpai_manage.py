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
# GUI (CustomTkinter)
# ──────────────────────────────────────────

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
    class DetailsDialog(ctk.CTkToplevel):
        def __init__(self, master, repo_data, config, on_repo_changed):
            super().__init__(master)
            self.title("Repo Detayları")
            self.geometry("600x650")
            self.data = repo_data
            self.cfg = config
            self.on_repo_changed = on_repo_changed
            
            # Make the dialog modal
            self.grab_set()
            
            self.init_ui()
            self.fetch_stats()

        def init_ui(self):
            # Frame
            self.main_frame = ctk.CTkFrame(self, corner_radius=15)
            self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Title
            self.lbl_title = ctk.CTkLabel(self.main_frame, text=self.data['name'], font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color="#38bdf8")
            self.lbl_title.pack(anchor="w", padx=20, pady=(20, 5))
            
            # Info
            s = format_size(get_folder_size(self.data['path']))
            self.lbl_info = ctk.CTkLabel(self.main_frame, text=f"📂 Kategori: {self.data['category']}  |  💾 Boyut: {s}", font=ctk.CTkFont(size=13))
            self.lbl_info.pack(anchor="w", padx=20, pady=(0, 10))
            
            # Stats
            self.lbl_stats = ctk.CTkLabel(self.main_frame, text="📊 İstatistikler yükleniyor...", font=ctk.CTkFont(size=13, weight="bold"), text_color="#94a3b8", corner_radius=8, fg_color="#1e293b", justify="left")
            self.lbl_stats.pack(fill="x", padx=20, pady=(0, 10), ipady=10)
            
            # Description text box
            self.txt_desc = ctk.CTkTextbox(self.main_frame, height=150, corner_radius=8)
            self.txt_desc.pack(fill="both", expand=True, padx=20, pady=(0, 10))
            self.txt_desc.insert("0.0", self.data.get('description') or "Açıklama yok.")
            self.txt_desc.configure(state="disabled")
            
            # AI Button
            if self.cfg.get("groq_key"):
                self.btn_ai = ctk.CTkButton(self.main_frame, text="🤖 Yapay Zeka ile Analiz Et (Groq)", fg_color="#8b5cf6", hover_color="#7c3aed", command=self.start_ai_analyze)
                self.btn_ai.pack(fill="x", padx=20, pady=(0, 10))
                
            # Buttons row 1
            btn_frame1 = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            btn_frame1.pack(fill="x", padx=20, pady=(0, 10))
            
            self.btn_open = ctk.CTkButton(btn_frame1, text="Klasörü Aç", command=lambda: os.startfile(self.data['path']))
            self.btn_open.pack(side="left", expand=True, fill="x", padx=(0, 5))
            
            self.btn_code = ctk.CTkButton(btn_frame1, text="VS Code'da Aç", fg_color="#10b981", hover_color="#059669", command=self.open_vscode)
            self.btn_code.pack(side="left", expand=True, fill="x", padx=(5, 0))
            
            # Buttons row 2
            btn_frame2 = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            btn_frame2.pack(fill="x", padx=20, pady=(0, 15))
            
            self.btn_up = ctk.CTkButton(btn_frame2, text="Güncelle (Git Pull)", fg_color="#f59e0b", hover_color="#d97706", command=self.update_repo)
            self.btn_up.pack(side="left", expand=True, fill="x", padx=(0, 5))
            
            self.btn_del = ctk.CTkButton(btn_frame2, text="Sil", fg_color="#ef4444", hover_color="#dc2626", command=self.delete_repo)
            self.btn_del.pack(side="left", expand=True, fill="x", padx=(5, 0))
            
            self.btn_close = ctk.CTkButton(self.main_frame, text="Kapat", fg_color="#334155", hover_color="#475569", command=self.destroy)
            self.btn_close.pack(fill="x", padx=20, pady=(0, 20))

        def fetch_stats(self):
            def worker():
                try:
                    owner, repo = self.data['name'].split('/')[-2:]
                    info = fetch_repo_info(owner, repo, self.cfg.get("token"))
                    self.after(0, lambda: self.update_stats(info))
                except Exception as e:
                    self.after(0, lambda: self.lbl_stats.configure(text="⚠️ İstatistikler okunamadı."))
            threading.Thread(target=worker, daemon=True).start()

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
                self.lbl_stats.configure(text=text, text_color="#e2e8f0")
            else:
                self.lbl_stats.configure(text="⚠️ İstatistikler çekilemedi (API Sınırı veya Gizli Repo)")

        def start_ai_analyze(self):
            self.btn_ai.configure(state="disabled", text="Analiz ediliyor...")
            self.txt_desc.configure(state="normal")
            self.txt_desc.delete("0.0", "end")
            self.txt_desc.insert("0.0", "Analiz ediliyor, lütfen bekleyin...\n")
            self.txt_desc.configure(state="disabled")
            
            def worker():
                res = groq_analyze(self.data['path'], self.cfg['groq_key'])
                def on_done():
                    self.txt_desc.configure(state="normal")
                    self.txt_desc.delete("0.0", "end")
                    self.txt_desc.insert("0.0", res)
                    self.txt_desc.configure(state="disabled")
                    self.btn_ai.configure(state="normal", text="🤖 Yapay Zeka ile Analiz Et (Groq)")
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
                self.on_repo_changed()
                self.destroy()

    class EnpaiGUI(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("EnpaiManage (Enpai Dev)")
            self.geometry("1100x800")
            
            self.cfg = load_config()
            self.records = []
            
            self.init_ui()
            self.load_repos()
            self.after(5000, self.auto_sync)

        def init_ui(self):
            # Configure grid layout
            self.grid_rowconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=1)
            
            # Sidebar
            self.sidebar = ctk.CTkFrame(self, corner_radius=0, width=220)
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.sidebar.grid_propagate(False)
            
            self.lbl_logo = ctk.CTkLabel(self.sidebar, text="ENPAI DEV", font=ctk.CTkFont(size=24, weight="bold"), text_color="#38bdf8")
            self.lbl_logo.pack(pady=(30, 40))
            
            self.btn_menu_repos = ctk.CTkButton(self.sidebar, text="📂 Repolar", fg_color="transparent", anchor="w", command=lambda: self.show_page(self.page_repos))
            self.btn_menu_repos.pack(fill="x", padx=10, pady=5)
            
            self.btn_menu_settings = ctk.CTkButton(self.sidebar, text="⚙️ Ayarlar", fg_color="transparent", anchor="w", command=lambda: self.show_page(self.page_settings))
            self.btn_menu_settings.pack(fill="x", padx=10, pady=5)
            
            # Spacer
            ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True)
            
            self.btn_readme = ctk.CTkButton(self.sidebar, text="📝 Profil README", fg_color="#10b981", hover_color="#059669", command=self.gen_readme)
            self.btn_readme.pack(fill="x", padx=10, pady=(10, 5))
            
            self.lbl_author = ctk.CTkLabel(self.sidebar, text="By Enous", font=ctk.CTkFont(size=10), text_color="#64748b")
            self.lbl_author.pack(pady=(0, 20))
            
            # Pages
            self.page_repos = ctk.CTkFrame(self, fg_color="transparent")
            self.page_settings = ctk.CTkFrame(self, fg_color="transparent")
            
            self.setup_repos_page()
            self.setup_settings_page()
            
            self.show_page(self.page_repos)

        def show_page(self, page):
            self.page_repos.grid_forget()
            self.page_settings.grid_forget()
            page.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            
            # Highlight sidebar buttons
            if page == self.page_repos:
                self.btn_menu_repos.configure(fg_color=["gray75", "gray25"])
                self.btn_menu_settings.configure(fg_color="transparent")
            else:
                self.btn_menu_repos.configure(fg_color="transparent")
                self.btn_menu_settings.configure(fg_color=["gray75", "gray25"])

        def setup_repos_page(self):
            # Cloning section
            self.lbl_clone = ctk.CTkLabel(self.page_repos, text="GitHub Linkleri", font=ctk.CTkFont(size=14, weight="bold"))
            self.lbl_clone.pack(anchor="w", pady=(0, 5))
            
            self.url_in = ctk.CTkTextbox(self.page_repos, height=100)
            self.url_in.pack(fill="x", pady=(0, 10))
            
            self.btn_clone = ctk.CTkButton(self.page_repos, text="İndir", command=self.start_clone)
            self.btn_clone.pack(anchor="e", pady=(0, 5))
            
            self.lbl_status = ctk.CTkLabel(self.page_repos, text="Hazır.", text_color="#94a3b8")
            self.lbl_status.pack(anchor="w", pady=(0, 5))
            
            self.prog = ctk.CTkProgressBar(self.page_repos, progress_color="#38bdf8")
            self.prog.set(0)
            
            # Collection section
            self.lbl_coll = ctk.CTkLabel(self.page_repos, text="Repo Koleksiyonu", font=ctk.CTkFont(size=18, weight="bold"))
            self.lbl_coll.pack(anchor="w", pady=(20, 10))
            
            search_frame = ctk.CTkFrame(self.page_repos, fg_color="transparent")
            search_frame.pack(fill="x", pady=(0, 10))
            
            self.ent_search = ctk.CTkEntry(search_frame, placeholder_text="İsme göre ara...")
            self.ent_search.pack(side="left", fill="x", expand=True, padx=(0, 10))
            self.ent_search.bind("<KeyRelease>", lambda e: self.filter_list())
            
            self.cat_var = ctk.StringVar(value="Tümü")
            self.cb_cat = ctk.CTkOptionMenu(search_frame, variable=self.cat_var, values=["Tümü", "AI-ML", "Security", "Web", "Tools", "Python", "Other"], command=lambda e: self.filter_list())
            self.cb_cat.pack(side="left")
            
            self.scroll_list = ctk.CTkScrollableFrame(self.page_repos, fg_color="#1e293b", corner_radius=10)
            self.scroll_list.pack(fill="both", expand=True, pady=(0, 5))
            
            self.lbl_path = ctk.CTkLabel(self.page_repos, text="", text_color="#64748b", font=ctk.CTkFont(size=11))
            self.lbl_path.pack(anchor="w")

        def setup_settings_page(self):
            frame = ctk.CTkFrame(self.page_settings, corner_radius=10)
            frame.pack(fill="both", expand=True, padx=40, pady=40)
            
            ctk.CTkLabel(frame, text="Ayarlar", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=30, pady=(30, 20))
            
            ctk.CTkLabel(frame, text="GitHub Token", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=30, pady=(0, 5))
            self.t_ed = ctk.CTkEntry(frame, show="*")
            self.t_ed.insert(0, self.cfg.get("token", ""))
            self.t_ed.pack(fill="x", padx=30, pady=(0, 15))
            
            ctk.CTkLabel(frame, text="Groq API Key", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=30, pady=(0, 5))
            self.g_ed = ctk.CTkEntry(frame, show="*")
            self.g_ed.insert(0, self.cfg.get("groq_key", ""))
            self.g_ed.pack(fill="x", padx=30, pady=(0, 15))
            
            ctk.CTkLabel(frame, text="Klonlama Klasörü", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=30, pady=(0, 5))
            dir_frame = ctk.CTkFrame(frame, fg_color="transparent")
            dir_frame.pack(fill="x", padx=30, pady=(0, 30))
            
            self.d_ed = ctk.CTkEntry(dir_frame)
            self.d_ed.insert(0, self.cfg.get("repos_dir", ""))
            self.d_ed.pack(side="left", fill="x", expand=True, padx=(0, 10))
            
            ctk.CTkButton(dir_frame, text="Seç", fg_color="#334155", hover_color="#475569", width=80, command=self.browse).pack(side="left")
            
            ctk.CTkButton(frame, text="Ayarları Kaydet", command=self.save_sets).pack(anchor="e", padx=30, pady=(0, 30))

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
            if p:
                self.d_ed.delete(0, "end")
                self.d_ed.insert(0, p)

        def save_sets(self):
            self.cfg["token"] = self.t_ed.get().strip()
            self.cfg["repos_dir"] = self.d_ed.get()
            self.cfg["groq_key"] = self.g_ed.get().strip()
            save_config(self.cfg)
            self.show_page(self.page_repos)
            self.load_repos()

        def load_repos(self):
            r_dir = Path(self.cfg.get("repos_dir", str(Path.home() / "EnpaiRepos")))
            self.lbl_path.configure(text=f"Aktif Klasör: {r_dir}")
            if (r_dir / "repos.json").exists():
                with open(r_dir / "repos.json", "r", encoding="utf-8") as f: self.records = json.load(f)
            else: self.records = []
            self.sync_with_fs(refresh=False)
            self.filter_list()

        def auto_sync(self):
            self.sync_with_fs()
            self.after(5000, self.auto_sync)

        def sync_with_fs(self, refresh=True):
            if not self.records: return
            valid = [r for r in self.records if os.path.exists(r['path'])]
            if len(valid) != len(self.records):
                self.records = valid
                r_dir = Path(self.cfg.get("repos_dir", str(Path.home() / "EnpaiRepos")))
                with open(r_dir / "repos.json", "w", encoding="utf-8") as f: json.dump(self.records, f, indent=2, ensure_ascii=False)
                if refresh: self.filter_list()

        def filter_list(self):
            # Clear current items
            for widget in self.scroll_list.winfo_children():
                widget.destroy()
                
            search = self.ent_search.get().lower()
            cat = self.cat_var.get()
            
            for r in reversed(self.records):
                if (search in r['name'].lower()) and (cat == "Tümü" or r['category'] == cat):
                    self.create_repo_item(r)

        def create_repo_item(self, repo_data):
            btn = ctk.CTkButton(
                self.scroll_list, 
                text=f"📦 {repo_data['name']}   |   📂 {repo_data['category']}   |   📅 {repo_data['date']}",
                fg_color="#0f172a",
                hover_color="#38bdf8",
                text_color="#f8fafc",
                anchor="w",
                height=40,
                command=lambda r=repo_data: self.show_details(r)
            )
            btn.pack(fill="x", pady=2, padx=5)

        def show_details(self, repo_data):
            DetailsDialog(self, repo_data, self.cfg, self.load_repos)

        def start_clone(self):
            urls = [u for u in self.url_in.get("0.0", "end").split('\n') if u.strip()]
            if not urls: return
            
            self.prog.pack(fill="x", pady=(5, 0))
            self.prog.set(0)
            
            q = queue.Queue()
            def worker():
                total = len(urls); success = 0
                base_dir = Path(self.cfg.get("repos_dir", str(Path.home() / "EnpaiRepos")))
                token = self.cfg.get("token")
                
                for i, url in enumerate(urls):
                    url = url.strip()
                    if not url: continue
                    q.put(("prog", f"({i+1}/{total}) {url}", (i/total)))
                    try:
                        match = re.search(r"github\.com[:/]([^/]+)/([^/\.]+)", url)
                        if not match: continue
                        owner, repo_name = match.groups(); repo_name = repo_name.replace(".git", "")
                        info = fetch_repo_info(owner, repo_name, token); cat = detect_category(info); target = base_dir / cat / repo_name
                        if target.exists(): continue
                        target.mkdir(parents=True, exist_ok=True)
                        c_url = info.get("clone_url", url)
                        if token: c_url = c_url.replace("https://", f"https://{token.strip()}@")
                        if subprocess.run(["git", "clone", "--depth", "1", c_url, str(target)], capture_output=True, text=True).returncode == 0:
                            success += 1; d = info.get('description') or "Açıklama yok."
                            with open(target / "info.txt", "w", encoding="utf-8") as f: f.write(f"Repo: {info.get('full_name')}\n{d}\n")
                            rec_file = base_dir / "repos.json"; recs = []
                            if rec_file.exists():
                                with open(rec_file, "r", encoding="utf-8") as f: recs = json.load(f)
                            recs.append({"name": info.get("full_name"), "category": cat, "path": str(target), "description": d, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
                            with open(rec_file, "w", encoding="utf-8") as f: json.dump(recs, f, indent=2, ensure_ascii=False)
                    except: pass
                q.put(("done", f"{success} repo indirildi.", 1.0))
                
            def check_queue():
                try:
                    while True:
                        msg = q.get_nowait()
                        if msg[0] == "prog":
                            self.lbl_status.configure(text=msg[1])
                            self.prog.set(msg[2])
                        elif msg[0] == "done":
                            self.lbl_status.configure(text=msg[1])
                            self.prog.pack_forget()
                            self.load_repos()
                            self.url_in.delete("0.0", "end")
                            return
                except queue.Empty: pass
                self.after(100, check_queue)
                
            threading.Thread(target=worker, daemon=True).start()
            check_queue()

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
        app = EnpaiGUI()
        app.mainloop()
    else:
        print("\n[!] HATA: Arayuz baslatilamadi.")
        print("[!] CustomTkinter kutuphanesi eksik veya hatalı kurulmus olabilir.")
        print("-" * 50)
        print("HATA DETAYI:")
        print(GUI_ERROR)
        print("-" * 50)
        print("[!] Cozum: 'kurulum.bat' dosyasini yonetici olarak calistirin.\n")
        input("Cikmak icin ENTER'a basin...")

if __name__ == "__main__": main()
