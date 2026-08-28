#!/usr/bin/env python3
"""Refresh final dataset statistics and report charts from annotations.json."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analytics.absa_analytics import generate_dataset_statistics


DATASET = Path("annotation/annotations.json")
REPORT = Path("izvestaj-analize.json")
FIGURES = Path("docs/figures")


def label_bars(axis) -> None:
    for patch in axis.patches:
        value = patch.get_width() if patch.get_width() > patch.get_height() else patch.get_height()
        if patch.get_width() > patch.get_height():
            axis.text(patch.get_width() + max(value * 0.01, 10), patch.get_y() + patch.get_height() / 2, f"{int(value):,}".replace(",", "."), va="center", fontsize=9)
        else:
            axis.text(patch.get_x() + patch.get_width() / 2, patch.get_height() + max(value * 0.01, 10), f"{int(value):,}".replace(",", "."), ha="center", fontsize=9)


def main() -> None:
    statistics = generate_dataset_statistics(DATASET)
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {}
    report["dataset_statistics"] = statistics
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10})

    categories = statistics["category_distribution"]
    figure, axis = plt.subplots(figsize=(9, 5.4))
    names = list(categories)
    values = [categories[name]["count"] for name in names]
    axis.barh(names[::-1], values[::-1], color="#3569a8")
    axis.set_xlabel("Број анотација")
    axis.set_title("Расподела аспектних категорија")
    axis.grid(axis="x", alpha=0.2)
    label_bars(axis)
    figure.tight_layout()
    figure.savefig(FIGURES / "raspodela_kategorija.png", dpi=180)
    plt.close(figure)

    sentiments = statistics["sentiment_distribution"]
    figure, axis = plt.subplots(figsize=(7.5, 4.6))
    names = list(sentiments)
    values = [sentiments[name]["count"] for name in names]
    axis.bar(names, values, color=["#3a8f5c", "#b64b4b", "#777777", "#8a63a8"])
    axis.set_ylabel("Број анотација")
    axis.set_title("Расподела sentiment ознака")
    axis.grid(axis="y", alpha=0.2)
    label_bars(axis)
    figure.tight_layout()
    figure.savefig(FIGURES / "raspodela_sentimenta.png", dpi=180)
    plt.close(figure)

    figure, axes = plt.subplots(1, 2, figsize=(9, 4.4))
    review_values = [statistics["valid_reviews"], statistics["noise_reviews"]]
    axes[0].bar(["DA", "NE"], review_values, color=["#3a8f5c", "#b64b4b"])
    axes[0].set_title("Статус коментара")
    axes[0].set_ylabel("Број коментара")
    axes[0].grid(axis="y", alpha=0.2)
    label_bars(axes[0])
    annotation_values = [statistics["explicit"]["count"], statistics["implicit"]["count"]]
    axes[1].bar(["Експлицитни", "Имплицитни"], annotation_values, color=["#3569a8", "#d4943a"])
    axes[1].set_title("Тип аспекта")
    axes[1].set_ylabel("Број анотација")
    axes[1].grid(axis="y", alpha=0.2)
    label_bars(axes[1])
    figure.suptitle("Преглед коначног скупа")
    figure.tight_layout()
    figure.savefig(FIGURES / "statistika_pregled.png", dpi=180)
    plt.close(figure)
    print(json.dumps({
        "total_reviews": statistics["total_reviews"],
        "valid_reviews": statistics["valid_reviews"],
        "noise_reviews": statistics["noise_reviews"],
        "total_annotations": statistics["total_annotations"],
        "explicit": statistics["explicit"]["count"],
        "implicit": statistics["implicit"]["count"],
        "annotation_density": statistics["annotation_density"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
