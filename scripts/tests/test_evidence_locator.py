from openpyxl import Workbook

from evidence_locator import build_docling_evidence, build_workbook_evidence


def test_workbook_evidence_preserves_formulas_values_and_blanks(tmp_path):
    source = tmp_path / "sample.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "订单明细"
    sheet["A1"] = "订单"
    sheet["B1"] = None
    sheet["C1"] = "净额"
    sheet["A2"] = "ORD-004"
    sheet["B2"] = 10
    sheet["C2"] = "=B2*2"
    book.save(source)

    appendix, evidence = build_workbook_evidence(source)

    assert "订单明细 (A1:C2)" in appendix
    assert "`=B2*2`" in appendix
    assert evidence["sheets"][0]["rows"][0]["values"] == ["订单", None, "净额"]
    assert evidence["sheets"][0]["formula_cells"][0]["formula"] == "=B2*2"
    assert evidence["items"][1]["locator"] == {
        "kind": "xlsx", "sheet": "订单明细", "range": "A2:C2"
    }


def test_docling_evidence_preserves_page_and_converts_bbox_origin():
    evidence = build_docling_evidence(
        {
            "pages": {"1": {"page_no": 1, "size": {"width": 600, "height": 800}}},
            "texts": [
                {
                    "text": "协议于 2024-12-19 签署",
                    "prov": [
                        {
                            "page_no": 1,
                            "bbox": {
                                "l": 10, "t": 780, "r": 200, "b": 750,
                                "coord_origin": "BOTTOMLEFT",
                            },
                        }
                    ],
                }
            ],
            "tables": [],
        }
    )

    assert evidence["status"] == "success"
    assert evidence["items"][0]["locator"] == {"kind": "pdf", "page": 1}
    assert evidence["pages"][0]["blocks"][0]["bbox"] == [10, 20, 200, 50]
