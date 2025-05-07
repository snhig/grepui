from pathlib import Path
import sys, re
import subprocess
import os
 
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,QListWidgetItem, QRadioButton, QButtonGroup,
    QLineEdit, QCheckBox, QLabel, QFileDialog, QPlainTextEdit, QApplication, QMenu, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QPoint, QThreadPool, QThread 
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from search_worker import SearchWorker
# Import your provided function
from file_searcher import find_files
class SearchViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GREPui - Recursive Substring Finder")
        self.resize(1000, 700)
        self.match_positions = []
        self.current_match_index = -1
        # Layouts
        main_layout = QVBoxLayout(self)
        controls_layout = QVBoxLayout()
        search_layout = QHBoxLayout()
        dir_layout = QHBoxLayout()

        # --- Top Controls
        self.dir_edit = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.regex_radio = QRadioButton("Regex")
        self.substring_radio = QRadioButton("Substring")
        self.substring_radio.setChecked(True)  # default
        dir_layout.addWidget(self.browse_button)
        dir_layout.addWidget(self.dir_edit)
        
        # Search substing radio button layout

        self.search_mode_group = QButtonGroup()
        self.search_mode_group.addButton(self.regex_radio)
        self.search_mode_group.addButton(self.substring_radio)

        substring_layout = QVBoxLayout()
        radiobutton_layout = QHBoxLayout()
        substring_layout.addLayout(radiobutton_layout)
        self.case_checkbox = QCheckBox("Case Insensitive")
        self.case_checkbox.setChecked(True)  # Default to checked
        radiobutton_layout.addWidget(self.substring_radio)
        radiobutton_layout.addWidget(self.regex_radio)
        radiobutton_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.substring_edit = QLineEdit()
        self.substring_edit.setPlaceholderText("Substring or Regex to find...")
        substring_layout.addWidget(self.case_checkbox)
        substring_layout.addWidget(self.substring_edit)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Optional file extension (e.g., .txt)")
        self.recursive_checkbox = QCheckBox("Recursive")
        self.recursive_checkbox.setChecked(True)
        self.search_button = QPushButton("Search")

        substring_layout.addWidget(QLabel("Search Mode:"))
        controls_layout.addLayout(substring_layout)
        controls_layout.addWidget(QLabel("Directory:"))
        controls_layout.addLayout(dir_layout)
        controls_layout.addWidget(QLabel("Extension:"))
        controls_layout.addWidget(self.filter_edit)
        controls_layout.addWidget(self.recursive_checkbox)
        controls_layout.addWidget(self.search_button)

        

 
        # --- Search Results Area
        self.file_list = QListWidget()
        self.text_preview = QPlainTextEdit()
        _font = QFont("Consolas")
        _font.setStyleHint(QFont.Monospace)
        self.text_preview.setFont(_font)
        
        self.text_preview.setReadOnly(True)
 
        search_layout.addWidget(self.file_list, 2)
        search_layout.addWidget(self.text_preview, 3)
 
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(search_layout)

        self.stale_label = QLabel("")
        self.stale_label.setStyleSheet("color: orange; font-style: italic;")
        controls_layout.addWidget(self.stale_label)

        self.next_button = QPushButton("▶")
        self.prev_button = QPushButton("◀")

        for btn in (self.next_button, self.prev_button):
            btn.setFixedSize(20, 20)
            btn.setStyleSheet("""
                QPushButton {
                    border-radius: 10px;
                    background-color: #007ACC;
                    color: white;
                    font-weight: bold;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background-color: #005A9E;
                }
            """)

        self.next_button.setToolTip("Go to next match")
        self.prev_button.setToolTip("Go to previous match")

        nav_button_layout = QHBoxLayout()
        nav_button_layout.addWidget(self.prev_button)
        nav_button_layout.addWidget(self.next_button)
        nav_button_layout.addStretch()

        text_layout = QVBoxLayout()
        text_layout.addWidget(self.text_preview)
        text_layout.addLayout(nav_button_layout)

        search_layout.addWidget(self.file_list, 2)
        search_layout.addLayout(text_layout, 3)

 
        # --- Connections
        self.browse_button.clicked.connect(self.browse_directory)
        self.search_button.clicked.connect(self.perform_search)
        self.file_list.itemClicked.connect(self.display_file_content)
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.show_context_menu)

        self.dir_edit.textChanged.connect(self.mark_results_stale)
        self.substring_edit.textChanged.connect(self.mark_results_stale)
        self.filter_edit.textChanged.connect(self.mark_results_stale)
        self.recursive_checkbox.stateChanged.connect(self.mark_results_stale)
        self.case_checkbox.stateChanged.connect(self.mark_results_stale)
        self.regex_radio.toggled.connect(self.mark_results_stale)
        self.substring_radio.toggled.connect(self.mark_results_stale)

        self.next_button.clicked.connect(self.goto_next_match)
        self.prev_button.clicked.connect(self.goto_prev_match)
        
    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.dir_edit.setText(directory)
    
    def mark_results_stale(self):
        self.stale_label.setText("⚠ Results not refreshed. Click 'Search' to update.")

    def on_search_finished(self, matches):
        self.file_list.clear()
        for match_path, count in matches:
            itm = FpItem(str(match_path), count)
            self.file_list.addItem(itm)
        self.stale_label.setText(f"✅ Found {len(matches)} matching files.")

    def on_search_error(self, message):
        self.stale_label.setText(f"❌ Search error: {message}")

    def perform_search(self):
        self.text_preview.clear()
        directory = self.dir_edit.text().strip()
        substring = self.substring_edit.text().strip()
        extension = self.filter_edit.text().strip()
        recursive = self.recursive_checkbox.isChecked()
        use_regex = self.regex_radio.isChecked()
        case_insensitive = self.case_checkbox.isChecked()

        if not directory or not substring:
            return

        root_path = Path(directory)
        if not root_path.is_dir():
            return

        self.file_list.clear()
        self.stale_label.setText("🔍   Searching...")

        # Run in background
        worker = SearchWorker(
            root_path, extension, substring, use_regex,
            recursive, case_insensitive, find_files
        )
        worker.signals.finished.connect(self.on_search_finished)
        worker.signals.error.connect(self.on_search_error)

        QThreadPool.globalInstance().start(worker)

    
    def display_file_content(self, item):
        file_path = Path(item.fp)
        if not file_path.is_file():
            return
 
        substring = self.substring_edit.text().strip()
        if not substring:
            return
 
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            self.text_preview.setPlainText(f"Error reading file:\n{e}")
            return
 
        self.text_preview.setPlainText(content)
        self.highlight_matches(substring)
 
    def highlight_matches(self, pattern_str):
        use_regex = self.regex_radio.isChecked()
        case_insensitive = self.case_checkbox.isChecked()
        content = self.text_preview.toPlainText()

        # Clear existing formatting
        cursor = self.text_preview.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.Start)
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())  # Clear all formatting
        cursor.endEditBlock()

        # Prepare highlight format
        format = QTextCharFormat()
        format.setBackground(QColor("lightblue"))

        # Reset match tracking
        self.match_positions = []
        self.current_match_index = -1

        cursor = self.text_preview.textCursor()
        cursor.movePosition(QTextCursor.Start)

        if use_regex:
            try:
                flags = re.IGNORECASE if case_insensitive else 0
                pattern = re.compile(pattern_str, flags)
            except re.error as e:
                self.text_preview.setPlainText(f"Regex error:\n{e}")
                return

            for match in pattern.finditer(content):
                start, end = match.span()
                self.match_positions.append((start, end))  # Track match
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                cursor.mergeCharFormat(format)

        else:
            search_term = pattern_str
            if case_insensitive:
                search_term = pattern_str.lower()
                content_to_search = content.lower()
            else:
                content_to_search = content

            position = 0
            while position < len(content_to_search):
                index = content_to_search.find(search_term, position)
                if index == -1:
                    break
                self.match_positions.append((index, index + len(pattern_str)))  # Track match
                cursor.setPosition(index)
                cursor.setPosition(index + len(pattern_str), QTextCursor.KeepAnchor)
                cursor.mergeCharFormat(format)
                position = index + len(pattern_str)


    def goto_next_match(self):
        if not self.match_positions:
            return
        self.current_match_index = (self.current_match_index + 1) % len(self.match_positions)
        self.scroll_to_match(self.current_match_index)

    def goto_prev_match(self):
        if not self.match_positions:
            return
        self.current_match_index = (self.current_match_index - 1 + len(self.match_positions)) % len(self.match_positions)
        self.scroll_to_match(self.current_match_index)

    def scroll_to_match(self, index):
        start, end = self.match_positions[index]
        cursor = self.text_preview.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.text_preview.setTextCursor(cursor)
        self.text_preview.ensureCursorVisible()

    def show_context_menu(self, pos: QPoint):
        item = self.file_list.itemAt(pos)
        if item:
            menu = QMenu()
            open_action = menu.addAction(f"Open in File Explorer")
            copy_path_action = menu.addAction(f"Copy File Path to Clipboard :: {item.fp}")  # NEW

            action = menu.exec_(self.file_list.mapToGlobal(pos))
            if action == open_action:
                self.open_in_file_explorer(item.fp)
            elif action == copy_path_action:  # NEW
                self.copy_file_path_to_clipboard(item.fp)
    
    def copy_file_path_to_clipboard(self, filepath):
        clipboard = QApplication.clipboard()
        clipboard.setText(f'{filepath}')

    def open_in_file_explorer(self, filepath):
        path = Path(filepath)
        if not path.exists():
            return
 
        if sys.platform == "win32":
            # Windows: explorer and highlight the file
            subprocess.run(["explorer", "/select,", str(path)])
        elif sys.platform == "darwin":
            # macOS: open and reveal
            subprocess.run(["open", "-R", str(path)])
        else:
            # Linux: xdg-open folder (cannot highlight a specific file)
            subprocess.run(["xdg-open", str(path.parent)])
 
# --------
class FpItem(QListWidgetItem):
    def __init__(self, fp: str, match_count: int):
        self.fp = fp
        self.my_text = f"{os.path.basename(fp)}  ({match_count} matches)"
        super().__init__(self.my_text)


# For testing standalone
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # app.setStyle('windowsvista')
    widget = SearchViewerWidget()
    widget.show()
    sys.exit(app.exec())