import base64
import mimetypes
import os
import sys

from openai import OpenAI
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def load_env_file(file_path):
    if not os.path.exists(file_path):
        return
    with open(file_path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


load_env_file(os.path.join(os.path.dirname(__file__), ".env"))


class ImageAnalysisWorker(QObject):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, image_path, api_key):
        super().__init__()
        self.image_path = image_path
        self.api_key = api_key

    def run(self):
        try:
            mime_type = mimetypes.guess_type(self.image_path)[0] or "image/jpeg"
            with open(self.image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

            client = OpenAI(api_key=self.api_key)
            response = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "이 사진에 있는 주요 사물을 한국어로 설명해 주세요. "
                                    "확실하지 않은 내용은 추측이라고 표시하고, "
                                    "사진에서 확인되는 사물과 장면을 중심으로 답변해 주세요."
                                ),
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:{mime_type};base64,{encoded_image}",
                            },
                        ],
                    }
                ],
            )
            self.finished.emit(response.output_text.strip())
        except Exception as error:
            self.failed.emit(str(error))


class PhotoAnalysisWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_path = ""
        self.worker_thread = None
        self.worker = None
        self.setWindowTitle("사진 사물 해석기")
        self.resize(900, 650)
        self._build_ui()

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("OpenAI API 키"))
        self.api_key_input = QLineEdit(os.getenv("OPENAI_API_KEY", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("환경 변수 OPENAI_API_KEY를 사용하거나 직접 입력하세요")
        api_layout.addWidget(self.api_key_input)
        main_layout.addLayout(api_layout)

        button_layout = QHBoxLayout()
        self.select_button = QPushButton("사진 선택")
        self.select_button.clicked.connect(self.select_image)
        button_layout.addWidget(self.select_button)

        self.analyze_button = QPushButton("사물 해석")
        self.analyze_button.setEnabled(False)
        self.analyze_button.clicked.connect(self.analyze_image)
        button_layout.addWidget(self.analyze_button)
        main_layout.addLayout(button_layout)

        self.file_label = QLabel("선택된 사진이 없습니다.")
        self.file_label.setStyleSheet("color: #555; padding: 4px;")
        main_layout.addWidget(self.file_label)

        self.preview_label = QLabel("사진 미리보기")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(300)
        self.preview_label.setStyleSheet(
            "background: #f4f4f4; border: 1px solid #cccccc; color: #777;"
        )
        main_layout.addWidget(self.preview_label, stretch=2)

        main_layout.addWidget(QLabel("분석 결과"))
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("사진을 선택하고 '사물 해석' 버튼을 눌러 주세요.")
        main_layout.addWidget(self.result_text, stretch=1)

        self.statusBar().showMessage("준비되었습니다.")

    def select_image(self):
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "사진 선택",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp)",
        )
        if not image_path:
            return

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            QMessageBox.warning(self, "사진 열기 실패", "선택한 파일을 사진으로 열 수 없습니다.")
            return

        self.image_path = image_path
        self.file_label.setText(image_path)
        self._show_preview(pixmap)
        self.analyze_button.setEnabled(True)
        self.statusBar().showMessage("사진을 선택했습니다.")

    def _show_preview(self, pixmap):
        preview = pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(preview)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.image_path:
            self._show_preview(QPixmap(self.image_path))

    def analyze_image(self):
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(
                self,
                "API 키 필요",
                "OpenAI API 키를 입력하거나 OPENAI_API_KEY 환경 변수를 설정해 주세요.",
            )
            return
        if not self.image_path:
            return

        self.analyze_button.setEnabled(False)
        self.select_button.setEnabled(False)
        self.result_text.clear()
        self.statusBar().showMessage("사진을 분석하는 중입니다...")

        self.worker_thread = QThread(self)
        self.worker = ImageAnalysisWorker(self.image_path, api_key)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.analysis_finished)
        self.worker.failed.connect(self.analysis_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def analysis_finished(self, result):
        self.result_text.setPlainText(result or "분석 결과가 비어 있습니다.")
        self._analysis_done("분석이 완료되었습니다.")

    def analysis_failed(self, message):
        self.result_text.setPlainText(f"분석 중 오류가 발생했습니다.\n\n{message}")
        self._analysis_done("분석에 실패했습니다.")

    def _analysis_done(self, message):
        self.analyze_button.setEnabled(bool(self.image_path))
        self.select_button.setEnabled(True)
        self.statusBar().showMessage(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhotoAnalysisWindow()
    window.show()
    sys.exit(app.exec())