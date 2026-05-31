from __future__ import annotations

import hashlib
import http.cookiejar
import json
import re
import time
import urllib.parse
import urllib.request
from typing import Any

from ..models import Notification
from .base import Watcher, as_list


APP_KEY = "12574478"
ITEM_DETAIL_API = "mtop.alibaba.damai.detail.getdetail"
ITEM_DETAIL_VERSION = "1.2"
ITEM_LEGACY_API = "mtop.damai.item.detail.getdetail"
ITEM_LEGACY_VERSION = "1.0"


class DamaiWatcher(Watcher):
    def check(self, state: dict[str, Any], notify_on_first_run: bool = False) -> list[Notification]:
        item_id = str(self.config.get("item_id") or "")
        if not item_id:
            raise RuntimeError(f"{self.name}: damai watcher requires item_id")

        project = fetch_project(item_id)
        fingerprint = compact_json(
            {
                "tour_status": project.get("tour_status"),
                "project_status": project.get("project_status"),
                "raw_buy_text": project.get("raw_buy_text"),
                "price_range": project.get("price_range"),
                "perform_dates": project.get("perform_dates"),
            }
        )
        available = likely_available(project)
        first_run = "fingerprint" not in state
        changed = fingerprint != state.get("fingerprint")
        previous_available = bool(state.get("available"))

        state.update(
            {
                "fingerprint": fingerprint,
                "available": available,
                "checked_at": int(time.time()),
                "title": project.get("title"),
            }
        )

        if first_run and not notify_on_first_run and not self.config.get("notify_on_first_run", False):
            print(f"[{self.name}] initialized Damai monitor; available={available}")
            return []

        notify_on_change = bool(self.config.get("notify_on_change", True))
        should_notify = (available and not previous_available) or (changed and notify_on_change)
        if not should_notify:
            print(f"[{self.name}] no Damai status change; available={available}")
            return []

        return [
            Notification(
                title=str(self.config.get("title") or "Damai ticket status changed"),
                body=format_summary(project, self.config),
                url=f"https://m.damai.cn/shows/item.html?itemId={item_id}",
                meta={"available": available, "item_id": item_id},
            )
        ]


def compact_json(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


def token_from_cookiejar(cookiejar: http.cookiejar.CookieJar) -> str:
    for cookie in cookiejar:
        if cookie.name == "_m_h5_tk":
            return cookie.value.split("_")[0]
    return ""


def mtop_sign(token: str, timestamp_ms: str, data: str) -> str:
    raw = f"{token}&{timestamp_ms}&{APP_KEY}&{data}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def mtop_call(api: str, version: str, data: dict[str, Any]) -> dict[str, Any]:
    cookiejar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar))

    for _ in range(2):
        timestamp_ms = str(int(time.time() * 1000))
        data_text = compact_json(data)
        params = {
            "jsv": "2.7.2",
            "appKey": APP_KEY,
            "t": timestamp_ms,
            "sign": mtop_sign(token_from_cookiejar(cookiejar), timestamp_ms, data_text),
            "api": api,
            "v": version,
            "type": "json",
            "dataType": "json",
            "data": data_text,
        }
        url = f"https://mtop.damai.cn/h5/{api}/{version}/?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 Mobile/15E148"
                ),
                "Referer": "https://m.damai.cn/",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        payload = json.loads(opener.open(request, timeout=20).read().decode("utf-8"))
        ret = " ".join(payload.get("ret", []))
        if "TOKEN" in ret or "令牌" in ret:
            continue
        return payload
    raise RuntimeError("Damai token handshake failed")


def fetch_project(item_id: str) -> dict[str, Any]:
    payload = mtop_call(
        ITEM_DETAIL_API,
        ITEM_DETAIL_VERSION,
        {"itemId": item_id, "dmChannel": "damai@damaih5_h5"},
    )
    ret = " ".join(payload.get("ret", []))
    if "SUCCESS" not in ret:
        raise RuntimeError(f"Damai API failed: {ret}")

    result = json.loads(payload["data"]["result"])
    item_component = result["detailViewComponentMap"]["item"]
    static = item_component.get("staticData", {})
    item_base = static.get("itemBase", {})
    item = item_component.get("item", {})
    legacy = fetch_legacy_project(item_id)

    return {
        "title": item_base.get("itemName") or item.get("title") or "",
        "city": item_base.get("cityName", ""),
        "show_time": item_base.get("showTime", ""),
        "project_status": item_base.get("projectStatus", "") or legacy.get("project_status", ""),
        "price_range": item.get("priceRange") or (item_component.get("price") or {}).get("range") or "",
        "tour_status": extract_tour_status(legacy, item_id),
        "perform_dates": extract_perform_dates(item_base),
        "raw_buy_text": legacy.get("buy_text", ""),
    }


def fetch_legacy_project(item_id: str) -> dict[str, Any]:
    payload = mtop_call(
        ITEM_LEGACY_API,
        ITEM_LEGACY_VERSION,
        {"itemId": item_id, "dmChannel": "damai@damaih5_h5"},
    )
    data = payload.get("data") or {}
    return {
        "tour": (data.get("guide") or {}).get("tour") or {},
        "project_status": (data.get("item") or {}).get("projectStatus", ""),
        "buy_text": (data.get("buyButton") or {}).get("text", ""),
    }


def extract_tour_status(legacy: dict[str, Any], item_id: str) -> str:
    tour = legacy.get("tour") or {}
    for project in tour.get("projectList", []):
        if str(project.get("itemId")) == item_id:
            return str(project.get("saleStatus", ""))
    return ""


def extract_perform_dates(item_base: dict[str, Any]) -> list[str]:
    dates = []
    for note in item_base.get("serviceNotes", []):
        text = note.get("tagDescJson", "")
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        for rule in data.get("performRules", []):
            perform_date = re.sub(r"\s+", " ", rule.get("performDate", "")).strip()
            if perform_date:
                dates.append(perform_date)
    return dates


def likely_available(project: dict[str, Any]) -> bool:
    status_text = " ".join(
        [
            str(project.get("tour_status", "")),
            str(project.get("raw_buy_text", "")),
            str(project.get("project_status", "")),
        ]
    )
    bad_words = ["预约", "无票", "缺货", "暂时", "售罄", "登记"]
    good_words = ["热卖", "立即购买", "购买", "开抢", "可购", "有票"]
    return any(word in status_text for word in good_words) and not any(word in status_text for word in bad_words)


def format_summary(project: dict[str, Any], config: dict[str, Any]) -> str:
    target_text = config.get("target_text") or "see your config"
    target_dates = as_list(config.get("target_dates")) or ["see the Damai page"]
    dates = project.get("perform_dates") or target_dates
    lines = [
        str(project.get("title") or "Damai project"),
        f"Target: {target_text}",
        f"Current tour status: {project.get('tour_status') or 'unknown'}",
        f"Buy button: {project.get('raw_buy_text') or 'unknown'}",
        f"Price range: {project.get('price_range') or 'unknown'}",
        "",
        "Dates:",
    ]
    lines.extend(f"- {date}" for date in dates)
    return "\n".join(lines)
