# -*- coding: utf-8 -*-
"""商工登記查詢(GCIS 開放 API)煙霧測試。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fetchers.findbiz import query_company

if __name__ == "__main__":
    r = query_company("華碩電腦股份有限公司")
    print("status:", r["status"])
    print(json.dumps(r["results"][:1], ensure_ascii=False, indent=1))
