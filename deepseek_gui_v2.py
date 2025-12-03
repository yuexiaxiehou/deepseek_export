import customtkinter as ctk
import requests
import time
import json
import os
import re
import threading
from datetime import datetime

# ==========================================
#  UI 配置与主题 (科技感设定)
# ==========================================
ctk.set_appearance_mode("Dark")  # 深色模式
ctk.set_default_color_theme("dark-blue")  # 蓝色主题

class DeepSeekExporterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 窗口设置
        self.title("DEEPSEEK DATA EXPORTER // PROTOCOL v1.1")
        self.geometry("900x750") #稍微加高一点以容纳新按钮
        self.resizable(False, False)

        # 线程控制标志
        self.stop_flag = False
        self.is_running = False

        # 布局容器
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === 左侧侧边栏 (控制区) ===
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(9, weight=1) # 调整权重让底部顶起来

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="DEEPSEEK\nEXPORTER", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # 鉴权输入区
        self.lbl_auth = ctk.CTkLabel(self.sidebar_frame, text="Authorization (Bearer Token):", anchor="w")
        self.lbl_auth.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.entry_auth = ctk.CTkEntry(self.sidebar_frame, placeholder_text="e.g. Bearer FolRS...", show="*")
        self.entry_auth.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.lbl_cookie = ctk.CTkLabel(self.sidebar_frame, text="Cookie String:", anchor="w")
        self.lbl_cookie.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.entry_cookie = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Paste full cookie here...")
        self.entry_cookie.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")

        # 功能开关
        self.switch_var = ctk.StringVar(value="off")
        self.switch_details = ctk.CTkSwitch(self.sidebar_frame, text="下载对话详情 (Download Details)", 
                                            variable=self.switch_var, onvalue="on", offvalue="off")
        self.switch_details.grid(row=5, column=0, padx=20, pady=20, sticky="w")

        # === 按钮区域 ===
        
        # 启动按钮
        self.btn_start = ctk.CTkButton(self.sidebar_frame, text="启动", command=self.start_thread,
                                       fg_color="#1F6AA5", hover_color="#144870", height=40, font=ctk.CTkFont(weight="bold"))
        self.btn_start.grid(row=6, column=0, padx=20, pady=(10, 10), sticky="ew")

        # 停止按钮 (红色警戒色)
        self.btn_stop = ctk.CTkButton(self.sidebar_frame, text="停止", command=self.stop_process,
                                       fg_color="#800000", hover_color="#A00000", height=40, 
                                       font=ctk.CTkFont(weight="bold"), state="disabled") # 初始禁用
        self.btn_stop.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")

        # 状态标签
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="STATUS: READY", text_color="gray")
        self.status_label.grid(row=10, column=0, padx=20, pady=10)

        # === 右侧主区域 (日志终端) ===
        self.log_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1a1a")
        self.log_frame.grid(row=0, column=1, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.log_frame.grid_rowconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        # 终端文本框
        self.textbox = ctk.CTkTextbox(self.log_frame, font=("Consolas", 12), text_color="#00ff00", fg_color="transparent")
        self.textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.textbox.insert("0.0", ">>> SYSTEM READY...\n>>> WAITING FOR INPUT...\n")
        self.textbox.configure(state="disabled")

    def log(self, message):
        """线程安全的日志打印"""
        def _update():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.textbox.configure(state="normal")
            self.textbox.insert("end", f"[{timestamp}] {message}\n")
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
        self.after(0, _update)

    def set_ui_state(self, running):
        """控制按钮状态"""
        if running:
            self.btn_start.configure(state="disabled", text="RUNNING...")
            self.btn_stop.configure(state="normal", fg_color="#C0392B") # 激活变为亮红
            self.status_label.configure(text="STATUS: PROCESSING", text_color="#00ff00")
        else:
            self.btn_start.configure(state="normal", text="INITIALIZE EXPORT")
            self.btn_stop.configure(state="disabled", fg_color="#800000") # 禁用变为暗红
            self.status_label.configure(text="STATUS: IDLE", text_color="white")

    def start_thread(self):
        """启动后台线程"""
        auth = self.entry_auth.get().strip()
        cookie = self.entry_cookie.get().strip()
        
        if not auth or not cookie:
            self.log("❌ ERROR: Authorization and Cookie are required!")
            return

        is_download = (self.switch_var.get() == "on")
        
        # 重置标志
        self.stop_flag = False
        self.is_running = True
        self.set_ui_state(True)
        
        # 开启线程
        threading.Thread(target=self.run_export_logic, args=(auth, cookie, is_download), daemon=True).start()

    def stop_process(self):
        """停止信号"""
        if self.is_running:
            self.log(">>> ⚠️ ABORT SIGNAL RECEIVED... STOPPING...")
            self.stop_flag = True
            self.btn_stop.configure(state="disabled", text="STOPPING...") # 防止重复点击

    def run_export_logic(self, auth_token, cookie_str, download_details):
        """
        核心逻辑封装区
        """
        try:
            self.log(">>> INITIALIZING CORE LOGIC...")
            
            # --- 动态构建 HEADERS ---
            HEADERS = {
                "Host": "chat.deepseek.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,en-GB;q=0.6",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Authorization": auth_token,
                "Cookie": cookie_str,
                "Referer": "https://chat.deepseek.com/",
                "Origin": "https://chat.deepseek.com",
                "X-App-Version": "20241129.1",
                "X-Client-Locale": "zh_CN",
                "X-Client-Platform": "web",
                "X-Client-Version": "1.5.0",
                "Sec-Ch-Ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Priority": "u=1, i"
            }

            SAVE_DIR = "deepseek_exports"
            OUTPUT_DIR = "deepseek_export_final"
            
            # --- 内部函数 ---
            def safe_filename(title):
                return re.sub(r'[\\/*?:"<>|]', "", title).strip()[:80]

            def fetch_session_list():
                url = "https://chat.deepseek.com/api/v0/chat_session/fetch_page"
                all_sessions = []
                seen_ids = set()
                cursor_updated_at = None
                
                self.log("📋 开始获取会话列表...")
                
                page = 0
                while True:
                    # [STOP CHECK 1] 在翻页循环中检查
                    if self.stop_flag:
                        self.log("🛑 任务已在获取列表阶段中止。")
                        break

                    page += 1
                    params = {"lte_cursor.pinned": "false"}
                    if cursor_updated_at is not None:
                        params["lte_cursor.updated_at"] = cursor_updated_at
                    
                    try:
                        self.log(f"  -> 请求第 {page} 页...")
                        response = requests.get(url, headers=HEADERS, params=params)
                        if response.status_code != 200:
                            self.log(f"  ❌ 请求失败: {response.status_code}")
                            break

                        data = response.json()
                        biz_data = data.get("data", {}).get("biz_data", {})
                        current_list = biz_data.get("chat_sessions", [])
                        has_more = biz_data.get("has_more", False)
                        
                        if not current_list:
                            break
                        
                        new_count = 0
                        for item in current_list:
                            sid = item.get("id")
                            if sid not in seen_ids:
                                seen_ids.add(sid)
                                all_sessions.append(item)
                                new_count += 1
                        
                        self.log(f"     获取 {len(current_list)} 条，新增 {new_count} 条")
                        
                        if page > 1 and new_count == 0:
                            self.log("  ⚠️ 警告：数据重复，停止翻页。")
                            break

                        last_item = current_list[-1]
                        raw_time = last_item.get("updated_at")
                        if raw_time:
                            next_cursor = "{:.3f}".format(raw_time)
                        else:
                            next_cursor = None
                        if next_cursor == cursor_updated_at:
                            break
                        cursor_updated_at = next_cursor
                        
                        if not has_more:
                            self.log("  ✅ 全部列表获取完成。")
                            break
                        
                        # 休眠等待 (可被中断)
                        for _ in range(20): # 2秒拆分成20次0.1秒检查
                            if self.stop_flag: break
                            time.sleep(0.1)
                        
                    except Exception as e:
                        self.log(f"  ❌ 异常: {e}")
                        break
                return all_sessions

            def fetch_chat_history(session_id):
                url = "https://chat.deepseek.com/api/v0/chat/history_messages"
                params = {"chat_session_id": session_id, "count": 100} 
                try:
                    resp = requests.get(url, headers=HEADERS, params=params)
                    if resp.status_code == 200:
                        return resp.json()
                    return None
                except Exception as e:
                    self.log(f"  ❌ 请求详情网络错误: {e}")
                    return None

            def parse_message_content(msg_obj):
                content = ""
                if "content" in msg_obj and msg_obj["content"]:
                    content = msg_obj["content"]
                if "fragments" in msg_obj:
                    for frag in msg_obj["fragments"]:
                        text = frag.get("content", "")
                        if text:
                            content += text
                return content

            def save_to_markdown(session_info, history_data):
                title = session_info.get("title", "未命名")
                sid = session_info.get("id")
                
                if not history_data or "data" not in history_data: return
                data_field = history_data.get("data")
                if not data_field: return
                biz_data = data_field.get("biz_data")
                if not biz_data: return
                messages = biz_data.get("chat_messages", [])
                
                if not messages:
                    self.log(f"  ⚠️ {title}: 消息为空，跳过")
                    return

                if not os.path.exists(OUTPUT_DIR):
                    os.makedirs(OUTPUT_DIR)

                fname = safe_filename(f"{title}_{sid}.md")
                path = os.path.join(OUTPUT_DIR, fname)
                
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n")
                    f.write(f"> ID: {sid}\n> 时间: {session_info.get('updated_at', '')}\n\n---\n\n")
                    for msg in messages:
                        role = msg.get("role", "").upper()
                        content = parse_message_content(msg)
                        if not content: continue
                        if role == "USER":
                            f.write(f"### 🙋‍♂️ 我:\n\n{content}\n\n")
                        elif role == "ASSISTANT":
                            f.write(f"### 🤖 DeepSeek:\n\n{content}\n\n")
                        f.write("---\n")
                self.log(f"  💾 已保存: {fname}")

            # --- 核心流程 ---
            
            if not os.path.exists(SAVE_DIR):
                os.makedirs(SAVE_DIR)
                self.log(f"📁 已创建保存目录: {SAVE_DIR}")

            # 1. 获取列表
            sessions = fetch_session_list()
            
            # [STOP CHECK 2] 列表获取完后检查
            if self.stop_flag:
                self.log("🛑 用户中止：未保存完整会话列表。")
                return

            total = len(sessions)
            self.log(f"\n📊 共发现 {total} 个会话。")

            list_file = os.path.join(SAVE_DIR, "session_list.json")
            with open(list_file, "w", encoding="utf-8") as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
            self.log(f"💾 会话列表已保存至: {list_file}")

            if not download_details:
                self.log("\n🛑 开关 DOWNLOAD_DETAILS = OFF")
                self.log("✅ 仅保存了列表，程序结束。")
            else:
                self.log("\n🚀 开始批量下载对话详情...")
                for i, session in enumerate(sessions):
                    # [STOP CHECK 3] 每一个下载循环前检查
                    if self.stop_flag:
                        self.log("🛑 任务强制停止！后续下载已取消。")
                        break

                    sid = session.get("id")
                    title = session.get("title", "未命名会话")
                    self.log(f"[{i+1}/{total}] 正在处理: {title}")
                    try:
                        history = fetch_chat_history(sid)
                        save_to_markdown(session, history)
                        
                        # 响应更快的休眠 (每0.1秒检查一次停止信号)
                        for _ in range(15): # 等待约1.5秒
                            if self.stop_flag: break
                            time.sleep(0.1)

                    except Exception as e:
                        self.log(f"   ❌ 处理失败: {e}")
                        continue
                
                if not self.stop_flag:
                    self.log("\n🎉 所有任务执行完毕！")

        except Exception as err:
            self.log(f"❌ CRITICAL ERROR: {str(err)}")
        finally:
            self.is_running = False
            self.stop_flag = False
            # 在主线程更新UI
            self.after(0, lambda: self.set_ui_state(False))
            self.after(0, lambda: self.btn_stop.configure(text="ABORT OPERATION"))


if __name__ == "__main__":
    app = DeepSeekExporterApp()
    app.mainloop()
