import logging
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import asyncio
from deep_translator import GoogleTranslator
from telegram import Bot

# --- [설정 영역] ---
TOKEN = "8480650074:AAHkyapxigLVh9FNquAeJ2fbLHu_jZOOwOo"
GROUP_CHAT_ID = "-1003800425149"

KEYWORDS = ['uranium', 'enrichment', 'centrus', 'itochu', 'cameco', 'orano', 'reprocess', 'smr', 'kazakhstan', '우라늄', '농축', '센트러스', '이토추', '카메코', '오라노', '재처리', 'SMR']
MARKET_KEYWORDS = ['Nasdaq', 'S&P 500', 'Federal Reserve', 'Wall Street', 'Stock Market', 'Inflation', 'CPI', 'TSLA', 'NVDA', 'QQQ', 'Market Summary']

# --- [데이터 수집 함수들] ---

def get_market_status():
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    date_str, time_str = now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')
    
    # 1. 환율 및 우라늄 선물
    u_display, fx_display = "데이터 확인 불가", "조회 중..."
    try:
        fx = yf.Ticker("USDKRW=X")
        fx_data = fx.history(period="2d")
        if not fx_data.empty:
            c_fx, p_fx = fx_data['Close'].iloc[-1], fx_data['Close'].iloc[-2]
            fx_chg = ((c_fx - p_fx) / p_fx) * 100
            fx_display = f"₩{c_fx:,.2f} ({fx_chg:+.2f}%)"
    except: fx_display = "환율 서버 지연"
    
    try:
        u_ticker = yf.Ticker("UX=F")
        u_data = u_ticker.history(period="2d")
        if not u_data.empty:
            u_p, u_prev = u_data['Close'].iloc[-1], u_data['Close'].iloc[-2]
            u_chg = ((u_p - u_prev) / u_prev) * 100
            u_display = f"${u_p:,.2f} ({u_chg:+.2f}%)"
    except: u_display = "시장 정보 수집 중"

    # 2. 주요 종목 가격 추가 (추가된 부분)
    stock_report = ""
    stocks = {"TSLA": "테슬라", "NVDA": "엔비디아", "QQQ": "나스닥100"}
    for ticker, name in stocks.items():
        try:
            s = yf.Ticker(ticker)
            s_d = s.history(period="2d")
            c_s, p_s = s_d['Close'].iloc[-1], s_d['Close'].iloc[-2]
            s_chg = ((c_s - p_s) / p_s) * 100
            stock_report += f"🔹{name}: `${c_s:.2f}` ({s_chg:+.2f}%)\n"
        except: continue

    return (f"☢️ **[실시간 금융 시황]**\n"
            f"📅 `{date_str} {time_str}` (KST)\n\n"
            f"💰 **우라늄 선물:** `{u_display}`\n"
            f"💵 **원/달러 환율:** `{fx_display}`\n\n"
            f"📈 **주요 종목 현황**\n{stock_report}")

def fetch_news(query, days=1):
    news_list = []
    url = f"https://news.google.com/rss/search?q={query}+when:{days}d&hl=en-US&gl=US&ceid=US:en"
    try:
        res = requests.get(url, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for item in soup.find_all('item', limit=15):
            news_list.append({'title': item.title.text, 'link': item.link.text})
    except: pass
    return news_list

def get_integrated_articles(days=1):
    raw_news = fetch_news("Uranium+enrichment+OR+Centrus+OR+Itochu+OR+Cameco+OR+Orano", days=days)
    report = f"📰 **[우라늄 글로벌 핵심 뉴스]**\n"
    count, tr = 0, GoogleTranslator(source='en', target='ko')
    for item in raw_news:
        if count >= 5: break
        if any(kw.lower() in item['title'].lower() for kw in KEYWORDS):
            report += f"🔹 {tr.translate(item['title'])}\n🔗 [원문]({item['link']})\n\n"
            count += 1
    return report if count > 0 else "📭 최신 우라늄 뉴스 없음"

def get_market_analysis(days=1):
    raw_news = fetch_news("Nasdaq+Market+Summary+OR+US+Stock+Market+Analysis", days=days)
    report = f"🇺🇸 **[미 증시 시황 분석 요약]**\n"
    count, tr = 0, GoogleTranslator(source='en', target='ko')
    for item in raw_news:
        if count >= 5: break
        if any(kw.lower() in item['title'].lower() for kw in MARKET_KEYWORDS):
            report += f"📊 {tr.translate(item['title'])}\n🔗 [원문]({item['link']})\n\n"
            count += 1
    return report if count > 0 else "📭 최신 증시 분석 없음"

# --- [GitHub Actions 실행 메인 함수] ---

async def main():
    bot = Bot(token=TOKEN)
    full_report = "🌅 **[Good Morning] 오늘의 통합 브리핑**\n\n"
    full_report += get_market_status() + "\n"
    full_report += get_market_analysis(days=1) + "\n"
    full_report += get_integrated_articles(days=1)
    
    await bot.send_message(chat_id=GROUP_CHAT_ID, text=full_report, parse_mode='Markdown', disable_web_page_preview=True)
    print("✅ 전송 완료")

if __name__ == "__main__":
    asyncio.run(main())
