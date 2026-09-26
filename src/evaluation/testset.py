from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json

TEST_SET_SIZE = 10
QUESTION_PLAN = ["summary", "authors", "date", "categories"]  # xoay vong -> 3/3/2/2

QUESTION_TEMPLATES = {
    "summary": "What is the summary of the paper '{title}'?",
    "authors": "Who authored the paper '{title}'?",
    "date": "When was the paper '{title}' published?",
    "categories": "What categories does the paper '{title}' belong to?",
}


def _ground_truth(row: pd.Series, question_type: str) -> str:
    if question_type == "summary":
        return first_sentence(row["summary"])
    if question_type == "authors":
        return row["authors_joined"]
    if question_type == "date":
        return row["published"]
    return row["categories_joined"]


def _is_eligible(row: pd.Series, question_type: str) -> bool:
    if question_type == "authors":
        return bool(row["authors_joined"])
    if question_type == "categories":
        return bool(row["categories_joined"])
    return True


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    papers = df.copy()
    for column in ("paper_id", "title", "summary", "authors_joined", "categories_joined"):
        papers[column] = papers[column].fillna("").astype(str).map(normalize_whitespace)
    papers["published"] = pd.to_datetime(papers["published"], errors="coerce").dt.strftime("%Y-%m-%d")

    papers = papers[
        (papers["paper_id"] != "")
        & (papers["title"] != "")
        & (papers["summary"] != "")
        & papers["published"].notna()
        & ~papers["title"].str.contains("'")  # qa.py lay title nam giua 2 dau '...'
    ]
    papers = papers.drop_duplicates(subset="paper_id").sort_values("paper_id").reset_index(drop=True)
    if len(papers) < TEST_SET_SIZE:
        raise ValueError(f"Can it nhat {TEST_SET_SIZE} papers hop le de tao test set, hien co {len(papers)}.")

    test_set: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for position in range(TEST_SET_SIZE):
        # thu dang cau hoi theo ke hoach truoc; neu khong con paper phu hop thi chuyen sang dang ke tiep
        for shift in range(len(QUESTION_PLAN)):
            question_type = QUESTION_PLAN[(position + shift) % len(QUESTION_PLAN)]
            candidates = [
                row for _, row in papers.iterrows() if row["paper_id"] not in used_ids and _is_eligible(row, question_type)
            ]
            if candidates:
                break
        else:
            raise ValueError("Khong du paper hop le de tao test set.")
        if shift:
            print(f"[testset] Canh bao: khong co paper cho dang '{QUESTION_PLAN[position % len(QUESTION_PLAN)]}', dung '{question_type}'.")
        # chon rai deu tren toan bo corpus thay vi chi lay 10 bai dau
        row = candidates[(position * len(candidates)) // (TEST_SET_SIZE - position) % len(candidates)]
        used_ids.add(row["paper_id"])
        test_set.append(
            {
                "id": f"eval_{position + 1:03d}",
                "question_type": question_type,
                "question": QUESTION_TEMPLATES[question_type].format(title=row["title"]),
                "ground_truth": _ground_truth(row, question_type),
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )

    write_json(output_path, test_set)
    return test_set