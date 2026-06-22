from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'system')

from kivy.core.window import Window
Window.fullscreen = False
Window.softinput_mode = "pan"

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
import kivy.properties as kp
from kivy.properties import NumericProperty, StringProperty, ObjectProperty, BooleanProperty
import requests
import json
import threading
import os
import base64
import re
import webbrowser

GITHUB_TOKEN_FILE = "jimi_github_token.txt"
GEMINI_KEY_FILE = "jimi_gemini_key.txt"
USER_FILE = "jimi_user.txt"
REPO_FILE = "jimi_repo.txt"

for file, default in [(GITHUB_TOKEN_FILE, ""), (GEMINI_KEY_FILE, ""), (USER_FILE, "Hackabu4"), (REPO_FILE, "jimi-build")]:
    if not os.path.exists(file):
        with open(file, "w") as f: f.write(default)

def get_setting(file):
    try:
        with open(file, "r") as f:
            content = f.read().splitlines()
            return content[0].strip() if content else ""
    except: return ""

CHAT_HISTORY = []
CURRENT_GENERATED_CODE = ""

def ask_gemini(prompt, history, callback):
    def run():
        gemini_key = get_setting(GEMINI_KEY_FILE)
        if not gemini_key:
            Clock.schedule_once(lambda dt: callback("⚠️ Баптаулар (⚙️) бөліміне өтіп, Gemini API кілтін жазыңыз!", ""), 0)
            return

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        
        system_instruction = (
            "You are Jimi, a friendly AI companion and expert Kivy developer who speaks Kazakh fluently. "
            "If the user asks you to build, modify, or create any UI, app, button, or spinner, "
            "you MUST generate the complete, self-contained, working Python Kivy code. "
            "The code must use standard Kivy (NOT KivyMD) and load its own layout properly. "
            "Wrap your executable Python code block strictly between [START_PY] and [END_PY] tags."
        )
        
        contents = [{"role": "user", "parts": [{"text": system_instruction}]}]
        for msg in history:
            role_type = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role_type, "parts": [{"text": msg["text"]}]})

        payload = {"contents": contents}
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=25)
            result = response.json()
            
            if 'error' in result:
                Clock.schedule_once(lambda dt: callback(f"Қате: {result['error']['message']}", ""), 0)
                return
                
            ai_text = result['candidates'][0]['content']['parts'][0]['text']
            
            py_match = re.search(r'\[START_PY\](.*?)\[END_PY\]', ai_text, re.DOTALL)
            clean_code = ""
            clean_text = ai_text
            
            if py_match:
                clean_code = py_match.group(1).strip()
                clean_text = ai_text.replace(py_match.group(0), "\n\n(🔥 Интерфейс сәтті құрастырылды! Көру үшін жоғарыдағы ➡️ батырмасын басыңыз)")
                
            Clock.schedule_once(lambda dt: callback(clean_text.strip(), clean_code), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: callback(f"Қате: Сервер жауап бермеді.", ""), 0)

    threading.Thread(target=run).start()

class DarkScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.12, 0.12, 0.16, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)
    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

class ChatScreen(DarkScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height="50dp", spacing=5)
        folder_btn = Button(text="📁 Папка", size_hint_x=None, width="75dp", background_color=(0.2, 0.4, 0.8, 1), on_release=self.open_folder)
        title = Label(text="Jimi Сұхбат", font_size="18sp", bold=True, size_hint_x=1.0, halign="center")
        key_btn = Button(text="⚙️ Баптау", font_size="14sp", size_hint_x=None, width="90dp", background_color=(0.7, 0.2, 0.7, 1), on_release=self.open_settings)
        next_btn = Button(text="➡️", font_size="18sp", bold=True, size_hint_x=None, width="50dp", background_color=(0, 0.6, 0.5, 1), on_release=self.go_to_test_screen)
        top_bar.add_widget(folder_btn); top_bar.add_widget(title); top_bar.add_widget(key_btn); top_bar.add_widget(next_btn)
        self.main_layout.add_widget(top_bar)
        
        self.chat_scroll = ScrollView(size_hint_y=1.0)
        self.chat_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        self.chat_list.bind(minimum_height=self.chat_list.setter('height'))
        self.chat_scroll.add_widget(self.chat_list)
        self.main_layout.add_widget(self.chat_scroll)
        
        input_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height="50dp", spacing=5)
        self.input_field = TextInput(hint_text="Еркін сөйлесіңіз...", multiline=True, write_tab=False, background_color=(0.2, 0.2, 0.25, 1), foreground_color=(1, 1, 1, 1))
        send_btn = Button(text="Жіберу", size_hint_x=None, width="80dp", background_color=(0, 0.7, 0.3, 1), on_release=self.send_message)
        input_bar.add_widget(self.input_field); input_bar.add_widget(send_btn)
        self.main_layout.add_widget(input_bar)
        self.add_widget(self.main_layout)

    def scroll_to_bottom(self, dt): self.chat_scroll.scroll_y = 0
    def go_to_test_screen(self, instance):
        self.manager.get_screen("test_screen").load_dynamic_ui()
        self.manager.transition.direction = "left"; self.manager.current = "test_screen"
    def send_message(self, instance):
        user_text = self.input_field.text
        if user_text:
            lbl = Label(text=f"Сіз: {user_text}", size_hint_y=None, text_size=(Window.width - 40, None), halign="left", color=(0.8, 0.9, 1, 1))
            lbl.bind(texture_size=lambda instance, size: setattr(instance, 'height', size[1]))
            self.chat_list.add_widget(lbl); self.input_field.text = ""
            CHAT_HISTORY.append({"role": "user", "text": user_text})
            self.thinking_lbl = Label(text="Jimi: Жазып жатыр... ✍️", size_hint_y=None, height="40dp", color=(0.7, 0.7, 0.7, 1))
            self.chat_list.add_widget(self.thinking_lbl)
            Clock.schedule_once(self.scroll_to_bottom, 0.1)
            ask_gemini(user_text, CHAT_HISTORY, self.on_gemini_response)
    def on_gemini_response(self, ai_text, ai_code):
        if hasattr(self, 'thinking_lbl') and self.thinking_lbl in self.chat_list.children: self.chat_list.remove_widget(self.thinking_lbl)
        CHAT_HISTORY.append({"role": "model", "text": ai_text})
        global CURRENT_GENERATED_CODE
        if ai_code: CURRENT_GENERATED_CODE = ai_code
        lbl = Label(text=f"Jimi: {ai_text}", size_hint_y=None, text_size=(Window.width - 40, None), halign="left", color=(0.3, 1, 0.6, 1))
        lbl.bind(texture_size=lambda instance, size: setattr(instance, 'height', size[1]))
        self.chat_list.add_widget(lbl); Clock.schedule_once(self.scroll_to_bottom, 0.1)
    def open_folder(self, instance):
        self.manager.get_screen("folder_screen").check_github_artifacts()
        self.manager.transition.direction = "down"; self.manager.current = "folder_screen"
    def open_settings(self, instance):
        self.manager.transition.direction = "left"; self.manager.current = "settings_screen"

class SettingsScreen(DarkScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=15, spacing=8)
        layout.add_widget(Label(text="⚙️ Баптаулар", font_size="20sp", bold=True, size_hint_y=None, height="35dp"))
        self.token_input = TextInput(text=get_setting(GITHUB_TOKEN_FILE), multiline=False, size_hint_y=None, height="40dp")
        layout.add_widget(Label(text="Token:")); layout.add_widget(self.token_input)
        self.gemini_input = TextInput(text=get_setting(GEMINI_KEY_FILE), multiline=False, size_hint_y=None, height="40dp")
        layout.add_widget(Label(text="Gemini Key:")); layout.add_widget(self.gemini_input)
        self.user_input = TextInput(text=get_setting(USER_FILE), multiline=False, size_hint_y=None, height="40dp")
        layout.add_widget(Label(text="User:")); layout.add_widget(self.user_input)
        self.repo_input = TextInput(text=get_setting(REPO_FILE), multiline=False, size_hint_y=None, height="40dp")
        layout.add_widget(Label(text="Repo:")); layout.add_widget(self.repo_input)
        save_btn = Button(text="💾 САҚТАУ", size_hint_y=None, height="45dp", on_release=self.save_settings)
        layout.add_widget(save_btn); self.add_widget(layout)
    def save_settings(self, instance):
        with open(GITHUB_TOKEN_FILE, "w") as f: f.write(self.token_input.text.strip())
        with open(GEMINI_KEY_FILE, "w") as f: f.write(self.gemini_input.text.strip())
        with open(USER_FILE, "w") as f: f.write(self.user_input.text.strip())
        with open(REPO_FILE, "w") as f: f.write(self.repo_input.text.strip())
        self.manager.transition.direction = "right"; self.manager.current = "chat_screen"

class TestScreen(DarkScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        test_top_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height="50dp")
        back_arrow = Button(text="⬅️", size_hint_x=None, width="50dp", on_release=self.go_back_to_chat)
        test_top_bar.add_widget(back_arrow); test_top_bar.add_widget(Label(text="[ Jimi Құрастырған Элементтер ]"))
        self.main_layout.add_widget(test_top_bar)
        
        self.test_container = BoxLayout(orientation='vertical', size_hint_y=1.0)
        self.main_layout.add_widget(self.test_container)
        
        # ЖАҢАДАН ҚОСЫЛҒАН БӨЛІК: Қолданбаның жеке атын жазатын жолақ
        self.app_name_input = TextInput(
            hint_text="Қолданбаның жаңа атын жазыңыз (мысалы: MeninApp)", 
            size_hint_y=None, height="45dp", multiline=False, 
            background_color=(0.2, 0.2, 0.25, 1), foreground_color=(1, 1, 1, 1)
        )
        self.main_layout.add_widget(self.app_name_input)
        
        self.build_btn = Button(text="🚀 ГИТХАБҚА ЖІБЕРУ (BUILD)", size_hint_y=None, height="50dp", background_color=(0, 0.6, 0.2, 1), on_release=self.trigger_github_upload)
        self.main_layout.add_widget(self.build_btn)
        self.add_widget(self.main_layout)
        
    def go_back_to_chat(self, instance):
        self.manager.transition.direction = "right"; self.manager.current = "chat_screen"
        
    def load_dynamic_ui(self):
        self.test_container.clear_widgets()
        global CURRENT_GENERATED_CODE
        if CURRENT_GENERATED_CODE:
            try:
                local_scope = {
                    'App': App, 'BoxLayout': BoxLayout, 'Button': Button, 'Label': Label, 
                    'TextInput': TextInput, 'NumericProperty': NumericProperty, 'StringProperty': StringProperty,
                    'ObjectProperty': ObjectProperty, 'BooleanProperty': BooleanProperty,
                    'kp': kp, 'Clock': Clock, 'Window': Window, 'FloatLayout': FloatLayout, 'ScrollView': ScrollView
                }
                exec(CURRENT_GENERATED_CODE, local_scope)
                app_class = None
                for obj in local_scope.values():
                    if isinstance(obj, type) and issubclass(obj, App) and obj.__name__ != 'App':
                        app_class = obj()
                        break
                if app_class:
                    dynamic_widget = app_class.build()
                    if dynamic_widget: self.test_container.add_widget(dynamic_widget)
            except Exception as e:
                self.test_container.add_widget(Label(text=f"Қате: {str(e)[:100]}"))
                
    def trigger_github_upload(self, instance):
        self.build_btn.text = "Жіберілуде... ⏳"
        self.build_btn.disabled = True
        threading.Thread(target=self.upload_to_github).start()
        
    def upload_to_github(self):
        token = get_setting(GITHUB_TOKEN_FILE)
        username = get_setting(USER_FILE)
        repo = get_setting(REPO_FILE)
        global CURRENT_GENERATED_CODE
        
        if not token or not username or not repo or not CURRENT_GENERATED_CODE:
            Clock.schedule_once(lambda dt: self.update_btn_status("Жіберетін код немесе баптау жоқ!"), 0)
            return

        # Қолданбаның атын және пакетін дайындау
        app_title = self.app_name_input.text.strip()
        if not app_title:
            app_title = "JimiNewApp"
            
        # Пакет атына тек латын әріптері мен сандар керек (орынсыз, арнайы таңбасыз)
        safe_pkg_name = re.sub(r'[^a-z0-9]', '', app_title.lower())
        if not safe_pkg_name:
            safe_pkg_name = "myapp"

        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        
        # 1-ҚАДАМ: main.py файлын жіберу
        url_main = f"https://api.github.com/repos/{username}/{repo}/contents/main.py"
        sha_main = ""
        try:
            get_res = requests.get(url_main, headers=headers, timeout=10)
            if get_res.status_code == 200: sha_main = get_res.json().get("sha", "")
        except: pass

        content_bytes = CURRENT_GENERATED_CODE.encode("utf-8")
        base64_main = base64.b64encode(content_bytes).decode("utf-8")
        payload_main = {"message": f"Jimi: жаңа код ({app_title})", "content": base64_main}
        if sha_main: payload_main["sha"] = sha_main

        try:
            requests.put(url_main, headers=headers, json=payload_main, timeout=15)
        except:
            Clock.schedule_once(lambda dt: self.update_btn_status("Желілік байланыс қатесі (main.py)"), 0)
            return

        # 2-ҚАДАМ: buildozer.spec файлының ішіндегі атауын жаңарту
        url_spec = f"https://api.github.com/repos/{username}/{repo}/contents/buildozer.spec"
        try:
            spec_res = requests.get(url_spec, headers=headers, timeout=10)
            if spec_res.status_code == 200:
                spec_data = spec_res.json()
                spec_sha = spec_data.get("sha", "")
                spec_text = base64.b64decode(spec_data.get("content", "")).decode("utf-8")
                
                # title және package.name жолдарын ауыстыру
                spec_text = re.sub(r'^title\s*=\s*.*$', f'title = {app_title}', spec_text, flags=re.MULTILINE)
                spec_text = re.sub(r'^package\.name\s*=\s*.*$', f'package.name = {safe_pkg_name}', spec_text, flags=re.MULTILINE)
                
                base64_spec = base64.b64encode(spec_text.encode("utf-8")).decode("utf-8")
                payload_spec = {"message": f"Jimi: {app_title} үшін атауды өзгерту", "content": base64_spec, "sha": spec_sha}
                
                put_spec = requests.put(url_spec, headers=headers, json=payload_spec, timeout=15)
                if put_spec.status_code in [200, 201]:
                    Clock.schedule_once(lambda dt: self.update_btn_status("АТЫ ӨЗГЕРДІ ЖӘНЕ ЖЕТТІ! 🔥"), 0)
                else:
                    Clock.schedule_once(lambda dt: self.update_btn_status("Гитхабқа жетті, аты өзгермеді."), 0)
            else:
                Clock.schedule_once(lambda dt: self.update_btn_status("ГИТХАБҚА ЖЕТТІ! (buildozer.spec табылмады)"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.update_btn_status("ГИТХАБҚА ЖЕТТІ! (атын өзгертуде қате)"), 0)

    def update_btn_status(self, text):
        self.build_btn.text = text
        self.build_btn.disabled = False

class FolderScreen(DarkScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_box = BoxLayout(orientation='vertical', padding=10, spacing=10)
        back_btn = Button(text="Жобаға қайту", size_hint_y=None, height="50dp", background_color=(0.2, 0.5, 0.8, 1), on_release=self.go_back)
        self.main_box.add_widget(back_btn)
        self.status_lbl = Label(text="Дайын APK тексерілуде... 🔄", size_hint_y=None, height="30dp")
        self.main_box.add_widget(self.status_lbl)
        scroll = ScrollView(size_hint_y=1.0)
        self.list_view = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10, padding=10)
        self.list_view.bind(minimum_height=self.list_view.setter('height'))
        scroll.add_widget(self.list_view)
        self.main_box.add_widget(scroll)
        self.add_widget(self.main_box)
        
    def check_github_artifacts(self):
        self.list_view.clear_widgets()
        threading.Thread(target=self.fetch_artifacts_from_github).start()

    def fetch_artifacts_from_github(self):
        token = get_setting(GITHUB_TOKEN_FILE)
        username = get_setting(USER_FILE)
        repo = get_setting(REPO_FILE)
        if not token or not username or not repo: return

        url = f"https://api.github.com/repos/{username}/{repo}/actions/artifacts"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                artifacts = res.json().get("artifacts", [])
                if artifacts: Clock.schedule_once(lambda dt: self.display_artifacts(artifacts, username, repo), 0)
                else: Clock.schedule_once(lambda dt: self.show_status("Дайын APK жоқ."), 0)
        except: pass

    def show_status(self, text): self.status_lbl.text = text

    def display_artifacts(self, artifacts, username, repo):
        self.status_lbl.text = "Дайын файлдар табылды! 👇"
        for art in artifacts:
            art_name = art.get("name", "app-debug")
            run_id = art.get("workflow_run", {}).get("id", "")
            download_page_url = f"https://github.com/{username}/{repo}/actions/runs/{run_id}"
            box = BoxLayout(orientation='horizontal', size_hint_y=None, height="50dp", spacing=5)
            lbl = Label(text=f"📦 {art_name}.zip")
            btn = Button(text="🔗 СЫЛТЕМЕ", size_hint_x=None, width="110dp", background_color=(0.2, 0.6, 1, 1))
            btn.bind(on_release=lambda instance, url=download_page_url: webbrowser.open(url))
            box.add_widget(lbl); box.add_widget(btn)
            self.list_view.add_widget(box)

    def go_back(self, instance):
        self.manager.transition.direction = "up"; self.manager.current = "chat_screen"

class MainApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(ChatScreen(name="chat_screen"))
        sm.add_widget(SettingsScreen(name="settings_screen"))
        sm.add_widget(TestScreen(name="test_screen"))
        sm.add_widget(FolderScreen(name="folder_screen"))
        return sm

if __name__ == "__main__":
    MainApp().run()
