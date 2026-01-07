import math
from typing import List, Optional
import requests
from bs4 import BeautifulSoup

def get_price_fragment(collection, model, backdrop):
    url = f"https://fragment.com/gifts/{collection}?attr%5BModel%5D=%5B%22{model}%22%5D&attr%5BBackdrop%5D=%5B%22{backdrop}%22%5D"
    listik = []
    data = requests.get(url)
    div = BeautifulSoup(data.content, "lxml")
    divchik = div.find("div", class_="tm-catalog-grid js-autoscroll-body")
    if divchik:
        for child in divchik.find_all("a", recursive=False):
            priceik = child.find("div", class_="tm-grid-item-values")
            if priceik is not None:
                new_price = priceik.text.split("\n")
                price = new_price[1]
                status = new_price[2]
                if status == "Sold":
                    listik.append(float(price))
    else:
        return listik
    return listik

def to_amounts(actions: List[dict]) -> List[float]:
    """Безопасно извлечь и привести amount к float, отбросить нули/некорректные."""
    out = []
    for a in actions:
        try:
            val = float(a.get("amount", 0))
            type = str(a.get("type", "price_update"))
            if val > 0 and math.isfinite(val) and type == "purchase":
                out.append(val)
        except Exception:
            continue
    return out

def iqr_filter(xs: List[float], k: float = 1.5) -> List[float]:
    """Удалить выбросы по IQR: [Q1 - k*IQR, Q3 + k*IQR]"""
    if not xs:
        return []
    s = sorted(xs)
    n = len(s)
    q1 = s[n//4]
    q3 = s[(3*n)//4]
    iqr = q3 - q1
    low = q1 - k * iqr
    high = q3 + k * iqr
    return [x for x in s if low <= x <= high]

def median(xs: List[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        raise ValueError("empty")
    mid = n // 2
    if n % 2 == 1:
        return xs[mid]
    return 0.5 * (xs[mid-1] + xs[mid])

def trimmed_mean(xs: List[float], trim_frac: float = 0.2) -> float:
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        raise ValueError("empty")
    k = int(n * trim_frac)
    if n - 2*k <= 0:
        return sum(xs) / n
    trimmed = xs[k: n-k]
    return sum(trimmed) / len(trimmed)

def robust_price_estimate(amounts: List[float] = None,
                          n_recent: int = 10,
                          method: str = "iqr_trimmed") -> Optional[float]:
    """
    Возвращает робастную оценку цены.
    method: "median", "trimmed", "iqr_trimmed", "winsorized", "mad_median"
    """
    if not amounts:
        print('No Amounts')
        return None

    if len(amounts) < 2:
        return None

    # берем только первые n_recent (предполагаются наиболее свежие)
    use = amounts[:n_recent]

    if method == "iqr_trimmed":
        filtered = iqr_filter(use, k=1.5)
        if not filtered:
            # fallback
            return median(use)
        return trimmed_mean(filtered, trim_frac=0.1)