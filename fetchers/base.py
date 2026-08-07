# -*- coding: utf-8 -*-
"""Fetcher 共用基礎:HTTP session、robots.txt 檢查、delay、retry。"""
import time
import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from config import FETCH_DELAY_SECONDS, FETCH_RETRIES, FETCH_TIMEOUT, USER_AGENT

logger = logging.getLogger("fetcher")

_robots_cache = {}


def robots_allowed(url):
    """檢查 robots.txt 是否允許抓取;robots.txt 無法取得時視為允許。"""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _robots_cache:
        rp = RobotFileParser()
        try:
            rp.set_url(base + "/robots.txt")
            rp.read()
            _robots_cache[base] = rp
        except Exception:
            _robots_cache[base] = None
    rp = _robots_cache[base]
    if rp is None:
        return True
    try:
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True


def http_get(url, session=None, check_robots=True):
    """帶 retry 與 delay 的 GET;robots.txt 不允許時回傳 None。"""
    if check_robots and not robots_allowed(url):
        logger.warning("robots.txt 不允許抓取:%s", url)
        return None
    sess = session or requests.Session()
    headers = {"User-Agent": USER_AGENT}
    last_err = None
    for attempt in range(FETCH_RETRIES + 1):
        try:
            resp = sess.get(url, headers=headers, timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
            time.sleep(FETCH_DELAY_SECONDS)
            return resp
        except requests.RequestException as e:
            last_err = e
            time.sleep(FETCH_DELAY_SECONDS * (attempt + 1))
    logger.error("抓取失敗 %s:%s", url, last_err)
    return None
