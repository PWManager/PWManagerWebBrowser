import sys
import threading
from PyQt6.QtCore import QUrl, QThread
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QWidget, QTabWidget, QFileDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
import win32api
import os
from urllib.parse import quote
from flask import Flask, render_template_string, request
from random import randint

class server():
    def __init__(self):
        self.port = randint(5000, 9999)
        self.app = Flask(__name__)
        print(f"Server is starting on port {self.port}")

        @self.app.route('/')
        def index():
            return render_template_string(open('pages/search/index.html', encoding="utf-8").read())
        
        @self.app.route('/style.css')
        def style():
            return self.app.response_class(open('pages/search/style.css', encoding="utf-8").read(), mimetype="text/css")

    def start(self):
        print("Starting server...")
        self.app.run(port=self.port)

    def get_url(self):
        return "http://localhost:" + str(self.port)

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()

        pages_host = server()
        self.url = pages_host.get_url()

        pages_thread = threading.Thread(target=pages_host.start, daemon=True)
        pages_thread.start()

        self.setWindowTitle("PWManager Web Browser")
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(800, 600)

        # Контейнер для UI
        self.container = QWidget(self)
        self.setCentralWidget(self.container)
        self.layout = QVBoxLayout(self.container)

        # Панель инструментов с кнопками навигации
        self.toolbar = QHBoxLayout()
        self.back_button = QPushButton("Back", self)
        self.forward_button = QPushButton("Forward", self)
        self.reload_button = QPushButton("Reload", self)
        self.new_tab_button = QPushButton("New Tab", self)
        self.close_tab_button = QPushButton("Close Tab", self)

        # Кнопки для панели инструментов
        self.toolbar.addWidget(self.back_button)
        self.toolbar.addWidget(self.forward_button)
        self.toolbar.addWidget(self.reload_button)
        self.toolbar.addWidget(self.new_tab_button)
        self.toolbar.addWidget(self.close_tab_button)

        self.layout.addLayout(self.toolbar)

        # Поле ввода URL
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Enter URL or FTP path")
        self.url_input.setText("Search")
        self.layout.addWidget(self.url_input)

        # Добавление виджета для вкладок
        self.tabs = QTabWidget(self)
        self.layout.addWidget(self.tabs)

        # Создаем начальную вкладку
        self.create_new_tab()

        # Связываем события с функциями
        self.back_button.clicked.connect(self.back)
        self.forward_button.clicked.connect(self.forward)
        self.reload_button.clicked.connect(self.reload)
        self.new_tab_button.clicked.connect(self.create_new_tab)
        self.close_tab_button.clicked.connect(self.close_current_tab)

        # Обработчики изменения URL
        self.url_input.returnPressed.connect(self.navigate)

        # Обновляем поле ввода URL, когда меняется адрес в браузере
        self.tabs.currentChanged.connect(self.update_url_input)

    def create_new_tab(self):
        # Создание новой вкладки
        browser_view = QWebEngineView(self)

        # Запускаем сервер в отдельном потоке
        browser_view.setUrl(QUrl(self.url))

        version = win32api.GetVersionEx()

        # Устанавливаем кастомный User-Agent
        browser_view.page().profile().setHttpUserAgent(
            f"Mozilla/5.0 (Windows NT {version[0]}.{version[1]}; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) PWManagerWebBrowser/1.0"
        )

        browser_view.page().profile().setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        browser_view.page().profile().setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)

        # Обработчик события скачивания файла
        browser_view.page().profile().downloadRequested.connect(self.handle_download_requested)

        # Добавляем вкладку в QTabWidget
        tab_name = "New Tab"
        index = self.tabs.addTab(browser_view, tab_name)
        self.tabs.setCurrentIndex(index)

        # Обновляем URL-поле при смене вкладки
        browser_view.urlChanged.connect(lambda qurl: self.update_url_input(qurl))

        # Привязываем события навигации к действиям (это необходимо для того, чтобы ссылки открывались)
        browser_view.page().urlChanged.connect(self.on_link_clicked)

    def handle_download_requested(self, download):
        """Обработчик события скачивания файла."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", download.url().path().split('/')[-1])

        if file_path:
            download.setDownloadDirectory(os.path.dirname(file_path))  # Устанавливаем директорию для сохранения файла
            download.setDownloadFileName(os.path.basename(file_path))  # Устанавливаем имя файла
            download.accept()  # Начинаем скачивание файла

    def back(self):
        current_browser = self.current_browser()
        if current_browser:
            current_browser.back()

    def forward(self):
        current_browser = self.current_browser()
        if current_browser:
            current_browser.forward()

    def reload(self):
        current_browser = self.current_browser()
        if current_browser:
            current_browser.reload()

    def on_link_clicked(self, qurl):
        """Обработка кликов по ссылкам в браузере."""
        current_browser = self.current_browser()
        if current_browser:
            current_browser.setUrl(qurl)

    def navigate(self):
        """Обработчик перехода по URL."""
        url = self.url_input.text()
        if url:
            current_browser = self.current_browser()
            if current_browser:
                current_browser.setUrl(QUrl(url))

    def update_url_input(self, qurl):
        """Обновление поля ввода URL, когда URL в браузере меняется."""
        if isinstance(qurl, QUrl):  # Проверяем, что qurl — это объект QUrl
            self.url_input.setText(qurl.toString())

    def close_current_tab(self):
        """Закрыть текущую вкладку."""
        current_index = self.tabs.currentIndex()
        if current_index != -1:
            self.tabs.removeTab(current_index)

    def current_browser(self):
        """Получить текущий веб-браузер на активной вкладке."""
        current_index = self.tabs.currentIndex()
        return self.tabs.widget(current_index)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = Browser()
    window.show()
    sys.exit(app.exec())
