from __future__ import annotations

from pathlib import Path
import platform
import warnings

import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "S&P 500 과거 데이터.csv"
OUTPUT_DIR = BASE_DIR / "S&P500_분석결과"
START_DATE = "2010-01-01"
END_DATE = "2025-12-31"


def configure_korean_font() -> str | None:
    """설치된 한글 폰트를 찾아 matplotlib의 한글 깨짐을 방지한다."""
    preferred_fonts = [
        "Malgun Gothic",
        "맑은 고딕",
        "AppleGothic",
        "NanumGothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
    ]
    installed_names = {font.name for font in font_manager.fontManager.ttflist}

    for font_name in preferred_fonts:
        if font_name in installed_names:
            rcParams["font.family"] = font_name
            rcParams["axes.unicode_minus"] = False
            return font_name

    # Windows의 일반적인 폰트 경로를 한 번 더 확인한다.
    if platform.system() == "Windows":
        windows_fonts = Path("C:/Windows/Fonts")
        for font_path in windows_fonts.glob("*.ttf"):
            try:
                font_properties = font_manager.FontProperties(fname=font_path)
                if any(
                    keyword in font_properties.get_name().lower()
                    for keyword in ("malgun", "gothic", "nanum", "noto")
                ):
                    rcParams["font.family"] = font_properties.get_name()
                    rcParams["axes.unicode_minus"] = False
                    return font_properties.get_name()
            except OSError:
                continue

    rcParams["axes.unicode_minus"] = False
    warnings.warn(
        "한글 폰트를 찾지 못했습니다. 시스템에 맑은 고딕 또는 Noto Sans KR을 설치하세요."
    )
    return None


def clean_data(csv_path: Path) -> pd.DataFrame:
    """CSV를 읽고 날짜 및 숫자 열을 분석 가능한 형식으로 변환한다."""
    data = pd.read_csv(csv_path, encoding="utf-8-sig")
    data.columns = data.columns.str.strip()

    required_columns = {"날짜", "종가", "시가", "고가", "저가"}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {sorted(missing_columns)}")

    data["날짜"] = pd.to_datetime(
        data["날짜"].astype("string").str.replace(" ", "", regex=False),
        errors="coerce",
    )
    numeric_columns = [column for column in ["종가", "시가", "고가", "저가", "거래량"] if column in data]
    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column].astype("string").str.replace(",", "", regex=False),
            errors="coerce",
        )

    if "변동 %" in data:
        data["변동 %"] = pd.to_numeric(
            data["변동 %"].astype("string").str.replace("%", "", regex=False),
            errors="coerce",
        )

    data = (
        data.dropna(subset=["날짜", "종가"])
        .drop_duplicates(subset="날짜")
        .sort_values("날짜")
        .set_index("날짜")
    )
    data["일간수익률"] = data["종가"].pct_change()
    data["누적수익률"] = (1 + data["일간수익률"].fillna(0)).cumprod() - 1
    data["연환산변동성"] = data["일간수익률"].rolling(21).std() * (252**0.5)
    data["고점대비하락률"] = data["종가"] / data["종가"].cummax() - 1
    return data


def save_line_graph(data: pd.DataFrame, output_path: Path) -> None:
    filtered = data.loc[START_DATE:END_DATE]
    if filtered.empty:
        raise ValueError("요청한 기간에 사용할 수 있는 데이터가 없습니다.")

    figure, axis = plt.subplots(figsize=(15, 7))
    axis.plot(filtered.index, filtered["종가"], color="#1f5f8b", linewidth=1.5)
    axis.set_title("S&P 500 종가 추이 (2010년 1월 초 ~ 2025년 연말)", fontsize=16, pad=14)
    axis.set_xlabel("날짜")
    axis.set_ylabel("종가")
    axis.grid(True, alpha=0.25)
    figure.text(
        0.01,
        0.01,
        f"실제 데이터 범위: {filtered.index.min():%Y-%m-%d} ~ {filtered.index.max():%Y-%m-%d}",
        fontsize=9,
        color="#666666",
    )
    figure.tight_layout(rect=(0, 0.03, 1, 1))
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)


def save_analysis_graphs(data: pd.DataFrame, output_dir: Path) -> None:
    filtered = data.loc[START_DATE:END_DATE]

    figure, axes = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
    axes[0].plot(filtered.index, filtered["종가"], label="종가", color="#1f5f8b")
    axes[0].plot(
        filtered.index,
        filtered["종가"].rolling(50).mean(),
        label="50일 이동평균",
        color="#e07a5f",
    )
    axes[0].plot(
        filtered.index,
        filtered["종가"].rolling(200).mean(),
        label="200일 이동평균",
        color="#3a9d5d",
    )
    axes[0].set_title("종가와 이동평균")
    axes[0].legend()
    axes[0].grid(alpha=0.25)
    axes[1].plot(filtered.index, filtered["고점대비하락률"] * 100, color="#b23a48")
    axes[1].fill_between(filtered.index, filtered["고점대비하락률"] * 100, 0, color="#b23a48", alpha=0.2)
    axes[1].set_title("고점 대비 하락률")
    axes[1].set_ylabel("하락률 (%)")
    axes[1].grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_dir / "추세와_고점대비하락률.png", dpi=160)
    plt.close(figure)

    monthly = filtered["종가"].resample("ME").last().pct_change().dropna() * 100
    figure, axis = plt.subplots(figsize=(15, 5))
    colors = ["#b23a48" if value < 0 else "#3a9d5d" for value in monthly]
    axis.bar(monthly.index, monthly, color=colors, width=20)
    axis.axhline(0, color="black", linewidth=0.8)
    axis.set_title("월간 수익률")
    axis.set_ylabel("수익률 (%)")
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_dir / "월간수익률.png", dpi=160)
    plt.close(figure)


def create_report(data: pd.DataFrame, output_dir: Path) -> None:
    filtered = data.loc[START_DATE:END_DATE].copy()
    daily_returns = filtered["일간수익률"].dropna()
    year_end_prices = filtered["종가"].resample("YE").last()
    annual_base = pd.concat([filtered["종가"].iloc[:1], year_end_prices])
    annual_returns = annual_base.pct_change().dropna() * 100
    summary = pd.Series(
        {
            "분석 시작일": filtered.index.min(),
            "분석 종료일": filtered.index.max(),
            "분석 거래일 수": len(filtered),
            "시작 종가": filtered["종가"].iloc[0],
            "종료 종가": filtered["종가"].iloc[-1],
            "전체 누적수익률(%)": filtered["누적수익률"].iloc[-1] * 100,
            "연환산 수익률(%)": ((filtered["종가"].iloc[-1] / filtered["종가"].iloc[0]) ** (365.25 / (filtered.index[-1] - filtered.index[0]).days) - 1) * 100,
            "연환산 변동성(%)": daily_returns.std() * (252**0.5) * 100,
            "최대 낙폭(%)": filtered["고점대비하락률"].min() * 100,
            "상승일 비율(%)": (daily_returns > 0).mean() * 100,
        }
    )

    summary.to_csv(output_dir / "요약통계.csv", encoding="utf-8-sig", header=["값"])
    annual_returns.rename("연간수익률(%)").to_csv(
        output_dir / "연간수익률.csv", encoding="utf-8-sig", header=True
    )
    filtered.to_csv(output_dir / "정제데이터.csv", encoding="utf-8-sig")

    print("\n[요약 통계]")
    print(summary.to_string())
    print("\n[연간 수익률(%)]")
    print(annual_returns.round(2).to_string())


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    selected_font = configure_korean_font()
    data = clean_data(CSV_PATH)
    filtered = data.loc[START_DATE:END_DATE]

    print(f"원본 데이터: {data.index.min():%Y-%m-%d} ~ {data.index.max():%Y-%m-%d}, {len(data):,}행")
    print(f"분석 데이터: {filtered.index.min():%Y-%m-%d} ~ {filtered.index.max():%Y-%m-%d}, {len(filtered):,}행")
    if data.index.max() < pd.Timestamp(END_DATE):
        print(f"알림: 원본 데이터가 {data.index.max():%Y-%m-%d}에서 끝나므로 2020~2025 데이터는 포함되지 않습니다.")
    print(f"사용 폰트: {selected_font or 'matplotlib 기본 폰트(한글 폰트 설치 권장)'}")

    save_line_graph(filtered, OUTPUT_DIR / "S&P500_종가_2010-2025.png")
    save_analysis_graphs(data, OUTPUT_DIR)
    create_report(data, OUTPUT_DIR)
    print(f"\n결과 저장 위치: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()