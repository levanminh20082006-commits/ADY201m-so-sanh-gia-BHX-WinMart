"""Shared helpers. Everything built here is SYNTHETIC TEST DATA (never real collected data)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def bhx_product(code, name, price, list_price=None, brand="TestBrand", flash=None, specs=None, unit="Hộp"):
    product = {"id": int(code[-4:]), "productCode": code, "name": name, "fullName": name, "brandName": brand,
               "url": f"/test/{code}", "unit": unit, "exchangeQuantity": 1,
               "productPrices": [{"price": price, "sysPrice": list_price or price, "discountPercent": 0,
                                  "storeId": 9999, "isCanBuy": True}],
               "specifications": specs or [], "category": {"name": "Test"}}
    if flash:
        product["lstCampaingInfo"] = [{"startTime": "2026-01-01T16:00:00+07:00", "dueTime": "2026-01-01T18:00:00+07:00",
                                       "productPrice": {"price": flash}}]
    return product


def winmart_item(code, name, sale, price=None, brand="TESTBRAND", barcode="8930000000000"):
    return {"id": f"uuid-{code}", "itemNo": code, "sku": f"{code}HOP", "uom": "HOP", "name": name, "description": name, "brandName": brand,
            "barcode": barcode, "salePrice": sale, "price": price or sale, "uomName": "Hộp",
            "quantityPerUnit": 1.0, "quantity": 5.0, "categoryName": "Test", "seoName": f"test--s{code}"}


def page_record(store, products, run_id="test_run", collected_at="2026-01-01T10:00:00+07:00",
                dom_cards=None, slug="test-cat"):
    if store == "bhx":
        response = {"url": "https://api.test/Category/AjaxProduct", "status": 200,
                    "request_body": '{"provinceId":1,"storeId":9999,"PageIndex":1,"PageSize":10}',
                    "body": {"data": {"products": products}}}
    else:
        response = {"url": "https://api.test/item/category?pageNumber=1&pageSize=8&storeCode=1&storeGroupCode=2",
                    "status": 200, "request_body": None, "body": {"data": {"items": products}}}
    return {"run_id": run_id, "store": store, "group": "test", "category_slug": slug,
            "source_url": f"https://test/{slug}", "collected_at": collected_at, "status": "ok",
            "responses": [response], "dom_cards": dom_cards or []}


@pytest.fixture
def helpers():
    return {"bhx_product": bhx_product, "winmart_item": winmart_item, "page_record": page_record}
