from pathlib import Path
import re
import warnings

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager, rcParams


START_YEAR = 1970
END_YEAR = 2025
DATA_SHEET = "데이터"
OUTPUT_DIR = Path(__file__).resolve().parent / "분석결과"


def find_input_file() -> Path:
    """분석 결과 폴더를 제외한 현재 폴더의 첫 번째 xlsx 파일을 찾는다."""
    candidates = sorted(
        path
        for path in Path(__file__).resolve().parent.glob("*.xlsx")
        if not path.name.startswith("~$")
    )
    if not candidates:
        raise FileNotFoundError("분석 폴더에 xlsx 입력 파일이 없습니다.")
    return candidates[0]


def configure_korean_font() -> str:
    """설치된 한글 폰트를 찾아 matplotlib에 적용한다."""
    font_names = ["Malgun Gothic", "NanumGothic", "AppleGothic", "Noto Sans CJK KR"]
    installed = {font.name for font in font_manager.fontManager.ttflist}
    selected = next((name for name in font_names if name in installed), None)
    if selected:
        rcParams["font.family"] = selected
    else:
        warnings.warn(
            "한글 폰트를 찾지 못했습니다. Windows에서는 '맑은 고딕' 설치를 권장합니다."
        )
    rcParams["axes.unicode_minus"] = False
    return selected or "기본 폰트"


def normalize_label(label: object) -> str:
    return re.sub(r"\s+", "", str(label)).strip()


def parse_year(value: object) -> float:
    match = re.search(r"(\d{4})", str(value))
    return float(match.group(1)) if match else float("nan")


def load_and_clean(path: Path) -> pd.DataFrame:
    """가로형 KOSIS 표를 연도 기준 세로형 데이터로 변환하고 정리한다."""
    raw = pd.read_excel(path, sheet_name=DATA_SHEET, header=None)
    if raw.empty or raw.shape[0] < 2:
        raise ValueError("데이터 시트에 분석할 행이 없습니다.")

    years = raw.iloc[0, 1:].map(parse_year)
    valid_columns = years.between(START_YEAR, END_YEAR)
    if not valid_columns.any():
        raise ValueError(f"{START_YEAR}~{END_YEAR} 연도 열을 찾지 못했습니다.")
    year_values = years.loc[valid_columns].astype(int).tolist()

    records: dict[str, list[object]] = {"연도": year_values}
    for row_index in range(1, raw.shape[0]):
        label = normalize_label(raw.iloc[row_index, 0])
        if not label or label == "nan":
            continue
        values = raw.iloc[row_index, 1:].loc[valid_columns]
        records[label] = pd.to_numeric(values, errors="coerce").tolist()

    data = pd.DataFrame(records)
    data = data.loc[:, ~data.columns.duplicated()].sort_values("연도")
    data = data.drop_duplicates(subset="연도", keep="last").reset_index(drop=True)

    expected_years = set(range(START_YEAR, END_YEAR + 1))
    actual_years = set(data["연도"])
    missing_years = sorted(expected_years - actual_years)
    if missing_years:
        raise ValueError(f"누락된 연도가 있습니다: {missing_years}")

    required = "출생아수(명)"
    if required not in data.columns:
        raise ValueError(f"필수 컬럼 '{required}'을 찾지 못했습니다.")
    return data


def enrich_analysis(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    births = "출생아수(명)"
    result["출생아수_전년대비증감(명)"] = result[births].diff()
    result["출생아수_전년대비증감률(%)"] = result[births].pct_change() * 100
    result["출생아수_5년이동평균(명)"] = result[births].rolling(5, min_periods=1).mean()
    result["10년기간"] = (result["연도"] // 10 * 10).astype(str) + "년대"
    return result


def build_period_summary(data: pd.DataFrame) -> pd.DataFrame:
    numeric = data.select_dtypes(include="number").columns.drop("연도")
    summary = data.groupby("10년기간", sort=False)[list(numeric)].agg(["mean", "min", "max"])
    summary.columns = [f"{metric}_{stat}" for metric, stat in summary.columns]
    return summary.reset_index()


def save_analysis_tables(data: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    data.to_csv(OUTPUT_DIR / "정제데이터.csv", index=False, encoding="utf-8-sig")

    descriptive = data.describe(include="all").transpose()
    descriptive.to_csv(OUTPUT_DIR / "기술통계.csv", encoding="utf-8-sig")
    build_period_summary(data).to_csv(
        OUTPUT_DIR / "기간별요약.csv", index=False, encoding="utf-8-sig"
    )

    numeric = data.select_dtypes(include="number")
    numeric.corr().to_csv(OUTPUT_DIR / "지표상관관계.csv", encoding="utf-8-sig")

    births = data["출생아수(명)"]
    key_rows = {
        "최대 출생아수 연도": int(data.loc[births.idxmax(), "연도"]),
        "최대 출생아수(명)": int(births.max()),
        "최소 출생아수 연도": int(data.loc[births.idxmin(), "연도"]),
        "최소 출생아수(명)": int(births.min()),
        "1970년 대비 2025년 증감률(%)": float(
            (births.iloc[-1] / births.iloc[0] - 1) * 100
        ),
        "2025년 자연증가건수(명)": float(data.loc[data["연도"] == END_YEAR, "자연증가건수(명)"].iloc[0]),
    }
    pd.Series(key_rows, name="값").to_csv(
        OUTPUT_DIR / "핵심지표.csv", encoding="utf-8-sig"
    )


def save_charts(data: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    years = data["연도"]
    births = data["출생아수(명)"]

    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.plot(years, births, color="#1261A0", linewidth=2.4, label="출생아수")
    ax.plot(
        years,
        data["출생아수_5년이동평균(명)"],
        color="#F28E2B",
        linewidth=2,
        label="5년 이동평균",
    )
    ax.fill_between(years, births, color="#1261A0", alpha=0.10)
    ax.set_title("1970~2025년 출생아수 추이", fontsize=17, pad=14)
    ax.set_xlabel("연도")
    ax.set_ylabel("출생아수 (명)")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    ax.ticklabel_format(axis="y", style="plain")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "출생아수_라인그래프.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True)
    chart_specs = [
        ("자연증가건수(명)", "자연증가건수", "#59A14F"),
        ("조출생률(천명당)", "조출생률", "#E15759"),
        ("합계출산율(명)", "합계출산율", "#B07AA1"),
        ("출생성비(명)", "출생성비", "#F28E2B"),
    ]
    for ax, (column, title, color) in zip(axes.flat, chart_specs):
        ax.plot(years, data[column], color=color, linewidth=2)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
        ax.set_ylabel("값")
    fig.suptitle("출생 관련 주요 지표 추이", fontsize=18)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "주요지표_추이.png", dpi=160)
    plt.close(fig)


def main() -> None:
    input_path = find_input_file()
    font_name = configure_korean_font()
    cleaned = load_and_clean(input_path)
    analysis = enrich_analysis(cleaned)
    save_analysis_tables(analysis)
    save_charts(analysis)

    births = analysis["출생아수(명)"]
    print(f"입력 파일: {input_path.name}")
    print(f"분석 기간: {analysis['연도'].min()}~{analysis['연도'].max()} ({len(analysis)}개 연도)")
    print(f"출생아수 최대: {int(births.max()):,}명 ({int(analysis.loc[births.idxmax(), '연도'])}년)")
    print(f"출생아수 최소: {int(births.min()):,}명 ({int(analysis.loc[births.idxmin(), '연도'])}년)")
    print(f"1970년 대비 2025년 증감률: {(births.iloc[-1] / births.iloc[0] - 1) * 100:.1f}%")
    print(f"한글 폰트: {font_name}")
    print(f"결과 폴더: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()