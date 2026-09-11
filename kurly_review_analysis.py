"""컬리 상품 후기 300개 수집, 감성 분류 및 시각화."""

import json
import re
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
from bs4 import BeautifulSoup
from matplotlib import font_manager, rcParams
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


PRODUCT_NO = 5156742
PRODUCT_URL = (
    f"https://www.kurly.com/goods/{PRODUCT_NO}"
    "?collectionCode=market-best-logic"
)
TARGET_REVIEWS = 300
PAGE_SIZE = 20
OUTPUT_DIR = Path(__file__).resolve().parent / "kurly_review_results"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

POSITIVE_WORDS = (
    "맛있", "추천", "재구매", "만족", "좋아", "좋았", "훌륭", "간편", "편리",
    "푸짐", "진하", "깊은", "쫄깃", "신선", "최고", "대박", "굿", "맛집",
)
NEGATIVE_WORDS = (
    "맛없", "비싸", "아쉽", "실망", "별로", "나쁘", "짜", "싱겁", "느끼",
    "매워", "질겨", "퍼졌", "적", "불편", "늦", "냄새", "부족", "불만",
)


def configure_korean_font():
    """Windows에서 사용할 수 있는 한글 폰트를 선택한다."""
    candidates = ("Malgun Gothic", "NanumGothic", "Noto Sans CJK KR")
    installed = {font.name for font in font_manager.fontManager.ttflist}
    selected = next((font for font in candidates if font in installed), None)
    if selected:
        rcParams["font.family"] = selected
    rcParams["axes.unicode_minus"] = False


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def extract_review_list(payload):
    """API 응답 형식이 조금 달라도 후기 배열을 찾아 반환한다."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("data", "items", "reviews", "contents", "results"):
        items = payload.get(key)
        if isinstance(items, list):
            return items
        if isinstance(items, dict):
            found = extract_review_list(items)
            if found:
                return found
    return []


def normalize_review(item):
    """컬리 응답의 필드명을 분석용 열로 통일한다."""
    if not isinstance(item, dict):
        return None
    author = item.get("author") if isinstance(item.get("author"), dict) else {}
    text = clean_text(
        item.get("contents")
        or item.get("reviewBody")
        or item.get("content")
        or item.get("text")
    )
    if not text or text in {"상품 후기 운영 안내", "상품후기 운영 안내"}:
        return None
    return {
        "review_id": item.get("no") or item.get("id") or "",
        "date": item.get("registeredAt") or item.get("datePublished") or item.get("date") or "",
        "reviewer": item.get("ownerName") or author.get("name", ""),
        "review": text,
    }


def extract_embedded_reviews(html):
    """초기 HTML의 JSON 스크립트에서 후기 객체를 찾아 읽는다."""
    reviews = []
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.select("script"):
        raw = script.string or script.get_text()
        if not raw or not any(token in raw for token in ("reviewBody", "registeredAt", "contents")):
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        def visit(value):
            if isinstance(value, dict):
                if value.get("contents") or value.get("reviewBody"):
                    review = normalize_review(value)
                    if review:
                        reviews.append(review)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(payload)
    return reviews


def extract_raw_reviews(html):
    """Next.js의 비표준 데이터 스트림에서 후기 본문을 복원한다."""
    reviews = []
    pattern = re.compile(
        r"(?:\\?\"contents\\?\"|\\?\"reviewBody\\?\")\s*:\s*"
        r"\\?\"((?:\\\\.|[^\"\\])*)\\?\""
    )
    for index, match in enumerate(pattern.finditer(html)):
        encoded_text = match.group(1)
        try:
            text = json.loads(f'"{encoded_text}"')
        except json.JSONDecodeError:
            text = encoded_text.replace(r"\n", " ").replace(r'\"', '"')
        text = clean_text(text)
        if len(text) < 5:
            continue
        reviews.append(
            {
                "review_id": f"embedded-{index}",
                "date": "",
                "reviewer": "",
                "review": text,
            }
        )
    return reviews


def extract_html_reviews(html):
    """상품 페이지에 서버 렌더링된 후기 목록을 추출한다."""
    soup = BeautifulSoup(html, "html.parser")
    reviews = []
    for container in soup.select('[id^="review-"]'):
        body = container.select_one("article p, p")
        if body is None:
            continue
        date_node = container.select_one("footer span")
        reviewer_node = container.select_one("span[class*='e3ar37f9']")
        review = normalize_review(
            {
                "id": container.get("id", "").removeprefix("review-"),
                "date": clean_text(date_node.get_text(" ", strip=True) if date_node else ""),
                "ownerName": clean_text(
                    reviewer_node.get_text(" ", strip=True) if reviewer_node else ""
                ),
                "contents": body.get_text(" ", strip=True),
            }
        )
        if review:
            reviews.append(review)
    return reviews


def crawl_api_reviews(session, limit):
    """컬리 후기 API의 nextCursor를 따라가며 후기를 수집한다."""
    endpoint = (
        "https://api.kurly.com/product-review/v4/"
        f"contents-products/{PRODUCT_NO}/reviews"
    )
    params = {
        "sortType": "RECOMMEND",
        "size": min(PAGE_SIZE, 30),
        "onlyImage": "false",
    }
    reviews = []
    seen = set()

    while len(reviews) < limit:
        try:
            response = session.get(endpoint, params=params, timeout=20)
            response.raise_for_status()
            response.encoding = "utf-8"
            payload = response.json()
        except (requests.RequestException, ValueError):
            return []

        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        items = data.get("reviews", []) if isinstance(data, dict) else []
        if not items:
            break

        for item in items:
            review = normalize_review(item)
            if not review:
                continue
            key = review["review_id"] or review["review"]
            if key not in seen:
                seen.add(key)
                reviews.append(review)
                if len(reviews) >= limit:
                    break

        next_cursor = data.get("nextCursor", {})
        next_after = (
            next_cursor.get("after")
            if isinstance(next_cursor, dict)
            else next_cursor
        )
        if not next_after or len(items) < params["size"]:
            break
        params["after"] = next_after
        time.sleep(0.2)

    return reviews


def crawl_reviews(limit=TARGET_REVIEWS):
    """컬리 후기 API를 페이지 단위로 호출해 최대 limit개를 반환한다."""
    session = requests.Session()
    session.headers.update(HEADERS)
    api_reviews = crawl_api_reviews(session, limit)
    if len(api_reviews) >= limit:
        return pd.DataFrame(api_reviews[:limit])

    page = 2
    reviews = []
    seen = set()
    page_url_candidates = (
        "https://api.kurly.com/v1/reviews",
        "https://api.kurly.com/v1/products/{product_no}/reviews",
        "https://www.kurly.com/api/v1/reviews",
    )
    first_response = session.get(PRODUCT_URL, timeout=20)
    first_response.raise_for_status()
    first_response.encoding = first_response.apparent_encoding or first_response.encoding
    fallback = extract_html_reviews(first_response.text)
    if not fallback:
        fallback = extract_embedded_reviews(first_response.text)
    if not fallback:
        fallback = extract_raw_reviews(first_response.text)

    def add_reviews(items):
        added = 0
        for item in items:
            review = normalize_review(item) if not isinstance(item, dict) or not item.get("review") else item
            if not review:
                continue
            key = review["review_id"] or review["review"]
            if key not in seen:
                seen.add(key)
                reviews.append(review)
                added += 1
                if len(reviews) >= limit:
                    break
        return added

    add_reviews(fallback)

    while len(reviews) < limit and page <= (limit // PAGE_SIZE + 3):
        page_items = []
        html_page_candidates = (
            f"{PRODUCT_URL}&sort=recent&page={page}",
            f"{PRODUCT_URL}&sort=recent&pageNo={page}",
            f"{PRODUCT_URL}&reviewPage={page}",
        )
        for page_url in html_page_candidates:
            try:
                response = session.get(page_url, timeout=20)
                if response.ok:
                    response.encoding = response.apparent_encoding or response.encoding
                    page_items = extract_html_reviews(response.text)
                    if page_items:
                        break
            except requests.RequestException:
                continue

        added = add_reviews(page_items)
        if added:
            page += 1
            time.sleep(0.4)
            continue

        for template in page_url_candidates:
            endpoint = template.format(product_no=PRODUCT_NO)
            params = {
                "productNo": PRODUCT_NO,
                "goodsNo": PRODUCT_NO,
                "page": page,
                "pageNo": page,
                "pageSize": PAGE_SIZE,
                "size": PAGE_SIZE,
                "sort": "recommend",
            }
            try:
                response = session.get(endpoint, params=params, timeout=20)
                if response.ok and "json" in response.headers.get("Content-Type", ""):
                    page_items = extract_review_list(response.json())
                    if page_items:
                        break
            except (requests.RequestException, ValueError):
                continue

        normalized = [normalize_review(item) for item in page_items]
        normalized = [item for item in normalized if item]
        added = add_reviews(normalized)
        if not page_items or added == 0:
            break
        page += 1
        time.sleep(0.4)

    if len(reviews) < limit:
        add_reviews(fallback)

    if len(reviews) < limit:
        raise RuntimeError(
            f"{len(reviews)}개만 수집되었습니다. 컬리 후기 API가 변경되었거나 "
            "자동화 요청을 제한하고 있습니다. 개발자 도구의 후기 요청 URL을 "
            "page_url_candidates에 추가한 뒤 다시 실행하세요."
        )
    return pd.DataFrame(reviews[:limit])


def classify_sentiment(text):
    """한국어 긍정·부정 키워드 수를 비교하는 투명한 기준의 분류기."""
    positive = sum(text.count(word) for word in POSITIVE_WORDS)
    negative = sum(text.count(word) for word in NEGATIVE_WORDS)
    score = positive - negative
    label = "긍정" if score > 0 else "부정" if score < 0 else "중립"
    return pd.Series({"positive_count": positive, "negative_count": negative, "sentiment": label})


def analyze_reviews(reviews):
    reviews = reviews.copy()
    reviews[["positive_count", "negative_count", "sentiment"]] = reviews["review"].apply(
        classify_sentiment
    )
    OUTPUT_DIR.mkdir(exist_ok=True)
    reviews.to_csv(OUTPUT_DIR / "kurly_reviews.csv", index=False, encoding="utf-8-sig")
    summary = reviews["sentiment"].value_counts().reindex(["긍정", "중립", "부정"], fill_value=0)
    summary.rename("count").to_csv(
        OUTPUT_DIR / "kurly_sentiment_summary.csv", encoding="utf-8-sig"
    )

    return reviews


def create_analysis_figure(reviews):
    """분석 DataFrame을 좌우 두 차트가 있는 Matplotlib Figure로 만든다."""
    configure_korean_font()
    colors = {"긍정": "#2a9d8f", "중립": "#9aa0a6", "부정": "#e76f51"}
    summary = reviews["sentiment"].value_counts().reindex(
        ["긍정", "중립", "부정"], fill_value=0
    )
    figure = Figure(figsize=(10, 5), constrained_layout=True)
    axes = figure.subplots(1, 2)
    summary.plot.bar(ax=axes[0], color=[colors[label] for label in summary.index])
    axes[0].set_title("후기 감성 분포")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("후기 수")
    axes[0].tick_params(axis="x", rotation=0)
    for index, value in enumerate(summary):
        axes[0].text(index, value, str(value), ha="center", va="bottom")

    reviews["date"] = pd.to_datetime(reviews["date"], errors="coerce")
    grouped = reviews.dropna(subset=["date"]).copy()
    monthly = grouped.groupby(grouped["date"].dt.to_period("M"))["sentiment"].value_counts().unstack(fill_value=0)
    monthly.reindex(columns=["긍정", "중립", "부정"], fill_value=0).plot(
        ax=axes[1], marker="o", color=[colors[label] for label in ["긍정", "중립", "부정"]]
    )
    axes[1].set_title("월별 감성 후기 수")
    axes[1].set_xlabel("작성 월")
    axes[1].set_ylabel("후기 수")
    axes[1].legend(title="감성")
    figure.suptitle(f"컬리 상품 {PRODUCT_NO} 후기 감성 분석", fontsize=15)
    figure.savefig(OUTPUT_DIR / "kurly_review_analysis.png", dpi=150)
    return figure


def analyze_and_plot(reviews):
    """기존 콘솔 실행을 위한 분석·차트 생성 함수."""
    analyzed = analyze_reviews(reviews)
    figure = create_analysis_figure(analyzed)
    plt.show()
    return analyzed


class AnalysisWorker(QThread):
    """후기 수집과 감성 분석을 GUI 바깥 스레드에서 수행한다."""

    completed = pyqtSignal(object, object)
    failed = pyqtSignal(str)

    def run(self):
        try:
            reviews = crawl_reviews(TARGET_REVIEWS)
            analyzed = analyze_reviews(reviews)
            figure = create_analysis_figure(analyzed)
            self.completed.emit(analyzed, figure)
        except Exception as error:
            self.failed.emit(str(error))


class KurlyReviewWindow(QMainWindow):
    """컬리 후기 목록과 감성 분석 차트를 함께 보여주는 창."""

    def __init__(self):
        super().__init__()
        self.worker = None
        self.canvas = None
        self.setWindowTitle("컬리 후기 감성 분석")
        self.resize(1500, 850)
        self.setup_ui()

    def setup_ui(self):
        self.start_button = QPushButton("후기 300개 수집 및 분석")
        self.start_button.clicked.connect(self.start_analysis)
        self.status_label = QLabel("버튼을 눌러 컬리 후기 분석을 시작하세요.")

        self.review_table = QTableWidget(0, 4)
        self.review_table.setHorizontalHeaderLabels(["작성일", "작성자", "감성", "후기 내용"])
        self.review_table.setAlternatingRowColors(True)
        self.review_table.setWordWrap(True)
        self.review_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.review_table.setColumnWidth(0, 105)
        self.review_table.setColumnWidth(1, 85)
        self.review_table.setColumnWidth(2, 70)
        self.review_table.horizontalHeader().setStretchLastSection(True)

        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_placeholder = QLabel("분석이 완료되면 차트가 표시됩니다.")
        self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_layout.addWidget(self.chart_placeholder)

        splitter = QSplitter()
        splitter.addWidget(self.review_table)
        splitter.addWidget(self.chart_container)
        splitter.setSizes([700, 800])

        layout = QVBoxLayout()
        layout.addWidget(self.start_button)
        layout.addWidget(self.status_label)
        layout.addWidget(splitter, 1)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def start_analysis(self):
        if self.worker and self.worker.isRunning():
            return
        self.start_button.setEnabled(False)
        self.status_label.setText("후기 수집 및 분석 중입니다...")
        self.review_table.setRowCount(0)
        self.worker = AnalysisWorker()
        self.worker.completed.connect(self.show_results)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def show_results(self, reviews, figure):
        self.review_table.setRowCount(len(reviews))
        for row_index, (_, review) in enumerate(reviews.iterrows()):
            values = [review["date"], review["reviewer"], review["sentiment"], review["review"]]
            for column_index, value in enumerate(values):
                self.review_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
        self.review_table.resizeRowsToContents()
        self.chart_placeholder.hide()
        if self.canvas:
            self.chart_layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
        self.canvas = FigureCanvas(figure)
        self.chart_layout.addWidget(self.canvas)
        self.canvas.draw()
        self.status_label.setText(f"완료: 후기 {len(reviews)}개 분석 및 저장")
        self.start_button.setEnabled(True)

    def show_error(self, message):
        self.status_label.setText("분석에 실패했습니다.")
        self.start_button.setEnabled(True)
        QMessageBox.critical(self, "분석 오류", message)


def run_gui():
    app = QApplication([])
    window = KurlyReviewWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    run_gui()