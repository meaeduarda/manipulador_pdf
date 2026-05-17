import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QScrollArea, QLineEdit, QMessageBox, QFrame,
    QColorDialog, QSlider, QGroupBox, QDialog, QGridLayout,
    QTextEdit, QInputDialog, QListWidget, QListWidgetItem
)
from PyQt5.QtGui import QPixmap, QImage, QFont, QColor, QPainter, QPen, QBrush, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPoint, QSize
import fitz  
import PyPDF2
import os
import json
import logging
import shutil
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Função auxiliar para carregar ícone
def load_icon():
    """Tenta carregar o ícone de várias formas diferentes"""
    possible_paths = [
        "VisualizadorPdf.ico",
        "VisualizadorPdf.png",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "VisualizadorPdf.png"),
        "VisualizadorPdf.jpg",
        "VisualizadorPdf.jpeg",
        "VisualizadorPdf.ico",
        "VisualizadorPdf.bmp",
        "icon.png",
        "./icon.png",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                logger.info(f"Tentando carregar ícone de: {path}")
                icon = QIcon(path)
                if not icon.isNull():
                    logger.info(f"Ícone carregado com sucesso de: {path}")
                    return icon
            except Exception as e:
                logger.warning(f"Erro ao carregar ícone de {path}: {e}")
    

    logger.info("Procurando por qualquer imagem PNG/JPG/ICO na raiz...")
    try:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        for file in os.listdir(root_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.ico', '.bmp')):
                path = os.path.join(root_dir, file)
                try:
                    icon = QIcon(path)
                    if not icon.isNull():
                        logger.info(f"Usando ícone encontrado: {file}")
                        return icon
                except:
                    continue
    except Exception as e:
        logger.error(f"Erro ao procurar imagens: {e}")
    
    logger.warning("Nenhum ícone encontrado, usando ícone padrão do Qt")
    return QIcon()  # Ícone vazio (padrão)


class HighlighterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Marcador")
        self.setMinimumSize(300, 200)
        
        # Configurar ícone
        self.setWindowIcon(APP_ICON)

        layout = QVBoxLayout(self)

        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Cor:"))
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(40, 40)
        self.current_color = QColor(255, 255, 0)
        self.update_color_button()
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        layout.addLayout(color_layout)

        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacidade:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(50)
        self.opacity_label = QLabel("50%")
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        layout.addLayout(opacity_layout)

        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def update_color_button(self):
        self.color_btn.setStyleSheet(
            f"background-color: {self.current_color.name()}; border: 1px solid #000;"
        )

    def choose_color(self):
        color = QColorDialog.getColor(self.current_color, self, "Escolha a cor do marcador")
        if color.isValid():
            self.current_color = color
            self.update_color_button()

    def update_opacity_label(self, value):
        self.opacity_label.setText(f"{value}%")

    def get_settings(self):
        return {
            'color': self.current_color,
            'opacity': self.opacity_slider.value() / 100.0
        }


class InsertPagesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Inserir Páginas de Outro PDF")
        self.setMinimumSize(500, 400)
        
        # Configurar ícone
        self.setWindowIcon(APP_ICON)

        layout = QVBoxLayout(self)

        # PDF de origem
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("PDF de origem:"))
        self.source_pdf_label = QLabel("Nenhum arquivo selecionado")
        self.source_pdf_label.setWordWrap(True)
        self.source_pdf_label.setStyleSheet("border: 1px solid #ccc; padding: 4px; background: #f8f8f8;")
        source_layout.addWidget(self.source_pdf_label, 1)
        self.btn_select_source = QPushButton("Selecionar PDF")
        self.btn_select_source.clicked.connect(self.select_source_pdf)
        source_layout.addWidget(self.btn_select_source)
        layout.addLayout(source_layout)

        # Páginas disponíveis
        layout.addWidget(QLabel("Páginas disponíveis no PDF selecionado:"))

        self.pages_list = QListWidget()
        self.pages_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.pages_list)

        # Opções de inserção
        options_group = QGroupBox("Opções de Inserção")
        options_layout = QVBoxLayout()

        # Posição de inserção
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Inserir após a página:"))
        self.position_spin = QLineEdit("1")
        self.position_spin.setFixedWidth(50)
        pos_layout.addWidget(self.position_spin)
        pos_layout.addWidget(QLabel("(0 = início, -1 = final)"))
        pos_layout.addStretch()
        options_layout.addLayout(pos_layout)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Botões de ação
        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Selecionar Todas")
        self.btn_select_all.clicked.connect(self.select_all_pages)
        btn_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deselecionar Todas")
        self.btn_deselect_all.clicked.connect(self.deselect_all_pages)
        btn_layout.addWidget(self.btn_deselect_all)
        layout.addLayout(btn_layout)

        # Botões OK/Cancel
        dialog_btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Inserir Selecionadas")
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.setEnabled(False)
        dialog_btn_layout.addWidget(self.btn_ok)
        dialog_btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(dialog_btn_layout)

        self.source_pdf_path = None
        self.source_doc = None

    def select_source_pdf(self):
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("PDF Files (*.pdf)")
        file_dialog.setWindowTitle("Selecione um arquivo PDF para inserir páginas")
        if file_dialog.exec_():
            pdf_path = file_dialog.selectedFiles()[0]
            try:
                self.source_pdf_path = pdf_path
                self.source_doc = fitz.open(pdf_path)
                self.source_pdf_label.setText(os.path.basename(pdf_path))
                self.update_pages_list()
                self.btn_ok.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Não foi possível abrir o PDF: {e}")
                self.source_pdf_path = None
                self.source_doc = None
                self.source_pdf_label.setText("Nenhum arquivo selecionado")
                self.pages_list.clear()
                self.btn_ok.setEnabled(False)

    def update_pages_list(self):
        self.pages_list.clear()
        if self.source_doc:
            for i in range(len(self.source_doc)):
                item_text = f"Página {i+1}"
           
                try:
                    page = self.source_doc.load_page(i)
                    text = page.get_text("text").strip()[:100]
                    if text:
                        item_text += f" - {text}"
                except:
                    pass
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, i)  
                self.pages_list.addItem(item)

    def select_all_pages(self):
        for i in range(self.pages_list.count()):
            item = self.pages_list.item(i)
            item.setSelected(True)

    def deselect_all_pages(self):
        for i in range(self.pages_list.count()):
            item = self.pages_list.item(i)
            item.setSelected(False)

    def get_selection(self):
        selected_pages = []
        for item in self.pages_list.selectedItems():
            page_idx = item.data(Qt.UserRole)
            selected_pages.append(page_idx)
        return sorted(selected_pages)

    def get_insert_position(self):
        try:
            pos_text = self.position_spin.text().strip()
            if pos_text == "-1":
                return -1  # Final do documento
            pos = int(pos_text) - 1
            return max(0, pos)
        except:
            return 0  # Início por padrão


class PDFStartScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manipulador de PDF")
        self.setMinimumSize(480, 200)
        
        # Configurar ícone
        self.setWindowIcon(APP_ICON)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel("Bem-vindo ao Manipulador de PDF!")
        self.label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.btn_open = QPushButton("Abrir PDF")
        self.btn_open.setFixedWidth(160)
        layout.addWidget(self.btn_open, alignment=Qt.AlignCenter)

        self.path_label = QLabel("")
        self.path_label.setAlignment(Qt.AlignCenter)
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        self.pdf_path = None

    def set_pdf_path(self, path):
        self.pdf_path = path
        self.path_label.setText(
            f"Arquivo selecionado:\n{os.path.basename(path)}\n{path}"
        )


class PDFManipulatorApp(QMainWindow):
    def __init__(self, pdf_path):
        super().__init__()
        self.setWindowTitle(f"Manipulador de PDF - {pdf_path.split('/')[-1]}")
        self.resize(1100, 800)
        
        # Configurar ícone
        self.setWindowIcon(APP_ICON)
        
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.num_pages = len(self.doc)
        self.current_page = 0
        self.thumb_cache = {}
        self.unsaved_changes = False
        self.highlighting_enabled = False
        self.text_selection_mode = False
        self.text_editing_mode = False
        self.current_highlight_settings = {'color': QColor(255, 255, 0), 'opacity': 0.5}
        self.highlights = self.load_highlights()


        self.text_spans = []

        # Estado de seleção
        self.mouse_pressed = False
        self.selection_start = None   
        self.selection_end = None     
        self.selected_spans = []      
        self.selected_text_content = ""

        # Layout principal
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # Lateral esquerda (botões e campos)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(18)

        # Barra de navegação de páginas
        nav_layout = QHBoxLayout()
        self.page_info_label = QLabel(self.page_info_text())
        self.page_info_label.setMinimumWidth(120)
        self.page_info_label.setAlignment(Qt.AlignCenter)
        self.page_info_label.setStyleSheet("""
            border: 2px solid #27ae60;
            border-radius: 6px;
            font-weight: bold;
            padding: 4px 12px;
            background: #232629;
            color: #00FF00;
        """)
        nav_layout.addWidget(self.page_info_label)

        nav_layout.addStretch(1)

        nav_layout.addWidget(QLabel("Ir para pág.:"))
        self.page_jump_entry = QLineEdit()
        self.page_jump_entry.setFixedWidth(40)
        nav_layout.addWidget(self.page_jump_entry)
        btn_jump = QPushButton("Ir")
        btn_jump.setFixedWidth(40)
        btn_jump.clicked.connect(self.jump_to_page)
        nav_layout.addWidget(btn_jump)
        left_panel.addLayout(nav_layout)

        # --- NOVO: Grupo de Gerenciamento de Páginas ---
        pages_group = QGroupBox("Gerenciar Páginas")
        pages_layout = QVBoxLayout()

        # Botão para inserir páginas de outro PDF
        btn_insert_pages = QPushButton("Inserir Páginas de Outro PDF")
        btn_insert_pages.clicked.connect(self.insert_pages_from_pdf)
        pages_layout.addWidget(btn_insert_pages)

        # Botão para remover página atual
        btn_remove_current = QPushButton("Remover Página Atual")
        btn_remove_current.clicked.connect(self.remove_current_page)
        pages_layout.addWidget(btn_remove_current)

        # Botão para remover intervalo de páginas
        btn_remove_range = QPushButton("Remover Intervalo de Páginas...")
        btn_remove_range.clicked.connect(self.remove_page_range)
        pages_layout.addWidget(btn_remove_range)

        # Botão para extrair página atual como novo PDF
        btn_extract_page = QPushButton("Extrair Página Atual como PDF")
        btn_extract_page.clicked.connect(self.extract_current_page)
        pages_layout.addWidget(btn_extract_page)

        pages_group.setLayout(pages_layout)
        left_panel.addWidget(pages_group)

        # --- Grupo de Trabalho com Texto ---
        text_group = QGroupBox("Trabalhar com Texto")
        text_layout = QVBoxLayout()

        # Botão para ativar/desativar seleção de texto
        self.btn_toggle_text_selection = QPushButton("Ativar Seleção de Texto")
        self.btn_toggle_text_selection.setCheckable(True)
        self.btn_toggle_text_selection.toggled.connect(self.toggle_text_selection)
        text_layout.addWidget(self.btn_toggle_text_selection)

        # Botão para marcar texto selecionado
        btn_highlight_text = QPushButton("Marcar Texto Selecionado")
        btn_highlight_text.clicked.connect(self.highlight_selected_text)
        text_layout.addWidget(btn_highlight_text)

        text_group.setLayout(text_layout)
        left_panel.addWidget(text_group)

        # --- Grupo de Marcador de Texto ---
        highlighter_group = QGroupBox("Marcador de Texto")
        highlighter_layout = QVBoxLayout()

        # Botão para configurar marcador
        btn_config = QPushButton("Configurar Marcador")
        btn_config.clicked.connect(self.configure_highlighter)
        highlighter_layout.addWidget(btn_config)

        # Botão para gerenciar marcações
        btn_manage = QPushButton("Gerenciar Marcações")
        btn_manage.clicked.connect(self.manage_highlights)
        highlighter_layout.addWidget(btn_manage)

        # Botão para limpar marcações na página atual
        btn_clear_page = QPushButton("Limpar Marcações desta Página")
        btn_clear_page.clicked.connect(self.clear_page_highlights)
        highlighter_layout.addWidget(btn_clear_page)

        # Botão para limpar todas as marcações
        btn_clear_all = QPushButton("Limpar Todas as Marcações")
        btn_clear_all.clicked.connect(self.clear_all_highlights)
        highlighter_layout.addWidget(btn_clear_all)

        highlighter_group.setLayout(highlighter_layout)
        left_panel.addWidget(highlighter_group)

        # Remover página
        remove_layout = QHBoxLayout()
        self.entry_remove = QLineEdit()
        self.entry_remove.setFixedWidth(40)
        btn_remove = QPushButton("Remover")
        btn_remove.clicked.connect(self.remove_page_by_number)
        remove_layout.addWidget(QLabel("Remover pág.:"))
        remove_layout.addWidget(self.entry_remove)
        remove_layout.addWidget(btn_remove)
        left_panel.addLayout(remove_layout)

        # Mover página
        move_layout = QHBoxLayout()
        self.entry_from = QLineEdit()
        self.entry_from.setFixedWidth(40)
        self.entry_to = QLineEdit()
        self.entry_to.setFixedWidth(40)
        btn_move = QPushButton("Mover")
        btn_move.clicked.connect(self.move_page_custom)
        move_layout.addWidget(QLabel("Mover pág.:"))
        move_layout.addWidget(self.entry_from)
        move_layout.addWidget(QLabel("para:"))
        move_layout.addWidget(self.entry_to)
        move_layout.addWidget(btn_move)
        left_panel.addLayout(move_layout)

        # Mover para cima/baixo
        btn_up = QPushButton("Mover para Cima")
        btn_up.clicked.connect(self.move_page_up)
        left_panel.addWidget(btn_up)
        btn_down = QPushButton("Mover para Baixo")
        btn_down.clicked.connect(self.move_page_down)
        left_panel.addWidget(btn_down)

        # Adicionar numeração
        btn_add_numbers = QPushButton("Adicionar Numeração")
        btn_add_numbers.clicked.connect(self.add_page_numbers)
        left_panel.addWidget(btn_add_numbers)

        # Salvar alterações
        btn_save = QPushButton("Salvar Alterações")
        btn_save.clicked.connect(self.save_pdf)
        left_panel.addWidget(btn_save)

        # Alternar tema
        btn_theme = QPushButton("Alternar Modo Escuro/Claro")
        btn_theme.clicked.connect(self.toggle_theme)
        left_panel.addWidget(btn_theme)

        left_panel.addStretch(1)

        # Visualização da página principal
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setMinimumSize(600, 800)
        self.page_label.setStyleSheet("background: #f0f0f0; border: 1px solid #ccc;")
        self.page_label.setSizePolicy(self.page_label.sizePolicy().horizontalPolicy(), self.page_label.sizePolicy().verticalPolicy())

        # Ativar eventos de mouse para seleção de texto
        self.page_label.mousePressEvent = self.handle_mouse_press
        self.page_label.mouseMoveEvent = self.handle_mouse_move
        self.page_label.mouseReleaseEvent = self.handle_mouse_release

        self.page_pixmap = None
        self.pixmap_rect = None  # Retângulo onde o pixmap é desenhado no label

        # Área de miniaturas
        self.thumb_area = QScrollArea()
        self.thumb_area.setWidgetResizable(True)
        self.thumb_area.setFixedWidth(120)
        self.thumb_widget = QWidget()
        self.thumb_layout = QVBoxLayout(self.thumb_widget)
        self.thumb_layout.setAlignment(Qt.AlignTop)
        self.thumb_area.setWidget(self.thumb_widget)

        # Monta layout principal
        main_layout.addLayout(left_panel, 0)
        main_layout.addWidget(self.page_label, 1)
        main_layout.addWidget(self.thumb_area, 0)

        # Capturar eventos de teclado
        self.thumb_widget.setFocusPolicy(Qt.StrongFocus)
        self.thumb_widget.keyPressEvent = self.handle_thumb_keypress

        self.update_thumbnails()
        self.render_page(0)


    def insert_pages_from_pdf(self):
        """Abre diálogo para inserir páginas de outro PDF"""
        dialog = InsertPagesDialog(self)
        if dialog.exec_():
            try:
                source_pdf_path = dialog.source_pdf_path
                selected_pages = dialog.get_selection()
                insert_position = dialog.get_insert_position()
                
                if not selected_pages:
                    QMessageBox.warning(self, "Nenhuma página selecionada", 
                                      "Por favor, selecione pelo menos uma página para inserir.")
                    return
                
                # Abrir PDF de origem
                source_doc = fitz.open(source_pdf_path)
                
                # Perguntar se quer inserir antes ou depois da posição especificada
                if insert_position >= 0:
                    choices = ["Antes da página", "Depois da página"]
                    choice, ok = QInputDialog.getItem(
                        self, "Posição de Inserção",
                        f"Inserir páginas:", choices, 1, False
                    )
                    if not ok:
                        return
                    
                    # Ajustar posição baseado na escolha
                    insert_idx = insert_position
                    if choice == "Depois da página":
                        insert_idx += 1
                
                else:  #
                    insert_idx = self.num_pages
                
                # Inserir páginas selecionadas
                for page_idx in selected_pages:
                    # Inserir página individualmente
                    if insert_idx <= self.num_pages:
                        self.doc.insert_pdf(source_doc, from_page=page_idx, to_page=page_idx, 
                                          start_at=insert_idx)
                        insert_idx += 1
                    else:
                        # Se tentando inserir após o final, usar append
                        self.doc.insert_pdf(source_doc, from_page=page_idx, to_page=page_idx,
                                          start_at=-1)
                
                source_doc.close()
                
                # Atualizar estado
                self.num_pages = len(self.doc)
                self.thumb_cache.clear()
                self.unsaved_changes = True
                
                # Se inserindo após a página atual, manter a mesma página visível
                if insert_idx > self.current_page:
                    new_page = self.current_page
                else:
                    # Se inserindo antes, ajustar página atual
                    new_page = min(self.current_page + len(selected_pages), self.num_pages - 1)
                
                self.update_thumbnails()
                self.render_page(new_page)
                
                QMessageBox.information(
                    self, "Páginas Inseridas",
                    f"{len(selected_pages)} página(s) inserida(s) com sucesso!\n"
                    f"Total de páginas: {self.num_pages}"
                )
                
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao inserir páginas: {e}")

    def remove_current_page(self):
        """Remove a página atualmente visualizada"""
        try:
            current = self.current_page
            
            if self.num_pages <= 1:
                QMessageBox.warning(self, "Aviso", "Não é possível remover a única página do documento.")
                return
            
            if QMessageBox.question(
                self, "Confirmar Remoção",
                f"Tem certeza que deseja remover a página {current + 1}?",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                
                self.doc.delete_page(current)
                self.num_pages -= 1
                self.thumb_cache.clear()
                self.unsaved_changes = True
                
                # Ajustar página atual se necessário
                new_page = min(current, self.num_pages - 1)
                if new_page < 0:
                    new_page = 0
                
                self.update_thumbnails()
                self.render_page(new_page)
                
                QMessageBox.information(
                    self, "Página Removida",
                    f"Página {current + 1} removida com sucesso!\n"
                    f"Total de páginas: {self.num_pages}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao remover página: {e}")

    def remove_page_range(self):
        """Remove um intervalo de páginas"""
        try:
            # Diálogo para selecionar intervalo
            from_page, ok1 = QInputDialog.getInt(
                self, "Remover Intervalo", 
                "Página inicial:", 1, 1, self.num_pages
            )
            if not ok1:
                return
                
            to_page, ok2 = QInputDialog.getInt(
                self, "Remover Intervalo",
                "Página final:", min(from_page, self.num_pages), 1, self.num_pages
            )
            if not ok2:
                return
            
            # Ajustar índices (0-based)
            from_idx = from_page - 1
            to_idx = to_page - 1
            
            if from_idx > to_idx:
                from_idx, to_idx = to_idx, from_idx
            
            num_to_remove = to_idx - from_idx + 1
            
            if num_to_remove == self.num_pages:
                QMessageBox.warning(self, "Aviso", "Não é possível remover todas as páginas do documento.")
                return
            
            if QMessageBox.question(
                self, "Confirmar Remoção",
                f"Tem certeza que deseja remover as páginas {from_page} a {to_page}?\n"
                f"({num_to_remove} página(s) serão removidas)",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                
                # Remover páginas em ordem reversa para manter índices corretos
                for i in range(to_idx, from_idx - 1, -1):
                    self.doc.delete_page(i)
                
                self.num_pages = len(self.doc)
                self.thumb_cache.clear()
                self.unsaved_changes = True
                
                # Ajustar página atual
                if self.current_page >= from_idx:
                    new_page = max(0, min(self.current_page - num_to_remove, self.num_pages - 1))
                else:
                    new_page = min(self.current_page, self.num_pages - 1)
                
                self.update_thumbnails()
                self.render_page(new_page)
                
                QMessageBox.information(
                    self, "Páginas Removidas",
                    f"{num_to_remove} página(s) removida(s) com sucesso!\n"
                    f"Total de páginas: {self.num_pages}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao remover páginas: {e}")

    def extract_current_page(self):
        """Extrai a página atual como um novo PDF"""
        try:
            # Sugerir nome baseado no PDF original
            base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suggested_name = f"{base_name}_pagina{self.current_page + 1}_{timestamp}.pdf"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Salvar Página como PDF",
                suggested_name, "PDF Files (*.pdf)"
            )
            
            if file_path:
                # Criar novo documento com apenas a página atual
                new_doc = fitz.open()
                new_doc.insert_pdf(self.doc, from_page=self.current_page, to_page=self.current_page)
                new_doc.save(file_path)
                new_doc.close()
                
                QMessageBox.information(
                    self, "Página Extraída",
                    f"Página {self.current_page + 1} extraída com sucesso!\n"
                    f"Arquivo salvo em:\n{file_path}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao extrair página: {e}")


  
    # Conversões de coordenadas

    def screen_to_pixmap_coords(self, screen_point):
        """Converte QPoint nas coordenadas do widget para QPoint nas coordenadas do pixmap (original)."""
        if not self.page_pixmap or not self.pixmap_rect:
            return None

        if not self.pixmap_rect.contains(screen_point):
            return None

        # Posição relativa dentro do pixmap desenhado
        rel_x = (screen_point.x() - self.pixmap_rect.x()) / self.pixmap_rect.width()
        rel_y = (screen_point.y() - self.pixmap_rect.y()) / self.pixmap_rect.height()

        pixmap_size = self.page_pixmap.size()
        pixmap_x = int(rel_x * pixmap_size.width())
        pixmap_y = int(rel_y * pixmap_size.height())

        return QPoint(pixmap_x, pixmap_y)

    def pixmap_to_pdf_rect(self, qrect):
        """Converte um QRect em coordenadas do pixmap para um fitz.Rect nas coordenadas do PDF (usuário escala 1.2)."""
        scale = 1.2
        x0 = qrect.x() / scale
        y0 = qrect.y() / scale
        x1 = (qrect.x() + qrect.width()) / scale
        y1 = (qrect.y() + qrect.height()) / scale
        return fitz.Rect(x0, y0, x1, y1)

  
    # Detecção da estrutura do texto (agora em nível de spans)
 
    def detect_page_structure(self):
        """Detecta spans de texto (cada span com bbox e texto) na página atual.
           Salva em self.text_spans uma lista de dicionários.
        """
        self.text_spans = []
        page = self.doc.load_page(self.current_page)
        text_dict = page.get_text("dict")

        # A escala aplicada quando renderizamos o pixmap é 1.2 — por isso multiplicamos bboxes por esse fator
        scale = 1.2

        for block in text_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        text = span.get("text", "")
                        if not text.strip():
                            continue
                        x0, y0, x1, y1 = span["bbox"]
                        # Converter bbox do PDF para coordenadas do pixmap (inteiras)
                        rect = QRect(int(x0 * scale), int(y0 * scale),
                                     int((x1 - x0) * scale), int((y1 - y0) * scale))
                        pdf_rect = fitz.Rect(x0, y0, x1, y1)
                        self.text_spans.append({
                            'text': text,
                            'rect': rect,
                            'pdf_rect': pdf_rect,
                            'page': self.current_page
                        })

        QMessageBox.information(self, "Estrutura Detectada",
                                f"Foram detectados {len(self.text_spans)} spans de texto nesta página.")
        self.update_page_display()

   
    # Eventos do mouse (seleção)
  
    def handle_mouse_press(self, event):
        if self.text_selection_mode and event.button() == Qt.LeftButton:
            self.mouse_pressed = True
            pixmap_point = self.screen_to_pixmap_coords(event.pos())
            if pixmap_point is None:
                self.selection_start = None
                self.selection_end = None
            else:
                self.selection_start = pixmap_point
                self.selection_end = pixmap_point

            self.selected_spans = []
            self.selected_text_content = ""

            # Garante que tenhamos spans detectados
            if not self.text_spans:
                self.detect_page_structure()

            self.update_page_display()
            event.accept()
        else:
            # Fallback padrão caso seleção não ativa
            QLabel.mousePressEvent(self.page_label, event)

    def handle_mouse_move(self, event):
        if self.text_selection_mode and self.mouse_pressed and self.selection_start:
            pixmap_point = self.screen_to_pixmap_coords(event.pos())
            if pixmap_point is None:
                return

            self.selection_end = pixmap_point
            selection_rect = QRect(self.selection_start, self.selection_end).normalized()

            # Limpa seleção atual
            self.selected_spans = []
            self.selected_text_content = ""

            # Para cada span, verifica interseção com selection_rect
            for span in self.text_spans:
                if selection_rect.intersects(span['rect']):
                    self.selected_spans.append(span)

            # Ordena spans por coordenada x, depois y, para manter a leitura
            self.selected_spans.sort(key=lambda s: (s['rect'].y(), s['rect'].x()))

            # Concatena o texto dos spans selecionados (respeitando ordem)
            texts = [s['text'] for s in self.selected_spans]
            self.selected_text_content = " ".join(t.strip() for t in texts).strip()

            self.update_page_display()
            event.accept()
        else:
            QLabel.mouseMoveEvent(self.page_label, event)

    def handle_mouse_release(self, event):
        if self.text_selection_mode and self.mouse_pressed and event.button() == Qt.LeftButton:
            self.mouse_pressed = False

            if self.selected_text_content:
                text_preview = (self.selected_text_content[:200] + "...") if len(self.selected_text_content) > 200 else self.selected_text_content
                QMessageBox.information(self, "Texto Selecionado",
                                        f"Texto selecionado ({len(self.selected_text_content)} caracteres):\n\n{text_preview}\n\n"
                                        f"Clique em 'Marcar Texto Selecionado' para destacar.")
            else:
                # Limpa seleção se nada foi selecionado
                self.selected_spans = []
                self.selected_text_content = ""

            self.update_page_display()
            event.accept()
        else:
            QLabel.mouseReleaseEvent(self.page_label, event)

    
    # Alternar modo seleção
   
    def toggle_text_selection(self, enabled):
        self.text_selection_mode = enabled
        if enabled:
            self.btn_toggle_text_selection.setText("Desativar Seleção de Texto")
            self.page_label.setCursor(Qt.IBeamCursor)
            # Detecta estrutura se ainda não foi feita
            if not self.text_spans:
                self.detect_page_structure()
        else:
            self.btn_toggle_text_selection.setText("Ativar Seleção de Texto")
            self.page_label.setCursor(Qt.ArrowCursor)
            self.selected_spans = []
            self.selected_text_content = ""
            self.selection_start = None
            self.selection_end = None
            self.mouse_pressed = False

        self.update_page_display()

   
    # Edição de texto (melhorada)
 
    def edit_selected_text(self):
        if not self.selected_spans:
            QMessageBox.warning(self, "Nenhum Texto Selecionado",
                                "Por favor, selecione um texto arrastando o mouse sobre ele no modo 'Seleção de Texto'.")
            return

        dialog = TextEditDialog(self.selected_text_content, self)
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text == self.selected_text_content:
                QMessageBox.information(self, "Sem alterações", "O texto não foi alterado.")
                return

            try:
                page = self.doc.load_page(self.current_page)

                # Calcula o retângulo unificado dos spans selecionados (em coordenadas do pixmap)
                union_rect = None
                for s in self.selected_spans:
                    if union_rect is None:
                        union_rect = QRect(s['rect'])
                    else:
                        union_rect = union_rect.united(s['rect'])

                if union_rect is None:
                    QMessageBox.warning(self, "Erro", "Não foi possível determinar a área para edição.")
                    return

                # Convertendo para coordenadas de PDF
                pdf_redact_rect = self.pixmap_to_pdf_rect(union_rect)

                # Adiciona anotação de redaction e aplica
                page.add_redact_annot(pdf_redact_rect, fill=(1, 1, 1))  # branca por padrão
                page.apply_redactions()

                # Inserir o novo texto: colocamos no canto superior esquerdo do retângulo
                insert_x = pdf_redact_rect.x0
                insert_y = pdf_redact_rect.y0

                # Escolha de fonte/size simples: tentamos inferir um tamanho razoável com base na altura do retângulo
                approx_height = pdf_redact_rect.y1 - pdf_redact_rect.y0
                fontsize = max(8, int(approx_height * 0.8))  # heurística simples

                # Inserir texto (multilinha simples)
                
                text_lines = new_text.splitlines() or [new_text]
                line_height = fontsize * 1.1
                y = insert_y
                for line in text_lines:
                    page.insert_text((insert_x, y), line, fontsize=fontsize, fontname="helv", color=(0, 0, 0))
                    y += line_height

                self.unsaved_changes = True

                # Atualiza estado local
                self.selected_text_content = new_text
                # Substitui textos dos spans selecionados (armazena o novo texto no primeiro span e esvazia os outros)
                if self.selected_spans:
                    self.selected_spans[0]['text'] = new_text
                    for s in self.selected_spans[1:]:
                        s['text'] = ""

                # Re-renderiza a página
                self.render_page(self.current_page)

                QMessageBox.information(self, "Texto Editado",
                                        "Texto editado com sucesso! Clique em 'Salvar Alterações' para gravar no PDF.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao editar texto: {e}")


   
    # Marcar texto selecionado
 
    def highlight_selected_text(self):
        if not self.selected_spans:
            QMessageBox.warning(self, "Nenhum Texto Selecionado",
                                "Por favor, selecione texto primeiro.")
            return

        page_key = str(self.current_page)
        if page_key not in self.highlights:
            self.highlights[page_key] = []

        # Adiciona um highlight para cada span selecionado
        for span in self.selected_spans:
            highlight = {
                'rect': span['rect'],
                'color': self.current_highlight_settings['color'],
                'opacity': self.current_highlight_settings['opacity'],
                'text': span['text']
            }
            self.highlights[page_key].append(highlight)

        self.unsaved_changes = True
        self.save_highlights()
        self.update_page_display()

        QMessageBox.information(
            self, "Texto Marcado",
            f"{len(self.selected_spans)} trecho(s) marcado(s) com sucesso!"
        )

  
    # Atualizar exibição da página
 
    def update_page_display(self):
        if not self.page_pixmap:
            return

        # Copia original
        display_pixmap = self.page_pixmap.copy()

        painter = QPainter(display_pixmap)

        # Desenha marcações salvas
        page_key = str(self.current_page)
        if page_key in self.highlights:
            for h in self.highlights[page_key]:
                color = QColor(h['color'])
                color.setAlphaF(h['opacity'])
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawRect(h['rect'])

        # Desenha retângulo da seleção enquanto arrastando
        if self.mouse_pressed and self.selection_start and self.selection_end:
            sel_rect = QRect(self.selection_start, self.selection_end).normalized()
            painter.setPen(QPen(QColor(0, 0, 200), 1))
            painter.setBrush(QBrush(QColor(100, 150, 255, 50)))
            painter.drawRect(sel_rect)

        # Destaca spans selecionados depois do mouse soltar
        if not self.mouse_pressed and self.selected_spans:
            painter.setPen(QPen(QColor(255, 200, 0), 1))
            painter.setBrush(QColor(255, 255, 200, 120))
            for s in self.selected_spans:
                painter.drawRect(s['rect'])

        painter.end()

        # Redesenhar imagem conforme tamanho do QLabel
        label_size = self.page_label.size()
        scaled = display_pixmap.scaled(
            label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        # Registrar onde ficou desenhado
        self.pixmap_rect = QRect(
            (label_size.width() - scaled.width()) // 2,
            (label_size.height() - scaled.height()) // 2,
            scaled.width(),
            scaled.height()
        )

        self.page_label.setPixmap(scaled)

  
    # Configurar marcador
  
    def configure_highlighter(self):
        dialog = HighlighterDialog(self)
        if dialog.exec_():
            self.current_highlight_settings = dialog.get_settings()
            QMessageBox.information(
                self, "Configuração Salva",
                f"Cor: {self.current_highlight_settings['color'].name()}\n"
                f"Opacidade: {int(self.current_highlight_settings['opacity'] * 100)}%"
            )

   
    # Gerenciar marcações
 
    def manage_highlights(self):
        page_key = str(self.current_page)
        if page_key not in self.highlights or not self.highlights[page_key]:
            QMessageBox.information(self, "Sem marcações", "Não há marcações nesta página.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Gerenciar Marcações")
        dialog.setMinimumSize(500, 400)
        
        # Configurar ícone
        dialog.setWindowIcon(APP_ICON)

        layout = QVBoxLayout(dialog)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)

        for idx, h in enumerate(self.highlights[page_key]):
            frame = QFrame()
            frame.setFrameStyle(QFrame.Box)
            fl = QHBoxLayout(frame)

            # Cor
            c = QColor(h['color'])
            c.setAlphaF(h['opacity'])
            color_label = QLabel()
            color_label.setFixedSize(20, 20)
            color_label.setStyleSheet(
                f"background-color: rgba({c.red()}, {c.green()}, {c.blue()}, {int(h['opacity']*255)}); "
                "border: 1px solid black;"
            )
            fl.addWidget(color_label)

            info = QLabel(f"{h['text'][:40]}... ({h['rect'].x()},{h['rect'].y()})")
            fl.addWidget(info)

            btn_remove = QPushButton("Remover")
            btn_remove.clicked.connect(lambda _, i=idx: self.remove_highlight(page_key, i, dialog))
            fl.addWidget(btn_remove)

            inner_layout.addWidget(frame)

        scroll.setWidget(inner)
        layout.addWidget(scroll)

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)

        dialog.exec_()

    def remove_highlight(self, page_key, index, dialog):
        del self.highlights[page_key][index]
        if not self.highlights[page_key]:
            del self.highlights[page_key]
        self.unsaved_changes = True
        self.save_highlights()
        self.update_page_display()
        dialog.accept()
        self.manage_highlights()

    
    # Limpar marcações

    def clear_page_highlights(self):
        page_key = str(self.current_page)
        if page_key in self.highlights:
            if QMessageBox.question(
                self, "Confirmar",
                f"Remover todas as marcações desta página?",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                del self.highlights[page_key]
                self.unsaved_changes = True
                self.save_highlights()
                self.update_page_display()
        else:
            QMessageBox.information(self, "Sem marcações", "Não há marcações nesta página.")

    def clear_all_highlights(self):
        if self.highlights:
            if QMessageBox.question(
                self, "Confirmar",
                f"Remover todas as marcações do documento?",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self.highlights.clear()
                self.unsaved_changes = True
                self.save_highlights()
                self.update_page_display()
        else:
            QMessageBox.information(self, "Nenhuma marcação", "Nenhuma marcação encontrada.")


    def save_highlights(self):
        path = self.pdf_path + ".highlights.json"
        data = {}

        for page_key, items in self.highlights.items():
            data[page_key] = []
            for h in items:
                data[page_key].append({
                    'rect': {
                        'x': h['rect'].x(),
                        'y': h['rect'].y(),
                        'w': h['rect'].width(),
                        'h': h['rect'].height()
                    },
                    'color': {
                        'r': h['color'].red(),
                        'g': h['color'].green(),
                        'b': h['color'].blue()
                    },
                    'opacity': h['opacity'],
                    'text': h.get('text', '')
                })

        with open(path, "w", encoding="utf8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_highlights(self):
        path = self.pdf_path + ".highlights.json"
        if not os.path.exists(path):
            return {}

        try:
            with open(path, "r", encoding="utf8") as f:
                data = json.load(f)

            highlights = {}
            for page_key, items in data.items():
                highlights[page_key] = []
                for h in items:
                    rect = QRect(h['rect']['x'], h['rect']['y'],
                                 h['rect']['w'], h['rect']['h'])
                    color = QColor(h['color']['r'], h['color']['g'], h['color']['b'])
                    highlights[page_key].append({
                        'rect': rect,
                        'color': color,
                        'opacity': h['opacity'],
                        'text': h.get('text', '')
                    })

            return highlights
        except Exception as e:
            print("Erro ao carregar marcações:", e)
            return {}


    def page_info_text(self):
        return f"Pág. {self.current_page+1} de {self.num_pages}"

    def handle_thumb_keypress(self, event):
        if event.key() == Qt.Key_Down:
            if self.current_page < self.num_pages - 1:
                self.render_page(self.current_page + 1)
        elif event.key() == Qt.Key_Up:
            if self.current_page > 0:
                self.render_page(self.current_page - 1)
        else:
            QWidget.keyPressEvent(self.thumb_widget, event)

    def render_page(self, page_num):
        """Renderiza a página indicada e reseta estados de seleção/escala."""
        self.current_page = page_num
        page = self.doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        self.page_pixmap = QPixmap.fromImage(img)

        # Limpa seleção e spans detectados (força nova detecção quando necessário)
        self.selected_spans = []
        self.selected_text_content = ""
        self.selection_start = None
        self.selection_end = None
        self.mouse_pressed = False
        self.text_spans = []

        # Atualiza miniaturas e exibição
        self.update_page_display()
        self.update_thumbnails()
        self.highlight_thumbnail(page_num)
        self.thumb_widget.setFocus()
        self.scroll_to_thumbnail(page_num)
        self.page_info_label.setText(self.page_info_text())


    def update_thumbnails(self):
        # Remove widgets antigos
        for i in reversed(range(self.thumb_layout.count())):
            w = self.thumb_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        thumb_w, thumb_h = int(60 * 1.2), int(80 * 1.2)

        for idx in range(self.num_pages):
            if idx not in self.thumb_cache:
                page = self.doc.load_page(idx)
                pix = page.get_pixmap(matrix=fitz.Matrix(0.12, 0.12))
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(img).scaled(thumb_w, thumb_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumb_cache[idx] = pixmap
            else:
                pixmap = self.thumb_cache[idx]

            thumb_label = QLabel()
            thumb_label.setPixmap(pixmap)
            thumb_label.setAlignment(Qt.AlignCenter)
            thumb_label.setStyleSheet("border: 2px solid transparent; margin-bottom: 2px;")
            thumb_label.mousePressEvent = self.make_thumbnail_click_handler(idx)

            num_label = QLabel(f"{idx+1}")
            num_label.setAlignment(Qt.AlignCenter)
            num_label.setFont(QFont("Segoe UI", 10, QFont.Bold))

            container = QVBoxLayout()
            container.setSpacing(0)
            container.setContentsMargins(0, 0, 0, 10)
            frame = QFrame()
            frame.setLayout(container)
            container.addWidget(thumb_label)
            container.addWidget(num_label)
            self.thumb_layout.addWidget(frame)

        self.highlight_thumbnail(self.current_page)

    def highlight_thumbnail(self, idx):
        for i in range(self.thumb_layout.count()):
            frame = self.thumb_layout.itemAt(i).widget()
            if frame:
                thumb_label = frame.layout().itemAt(0).widget()
                if i == idx:
                    thumb_label.setStyleSheet("border: 2px solid blue; margin-bottom: 2px;")
                else:
                    thumb_label.setStyleSheet("border: 2px solid transparent; margin-bottom: 2px;")

    def make_thumbnail_click_handler(self, idx):
        def handler(event):
            self.render_page(idx)
        return handler

    def scroll_to_thumbnail(self, idx):
        try:
            frame = self.thumb_layout.itemAt(idx).widget()
            if frame:
                self.thumb_area.ensureWidgetVisible(frame)
        except Exception:
            pass

    def jump_to_page(self):
        try:
            page = int(self.page_jump_entry.text()) - 1
            if 0 <= page < self.num_pages:
                self.render_page(page)
            else:
                QMessageBox.warning(self, "Aviso", "Número de página inválido.")
        except Exception:
            QMessageBox.warning(self, "Aviso", "Digite um número válido.")

    def remove_page_by_number(self):
        try:
            page_num = int(self.entry_remove.text()) - 1
            if page_num < 0 or page_num >= self.num_pages:
                raise ValueError
            self.doc.delete_page(page_num)
            self.num_pages -= 1
            self.thumb_cache.clear()
            # Ajusta highlights para páginas posteriores (simples: recarrega arquivo temporário)
            self.update_thumbnails()
            # Renderiza a página 0 como fallback
            self.render_page(max(0, min(self.current_page, self.num_pages - 1)))
            self.unsaved_changes = True
            QMessageBox.information(self, "Sucesso", "Página removida! Clique em 'Salvar Alterações' para gravar no arquivo.")
        except Exception:
            QMessageBox.critical(self, "Erro", "Digite um número de página válido.")

    def move_page_up(self):
        idx = self.current_page
        if idx > 0:
            # Verifica se há alterações não salvas
            if self.unsaved_changes:
                reply = QMessageBox.question(
                    self, 'Salvar Alterações',
                    'Existem alterações não salvas. Deseja salvar antes de mover a página?',
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Cancel:
                    return
                elif reply == QMessageBox.Yes:
                    self.save_pdf()  # Salva as alterações
            
            self.move_page_to_position(idx, idx - 1)
            self.render_page(idx - 1)
            QMessageBox.information(self, "Sucesso", "Página movida para cima!")
        else:
            QMessageBox.warning(self, "Aviso", "Já está na primeira página!")

    def move_page_down(self):
        idx = self.current_page
        if idx < self.num_pages - 1:
            # Verifica se há alterações não salvas
            if self.unsaved_changes:
                reply = QMessageBox.question(
                    self, 'Salvar Alterações',
                    'Existem alterações não salvas. Deseja salvar antes de mover a página?',
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Cancel:
                    return
                elif reply == QMessageBox.Yes:
                    self.save_pdf()  # Salva as alterações
            
            self.move_page_to_position(idx, idx + 1)
            self.render_page(idx + 1)
            QMessageBox.information(self, "Sucesso", "Página movida para baixo!")
        else:
            QMessageBox.warning(self, "Aviso", "Já está na última página!")

    def move_page_custom(self):
        try:
            from_page = int(self.entry_from.text()) - 1
            to_page = int(self.entry_to.text()) - 1
            if from_page < 0 or from_page >= self.num_pages or to_page < 0 or to_page >= self.num_pages:
                raise ValueError
            if from_page == to_page:
                QMessageBox.information(self, "Info", "A página já está na posição desejada.")
                return
            
            # Verifica se há alterações não salvas
            if self.unsaved_changes:
                reply = QMessageBox.question(
                    self, 'Salvar Alterações',
                    'Existem alterações não salvas. Deseja salvar antes de mover a página?',
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Cancel:
                    return
                elif reply == QMessageBox.Yes:
                    self.save_pdf()  # Salva as alterações
            
            self.move_page_to_position(from_page, to_page)
            self.render_page(to_page)
            QMessageBox.information(self, "Sucesso", f"Página {from_page + 1} movida para a posição {to_page + 1}!")
        except Exception:
            QMessageBox.critical(self, "Erro", "Digite números válidos.")

    def move_page_to_position(self, from_page, to_page):
        if from_page == to_page:
            return
        if to_page < 0 or to_page >= self.num_pages:
            raise ValueError("Posição de destino inválida.")

        try:
            # Usa PyPDF2 para reordenar páginas de forma segura
            with open(self.pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                # Verifica se o índice existe
                if from_page >= len(reader.pages):
                    QMessageBox.critical(self, "Erro", f"Página {from_page + 1} não existe no PDF.")
                    return
                    
                pages = list(reader.pages)
                page_to_move = pages.pop(from_page)
                # Ajusta índice se removido antes do destino
                if from_page < to_page:
                    to_page -= 1
                pages.insert(to_page, page_to_move)
                writer = PyPDF2.PdfWriter()
                for p in pages:
                    writer.add_page(p)
                temp_path = self.pdf_path + ".temp"
                with open(temp_path, 'wb') as out_f:
                    writer.write(out_f)

            # Fecha o documento atual
            self.doc.close()
            
            # Copia o arquivo temporário para o original
            shutil.copy2(temp_path, self.pdf_path)
            os.remove(temp_path)  # Remove o temporário
            
            # Reabre o documento com o PyMuPDF
            self.doc = fitz.open(self.pdf_path)
            self.num_pages = len(self.doc)
            self.thumb_cache.clear()
            self.unsaved_changes = True  # Marca como alterado
            self.update_thumbnails()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao mover página: {str(e)}")
            # Tenta reabrir o documento original em caso de erro
            try:
                self.doc = fitz.open(self.pdf_path)
                self.num_pages = len(self.doc)
            except:
                pass


    def add_page_numbers(self):
        try:
            for i in range(self.num_pages):
                page = self.doc.load_page(i)
                text = f"{i+1} / {self.num_pages}"
                rect = page.rect
                x = rect.width - 55
                y = rect.height - 15
                page.insert_text(
                    (x, y),
                    text,
                    fontsize=12,
                    color=(0, 0, 0),
                    fontname="helv"
                )
            self.unsaved_changes = True
            QMessageBox.information(self, "Numeração adicionada", "Numeração de páginas adicionada com sucesso! Clique em 'Salvar Alterações' para gravar no PDF.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao adicionar numeração: {e}")


    def toggle_theme(self):
        if getattr(self, "dark_mode", False):
            self.setStyleSheet("")
            self.page_label.setStyleSheet("background: #f0f0f0; border: 1px solid #ccc;")
            self.thumb_area.setStyleSheet("")
            self.page_info_label.setStyleSheet("""
                border: 2px solid #27ae60;
                border-radius: 6px;
                font-weight: bold;
                padding: 4px 12px;
                background: #232629;
                color: #00FF00;
            """)
            self.dark_mode = False
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #121212;
                    color: #e0e0e0;
                }
                QLineEdit {
                    background-color: #2b2b2b;
                    color: #f0f0f0;
                    border: 1px solid #555;
                }
                QPushButton {
                    background-color: #333;
                    color: #f0f0f0;
                    border: 1px solid #777;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #444;
                }
                QLabel {
                    color: #e0e0e0;
                }
            """)
            self.page_label.setStyleSheet("background: #1e1e1e; border: 1px solid #555;")
            self.dark_mode = True

    def save_pdf(self):
        if not self.unsaved_changes:
            QMessageBox.information(self, "Nada para salvar", "Não há alterações pendentes.")
            return

        temp_path = self.pdf_path + ".save_temp"
        try:
            # Salva o documento atual
            self.doc.save(temp_path)
            self.doc.close()
            
            # Substitui o arquivo original
            os.replace(temp_path, self.pdf_path)
            
            # Reabre documento salvo
            self.doc = fitz.open(self.pdf_path)
            self.num_pages = len(self.doc)
            self.thumb_cache.clear()
            self.update_thumbnails()
            
            # Mantém a página atual visível
            if self.current_page < self.num_pages:
                self.render_page(self.current_page)
            else:
                self.render_page(self.num_pages - 1)
                
            self.unsaved_changes = False
            QMessageBox.information(self, "Salvo", "Alterações salvas com sucesso!")
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar/substituir o arquivo: {e}")
            
            # Tenta reabrir o documento em caso de erro
            try:
                self.doc = fitz.open(self.pdf_path)
                self.num_pages = len(self.doc)
            except:
                QMessageBox.critical(self, "Erro Grave", "Não foi possível reabrir o PDF. O aplicativo será fechado.")
                self.close()

            
    def handle_thumb_keypress(self, event):
        if event.key() == Qt.Key_Down:
            if self.current_page < self.num_pages - 1:
                self.render_page(self.current_page + 1)
        elif event.key() == Qt.Key_Up:
            if self.current_page > 0:
                self.render_page(self.current_page - 1)
        else:
            QWidget.keyPressEvent(self.thumb_widget, event)

    def closeEvent(self, event):
        if getattr(self, "unsaved_changes", False):
            resp = QMessageBox.question(
                self, "Salvar alterações?",
                "Você deseja salvar as alterações antes de sair?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if resp == QMessageBox.Cancel:
                event.ignore()
                return
            elif resp == QMessageBox.Yes:
                self.save_pdf()

        try:
            if self.doc:
                self.doc.close()
        except Exception:
            pass

        event.accept()


def main():

    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ManipuladorPDF.App")

    app = QApplication(sys.argv)

    # Carrega o ícone somente DEPOIS do QApplication existir
    global APP_ICON
    APP_ICON = load_icon()

    if APP_ICON.isNull():
        logger.warning("Ícone não carregado — usando padrão.")
    else:
        logger.info("Ícone carregado com sucesso!")

    # Ícone da aplicação inteira (barra superior + barra de tarefas)
    app.setWindowIcon(APP_ICON)

    start_screen = PDFStartScreen()
    start_screen.show()

    def open_pdf():
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("PDF Files (*.pdf)")
        file_dialog.setWindowTitle("Selecione um arquivo PDF")
        if file_dialog.exec_():
            pdf_path = file_dialog.selectedFiles()[0]
            start_screen.set_pdf_path(pdf_path)
            window = PDFManipulatorApp(pdf_path)
            window.show()
            start_screen.close()

    start_screen.btn_open.clicked.connect(open_pdf)

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()