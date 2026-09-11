import sqlite3
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


if getattr(sys, "frozen", False):
    # exe로 실행하는 경우
    BASE_DIR = Path(sys.executable).parent
else:
    # .py로 실행하는 경우
    BASE_DIR = Path(__file__).parent

DATABASE_PATH = BASE_DIR / "products.db"

class ProductDatabase:
    def __init__(self, database_path=DATABASE_PATH):
        self.database_path = database_path
        self.create_table()

    def connect(self):
        return sqlite3.connect(self.database_path)

    def create_table(self):
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS Products (
                    productID INTEGER PRIMARY KEY AUTOINCREMENT,
                    productName TEXT NOT NULL,
                    productPrice INTEGER NOT NULL
                )
                """
            )

    def add_product(self, product_name, product_price):
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO Products (productName, productPrice)
                VALUES (?, ?)
                """,
                (product_name, product_price),
            )
            return cursor.lastrowid

    def update_product(self, product_id, product_name, product_price):
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE Products
                SET productName = ?, productPrice = ?
                WHERE productID = ?
                """,
                (product_name, product_price, product_id),
            )
            return cursor.rowcount > 0

    def delete_product(self, product_id):
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM Products WHERE productID = ?",
                (product_id,),
            )
            return cursor.rowcount > 0

    def search_products(self, keyword=""):
        with self.connect() as connection:
            if keyword.strip():
                cursor = connection.execute(
                    """
                    SELECT productID, productName, productPrice
                    FROM Products
                    WHERE productName LIKE ?
                    ORDER BY productID
                    """,
                    (f"%{keyword.strip()}%",),
                )
            else:
                cursor = connection.execute(
                    """
                    SELECT productID, productName, productPrice
                    FROM Products
                    ORDER BY productID
                    """
                )
            return cursor.fetchall()

def save_products_to_excel(products, file_path):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Products"

    headers = ["productID", "productName", "productPrice"]
    worksheet.append(headers)
    for cell in worksheet[1]:
        cell.font = Font(bold=True)

    for product in products:
        worksheet.append(list(product))

    worksheet.column_dimensions["A"].width = 14
    worksheet.column_dimensions["B"].width = 28
    worksheet.column_dimensions["C"].width = 18
    workbook.save(file_path)

class ProductWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.product_database = ProductDatabase()
        self.current_products = []
        self.setup_ui()
        self.load_products()

    def setup_ui(self):
        self.setWindowTitle("Products 관리")
        self.resize(860, 650)
        self.setMinimumSize(760, 560)
        self.setStyleSheet(
            """
            QWidget {
                color: #24324a;
                font-family: 'Malgun Gothic';
                font-size: 10pt;
            }
            ProductWindow {
                background: #f5f7fb;
            }
            QLabel#pageTitle {
                color: #17233c;
                font-size: 24pt;
                font-weight: 700;
            }
            QLabel#pageSubtitle {
                color: #74809a;
                font-size: 10pt;
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #e4e9f2;
                border-radius: 12px;
                margin-top: 12px;
                padding: 18px 16px 14px;
                font-weight: 700;
                color: #344361;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 7px;
                background: #ffffff;
            }
            QLineEdit, QSpinBox {
                background: #fbfcfe;
                border: 1px solid #d8e0ed;
                border-radius: 7px;
                padding: 9px 11px;
                selection-background-color: #ff806d;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 2px solid #ff806d;
                padding: 8px 10px;
                background: #ffffff;
            }
            QPushButton {
                background: #e9edf5;
                border: 0;
                border-radius: 7px;
                color: #344361;
                font-weight: 700;
                padding: 10px 15px;
            }
            QPushButton:hover {
                background: #dce3f0;
            }
            QPushButton:pressed {
                padding-top: 11px;
                padding-bottom: 9px;
            }
            QPushButton#addButton {
                background: #ff806d;
                color: #ffffff;
            }
            QPushButton#addButton:hover {
                background: #f36f5d;
            }
            QPushButton#updateButton {
                background: #263b63;
                color: #ffffff;
            }
            QPushButton#updateButton:hover {
                background: #1d2f51;
            }
            QPushButton#deleteButton {
                background: #fff0ee;
                color: #d95b4c;
            }
            QPushButton#deleteButton:hover {
                background: #ffe1dd;
            }
            QPushButton#exportButton {
                background: #29a37a;
                color: #ffffff;
                padding: 12px;
            }
            QPushButton#exportButton:hover {
                background: #218d69;
            }
            QTableWidget {
                background: #ffffff;
                alternate-background-color: #f8faff;
                border: 1px solid #e4e9f2;
                border-radius: 12px;
                gridline-color: #edf0f6;
                selection-background-color: #ffe1db;
                selection-color: #24324a;
                outline: 0;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f2f7;
            }
            QHeaderView::section {
                background: #263b63;
                border: 0;
                color: #ffffff;
                font-weight: 700;
                padding: 11px 8px;
            }
            QScrollBar:vertical {
                background: #f5f7fb;
                width: 10px;
                margin: 3px;
            }
            QScrollBar::handle:vertical {
                background: #cbd4e4;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            """
        )

        title = QLabel("Products 관리")
        title.setObjectName("pageTitle")
        subtitle = QLabel("상품 정보를 한눈에 관리하고 엑셀 파일로 내보내세요.")
        subtitle.setObjectName("pageSubtitle")

        heading_layout = QVBoxLayout()
        heading_layout.setSpacing(2)
        heading_layout.addWidget(title)
        heading_layout.addWidget(subtitle)

        self.product_name_input = QLineEdit()
        self.product_name_input.setPlaceholderText("제품명을 입력하세요")

        self.product_price_input = QSpinBox()
        self.product_price_input.setRange(0, 2_147_483_647)
        self.product_price_input.setSuffix(" 원")

        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.addRow("제품명", self.product_name_input)
        form_layout.addRow("제품 가격", self.product_price_input)

        input_group = QGroupBox("상품 정보")
        input_group.setLayout(form_layout)

        self.add_button = QPushButton("제품 입력")
        self.update_button = QPushButton("선택 제품 수정")
        self.delete_button = QPushButton("선택 제품 삭제")
        self.clear_button = QPushButton("입력 초기화")
        self.add_button.clicked.connect(self.add_product)
        self.update_button.clicked.connect(self.update_product)
        self.delete_button.clicked.connect(self.delete_product)
        self.clear_button.clicked.connect(self.clear_inputs)
        self.add_button.setObjectName("addButton")
        self.update_button.setObjectName("updateButton")
        self.delete_button.setObjectName("deleteButton")

        input_buttons = QHBoxLayout()
        input_buttons.addWidget(self.add_button)
        input_buttons.addWidget(self.update_button)
        input_buttons.addWidget(self.delete_button)
        input_buttons.addWidget(self.clear_button)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("제품명 검색")
        self.search_input.returnPressed.connect(self.search_products)
        self.search_button = QPushButton("검색")
        self.show_all_button = QPushButton("전체 조회")
        self.search_button.clicked.connect(self.search_products)
        self.show_all_button.clicked.connect(self.load_products)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("검색"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.show_all_button)

        search_group = QGroupBox("상품 찾기")
        search_group.setLayout(search_layout)

        self.product_table = QTableWidget(0, 3)
        self.product_table.setHorizontalHeaderLabels(
            ["productID", "제품명", "제품 가격"]
        )
        self.product_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.product_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.product_table.cellClicked.connect(self.select_product)
        self.product_table.horizontalHeader().setStretchLastSection(True)
        self.product_table.setAlternatingRowColors(True)
        self.product_table.verticalHeader().setDefaultSectionSize(42)
        self.product_table.verticalHeader().setVisible(False)

        self.export_button = QPushButton("현재 목록을 엑셀로 저장")
        self.export_button.setObjectName("exportButton")
        self.export_button.clicked.connect(self.export_to_excel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addLayout(heading_layout)
        layout.addWidget(input_group)
        layout.addLayout(input_buttons)
        layout.addWidget(search_group)
        layout.addWidget(self.product_table)
        layout.addWidget(self.export_button)

    def load_products(self):
        self.search_input.clear()
        self.display_products(self.product_database.search_products())

    def search_products(self):
        products = self.product_database.search_products(self.search_input.text())
        self.display_products(products)

    def display_products(self, products):
        self.current_products = products
        self.product_table.setRowCount(0)
        for row_index, product in enumerate(products):
            self.product_table.insertRow(row_index)
            for column_index, value in enumerate(product):
                item = QTableWidgetItem(str(value))
                if column_index in (0, 2):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.product_table.setItem(row_index, column_index, item)

    def select_product(self, row, _column):
        _product_id, product_name, product_price = self.current_products[row]
        self.product_name_input.setText(product_name)
        self.product_price_input.setValue(product_price)
        self.product_table.selectRow(row)

    def selected_product_id(self):
        row = self.product_table.currentRow()
        if row < 0 or row >= len(self.current_products):
            return None
        return self.current_products[row][0]

    def add_product(self):
        product_name = self.product_name_input.text().strip()
        if not product_name:
            QMessageBox.warning(self, "입력 오류", "제품명을 입력하세요.")
            return

        product_id = self.product_database.add_product(
            product_name, self.product_price_input.value()
        )
        self.load_products()
        self.clear_inputs()
        QMessageBox.information(
            self, "입력 완료", f"제품이 입력되었습니다. ID: {product_id}"
        )

    def update_product(self):
        product_id = self.selected_product_id()
        product_name = self.product_name_input.text().strip()
        if product_id is None:
            QMessageBox.warning(self, "선택 오류", "수정할 제품을 목록에서 선택하세요.")
            return
        if not product_name:
            QMessageBox.warning(self, "입력 오류", "제품명을 입력하세요.")
            return

        self.product_database.update_product(
            product_id, product_name, self.product_price_input.value()
        )
        self.load_products()
        self.clear_inputs()
        QMessageBox.information(self, "수정 완료", "제품이 수정되었습니다.")

    def delete_product(self):
        product_id = self.selected_product_id()
        if product_id is None:
            QMessageBox.warning(self, "선택 오류", "삭제할 제품을 목록에서 선택하세요.")
            return

        answer = QMessageBox.question(
            self,
            "삭제 확인",
            f"productID {product_id} 제품을 삭제하시겠습니까?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.product_database.delete_product(product_id)
            self.load_products()
            self.clear_inputs()

    def clear_inputs(self):
        self.product_name_input.clear()
        self.product_price_input.setValue(0)
        self.product_table.clearSelection()

    def export_to_excel(self):
        if not self.current_products:
            QMessageBox.information(self, "저장 안내", "엑셀로 저장할 제품이 없습니다.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "엑셀 파일 저장",
            "products.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not file_path:
            return

        try:
            save_products_to_excel(self.current_products, file_path)
            QMessageBox.information(
                self, "저장 완료", f"엑셀 파일이 저장되었습니다.\n{file_path}"
            )
        except PermissionError:
            QMessageBox.warning(
                self,
                "저장 오류",
                "엑셀 파일이 다른 프로그램에서 열려 있습니다. 파일을 닫고 다시 시도하세요.",
            )


if __name__ == "__main__":
    application = QApplication(sys.argv)
    window = ProductWindow()
    window.show()
    sys.exit(application.exec())


def print_products(products):
    if not products:
        print("검색된 제품이 없습니다.")
        return

    print("\nID\t제품명\t가격")
    print("-" * 30)
    for product_id, product_name, product_price in products:
        print(f"{product_id}\t{product_name}\t{product_price:,}원")


def run_menu():
    product_database = ProductDatabase()

    while True:
        print("\n===== Products 관리 =====")
        print("1. 제품 입력")
        print("2. 제품 수정")
        print("3. 제품 삭제")
        print("4. 제품 검색")
        print("5. 전체 제품 조회")
        print("0. 종료")

        choice = input("메뉴를 선택하세요: ").strip()

        try:
            if choice == "1":
                product_name = input("제품명: ").strip()
                product_price = int(input("제품 가격: ").strip())
                product_id = product_database.add_product(product_name, product_price)
                print(f"제품이 입력되었습니다. productID: {product_id}")
            elif choice == "2":
                product_id = int(input("수정할 productID: ").strip())
                product_name = input("새 제품명: ").strip()
                product_price = int(input("새 제품 가격: ").strip())
                if product_database.update_product(product_id, product_name, product_price):
                    print("제품이 수정되었습니다.")
                else:
                    print("해당 productID의 제품을 찾을 수 없습니다.")
            elif choice == "3":
                product_id = int(input("삭제할 productID: ").strip())
                if product_database.delete_product(product_id):
                    print("제품이 삭제되었습니다.")
                else:
                    print("해당 productID의 제품을 찾을 수 없습니다.")
            elif choice == "4":
                keyword = input("검색할 제품명: ").strip()
                print_products(product_database.search_products(keyword))
            elif choice == "5":
                print_products(product_database.search_products())
            elif choice == "0":
                print("프로그램을 종료합니다.")
                break
            else:
                print("올바른 메뉴 번호를 입력하세요.")
        except ValueError:
            print("productID와 가격은 숫자로 입력하세요.")


if __name__ == "__main__":
    run_menu()
