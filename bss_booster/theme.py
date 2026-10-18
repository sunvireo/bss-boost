"""Reference-inspired light UI and optional dark appearance."""

def stylesheet(mode: str = "Light") -> str:
    dark = mode == "Dark"
    bg = "#191c26" if dark else "#faf4f3"
    paper = "#252a38" if dark else "#ffffff"
    ink = "#f4f3f7" if dark else "#23232a"
    muted = "#a6a4b5" if dark else "#71717e"
    border = "#393e4c" if dark else "#e9e5e8"
    soft = "#313547" if dark else "#f6f4f7"
    purple = "#5900bb"
    purple_hover = "#7325d3"
    return f'''
QWidget {{ color: {ink}; font-family: "Segoe UI", Arial; font-size: 12px; }}
QWidget#Root {{ background: {bg}; }}
QWidget#TopBar, QWidget#BottomBar {{ background: {paper}; }}
QWidget#TopBar {{ border-bottom: 1px solid {border}; }}
QWidget#BottomBar {{ border-top: 1px solid {border}; }}
QWidget#PageBody, QScrollArea#PageScroll, QScrollArea#PageScroll > QWidget > QWidget {{ background: {bg}; }}
QFrame#Panel, QFrame#AlarmCard, QFrame#SlotRow {{ background: {paper}; border: 1px solid {border}; border-radius: 13px; }}
QFrame#SlotTile {{ background: {paper}; border: 1px solid {border}; border-radius: 12px; }}
QPushButton#HotbarKey[selected="true"] {{ border: 2px solid {purple}; background: {'#342a4a' if dark else '#f8f1ff'}; }}
QLabel#Title {{ font-size: 25px; font-weight: 700; }}
QLabel#Subtitle {{ font-size: 12px; color: {muted}; }}
QLabel#Eyebrow {{ font-size: 10px; font-weight: 700; color: {purple if not dark else '#ba9cf8'}; }}
QLabel#SectionTitle {{ font-size: 15px; font-weight: 700; }}
QLabel#Muted {{ color: {muted}; }}
QLabel#Count {{ font-size: 20px; font-weight: 700; }}
QLabel#Timer {{ font-size: 18px; font-weight: 700; color: {purple if not dark else '#d0b4ff'}; }}
QPushButton {{ padding: 9px 13px; border: 1px solid {border}; border-radius: 9px; background: {paper}; font-weight: 600; }}
QPushButton:hover {{ background: {soft}; border-color: {'#747080' if dark else '#cbc2d5'}; }}
QPushButton:pressed {{ background: {'#433552' if dark else '#e9ddf7'}; }}
QPushButton:disabled {{ color: {muted}; background: {soft}; border-color: {border}; }}
QPushButton#HotbarKey {{ font-size: 12px; font-weight: 700; padding: 6px; background: {paper}; border-radius: 12px; border: 1px solid {border}; }}
QPushButton#Primary {{ background: {purple}; color: white; border: 1px solid {purple}; }}
QPushButton#Primary:hover {{ background: {purple_hover}; border-color: {purple_hover}; }}
QPushButton#Primary:disabled {{ background: {soft}; color: {muted}; border-color: {border}; }}
QPushButton#SoftPurple {{ background: {'#3b2854' if dark else '#f0e6ff'}; color: {'#d7bbff' if dark else purple}; border: 1px solid {'#66488e' if dark else '#e4d3fb'}; }}
QPushButton#Danger {{ color: {'#ffadb0' if dark else '#b83448'}; }}
QPushButton#NavTab {{ border: none; border-radius: 0; background: transparent; padding: 13px 15px; font-weight: 600; }}
QPushButton#NavTab:hover {{ background: {soft}; }}
QPushButton#NavTab[active="true"] {{ background: {'#42314d' if dark else '#f0e8f7'}; color: {'#d3b3ff' if dark else purple}; border-bottom: 3px solid {purple}; }}
QPushButton#AddButton {{ border: none; border-radius: 20px; background: {purple}; color: white; font-size: 23px; font-weight: 400; padding: 0; }}
QPushButton#AddButton:hover {{ background: {purple_hover}; }}
QLineEdit, QKeySequenceEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {paper}; border: 1px solid {border}; border-radius: 8px; padding: 8px; min-height: 20px; selection-background-color: {purple}; }}
QLineEdit:focus, QKeySequenceEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {purple}; }}
QComboBox QAbstractItemView {{ background: {paper}; color: {ink}; selection-background-color: {purple}; selection-color: white; border: 1px solid {border}; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {border}; border-radius: 4px; background: {paper}; }}
QCheckBox::indicator:checked {{ background: {purple}; border-color: {purple}; image: none; }}
QSlider::groove:horizontal {{ background: {border}; border-radius: 3px; height: 6px; }}
QSlider::handle:horizontal {{ background: {purple}; width: 16px; margin: -5px 0; border-radius: 8px; }}
QSlider::sub-page:horizontal {{ background: {purple}; border-radius: 3px; }}
QScrollBar:vertical {{ background: transparent; width: 9px; }}
QScrollBar::handle:vertical {{ background: {'#505769' if dark else '#d7d0da'}; min-height: 25px; border-radius: 4px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QPlainTextEdit {{ background: {paper}; border: 1px solid {border}; border-radius: 11px; padding: 10px; }}
QToolTip {{ background: {paper}; color: {ink}; border: 1px solid {border}; padding: 6px; }}
'''
