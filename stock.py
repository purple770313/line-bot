from typing import Optional
import yfinance as yf

# 指數代碼對照
INDEX_MAP = {
    # 美股指數
    "大盤": "^GSPC",
    "s&p": "^GSPC",
    "s&p500": "^GSPC",
    "sp500": "^GSPC",
    "道瓊": "^DJI",
    "道瓊斯": "^DJI",
    "dji": "^DJI",
    "dow": "^DJI",
    "那斯達克": "^IXIC",
    "nasdaq": "^IXIC",
    "費半": "^SOX",
    "sox": "^SOX",
    "russell": "^RUT",
    "羅素": "^RUT",
    "rut": "^RUT",
    "nasdaq100": "^NDX",
    "那斯達克100": "^NDX",
    "ndx": "^NDX",
    "恐慌指數": "^VIX",
    "vix": "^VIX",
    # 台股指數
    "台股": "^TWII",
    "加權": "^TWII",
    "twii": "^TWII",
    "櫃買": "^TWOII",
    "otc": "^TWOII",
}

# 定時推播的指數清單
DAILY_INDICES = [
    ("^GSPC", "S&P 500"),
    ("^DJI", "道瓊"),
    ("^IXIC", "那斯達克"),
    ("^SOX", "費半"),
    ("^NDX", "那斯達克100"),
    ("^RUT", "羅素2000"),
    ("^VIX", "恐慌指數"),
    ("^TWII", "台灣加權"),
]


def _fetch(symbol: str) -> Optional[dict]:
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        current = info.get("regularMarketPrice") or info.get("currentPrice")
        prev_close = info.get("previousClose")

        if current is None or prev_close is None:
            hist = ticker.history(period="5d")
            if hist.empty:
                return None
            current = float(hist["Close"].iloc[-1])
            prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current

        return {
            "name": info.get("longName") or info.get("shortName") or symbol,
            "symbol": symbol.upper(),
            "current": float(current),
            "prev_close": float(prev_close),
            "currency": info.get("currency", "USD"),
        }
    except Exception:
        return None


def format_quote(symbol: str) -> str:
    data = _fetch(symbol)
    if data is None:
        return f"❌ 找不到 {symbol} 的資料，請確認代號是否正確"

    change = data["current"] - data["prev_close"]
    pct = (change / data["prev_close"]) * 100
    arrow = "▲" if change >= 0 else "▼"
    sign = "+" if change >= 0 else ""

    return (
        f"📊 {data['name']} ({data['symbol']})\n"
        f"收盤價：{data['current']:,.2f} {data['currency']}\n"
        f"漲跌：{arrow} {sign}{change:,.2f} ({sign}{pct:.2f}%)\n"
        f"前收：{data['prev_close']:,.2f} {data['currency']}"
    )


def daily_summary() -> str:
    lines = ["📋 每日收盤摘要\n"]
    for symbol, label in DAILY_INDICES:
        data = _fetch(symbol)
        if data is None:
            lines.append(f"  {label}：查詢失敗")
            continue
        change = data["current"] - data["prev_close"]
        pct = (change / data["prev_close"]) * 100
        arrow = "▲" if change >= 0 else "▼"
        sign = "+" if change >= 0 else ""
        lines.append(f"{arrow} {label}：{data['current']:,.2f}  {sign}{pct:.2f}%")
    return "\n".join(lines)


def query(text: str) -> str:
    text_lower = text.strip().lower()

    if text_lower in ("說明", "help", "?", "？"):
        return HELP_TEXT

    # 台股個股：純數字 4 碼 → 加 .TW
    if text_lower.isdigit() and len(text_lower) == 4:
        return format_quote(f"{text_lower}.TW")

    # 中文關鍵字 → 指數代碼
    symbol = INDEX_MAP.get(text_lower, text.strip().upper())
    return format_quote(symbol)


HELP_TEXT = """📊 查詢指令說明

🇺🇸 美股個股（輸入代號）
  AAPL TSLA NVDA MSFT AMZN

🇺🇸 美股指數
  大盤 / S&P500
  道瓊 / DOW
  那斯達克 / NASDAQ
  那斯達克100 / NDX
  費半 / SOX
  羅素 / Russell
  恐慌指數 / VIX

🇹🇼 台股個股（輸入 4 碼）
  2330  2317  2454

🇹🇼 台股指數
  台股 / 加權
  櫃買 / OTC

輸入「說明」顯示此選單"""
