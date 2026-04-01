import logging
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import asyncio
import random
from deep_translator import GoogleTranslator
from telegram import Bot

# --- [설정 영역] ---
TOKEN = "8480650074:AAHkyapxigLVh9FNquAeJ2fbLHu_jZOOwOo"
GROUP_CHAT_ID = "-1003800425149" 

# 필터링 키워드를 조금 더 포괄적으로 수정
KEYWORDS = ['uranium', 'nuclear', 'enrichment', 'centrus', 'itochu', 'cameco', 'orano', 'kazakhstan', 'smr', '우라늄', '원자력', '농축']
MARKET_KEYWORDS = ['nasdaq', 's&p', 'fed', 'stock', 'inflation', 'cpi', 'tsla', 'nvda', 'qqq', 'market', '테슬라', '엔비디아', '증시']

# --- [데이터 수집 함수들] ---

def get_market_status():
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    date_str, time_str = now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')
    
    u_display = "조회 실패"
    fx_display = "조회 중..."

    # 1. 환율
    try:
        fx = yf.Ticker("USDKRW=X")
        fx_data = fx.history(period="2d")
        if not fx_data.empty:
            c_fx = fx_data['Close'].iloc[-1]
            p_fx = fx_data['Close'].iloc[-2]
            fx_chg = ((c_fx - p_fx) / p_fx) * 100
            fx_display = f"₩{c_fx:,.2f} ({fx_chg:+.2f}%)"
    except: fx_display = "서버 지연"

    # 2. 우라늄 선물 (야후 실패 시 인베스팅닷컴 강제 크롤링)
    try:
        u_ticker = yf.Ticker("UX=F")
        u_data = u_ticker.history(period="2d")
        if not u_data.empty:
            u_p = u_data['Close'].iloc[-1]
            u_prev = u_data['Close'].iloc[-2]
            u_chg = ((u_p - u_prev) / u_prev) * 100
            u_display = f"${u_p:,.2f} ({u_chg:+.2f}%)"
        else: raise ValueError()
    except:
        try:
            # 인베스팅닷컴 백업 경로
            url = f"https://www.investing.com/commodities/uranium-futures"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            # 신규 레이아웃 대응
            price = soup.find('span', {'data-test': 'instrument-price-last'}).text
            change = soup.find('span', {'data-test': 'instrument-price-change-percent'}).text
            u_display = f"${price} ({change})"
        except: u_display = "시장 휴장 또는 데이터 지연"

    # 3. 주요 종목 현황
    stock_report = ""
    stocks = {"TSLA": "테슬라", "NVDA": "엔비디아", "QQQ": "나스닥100", "TSLL": "테슬라2배", "NVDL": "엔비디아2배"}
    for ticker, name in stocks.items():
        try:
            s = yf.Ticker(ticker)
            s_d = s.history(period="2d")
            if not s_d.empty:
                c_s = s_d['Close'].iloc[-1]
                p_s = s_d['Close'].iloc[-2]
                s_chg = ((c_s - p_s) / p_s) * 100
                stock_report += f"🔹{name}: `${c_s:.2f}` ({s_chg:+.2f}%)\n"
        except: continue

    return (f"☢️ **[금융 시황 리포트]**\n"
            f"📅 `{date_str} {time_str}` (KST)\n\n"
            f"💰 **우라늄 선물:** `{u_display}`\n"
            f"💵 **원/달러 환율:** `{fx_display}`\n\n"
            f"📈 **주요 종목 현황**\n{stock_report}")

def fetch_news(query, days=1):
    news_list = []
    # 검색 쿼리 최적화 (언어 설정을 영어로 하여 더 많은 데이터 수집)
    url = f"https://news.google.com/rss/search?q={query}+when:{days}d&hl=en-US&gl=US&ceid=US:en"
    try:
        res = requests.get(url, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        items = soup.find_all('item', limit=30) # 더 많은 샘플 수집
        for item in items:
            news_list.append({'title': item.title.text, 'link': item.link.text})
    except: pass
    return news_list

def get_integrated_articles(days=1):
    # 검색 키워드 강화
    query = "(Uranium+OR+Nuclear+OR+Cameco+OR+Kazatomprom)"
    raw_news = fetch_news(query, days=days)
    report = f"📰 **[우라늄/원자력 핵심 뉴스]**\n"
    count = 0
    tr = GoogleTranslator(source='en', target='ko')
    
    for item in raw_news:
        if count >= 5: break
        # 필터링 조건 완화 (대소문자 구분 없이 제목에 키워드 포함 시 통과)
        if any(kw.lower() in item['title'].lower() for kw in KEYWORDS):
            try:
                translated_title = tr.translate(item['title'])
                report += f"🔹 {translated_title}\n🔗 [원문]({item['link']})\n\n"
                count += 1
            except: continue
            
    return report if count > 0 else "📭 최근 업데이트된 우라늄 뉴스 없음"

def get_market_analysis(days=1):
    # 검색 키워드 강화
    query = "(Nasdaq+summary+OR+Federal+Reserve+OR+Stock+market+analysis)"
    raw_news = fetch_news(query, days=days)
    report = f"🇺🇸 **[미 증시 시황 분석 요약]**\n"
    count = 0
    tr = GoogleTranslator(source='en', target='ko')
    
    for item in raw_news:
        if count >= 6: break
        if any(kw.lower() in item['title'].lower() for kw in MARKET_KEYWORDS):
            try:
                translated_title = tr.translate(item['title'])
                report += f"📊 {translated_title}\n🔗 [원문]({item['link']})\n\n"
                count += 1
            except: continue
            
    return report if count > 0 else "📭 최근 업데이트된 증시 분석 없음"

# --- [메인 함수] ---

async def main():
    bot = Bot(token=TOKEN)
    full_report = "🌅 **오늘의 통합 경제 브리핑**\n\n"
    full_report += get_market_status() + "\n"
    full_report += get_market_analysis(days=1) + "\n"
    full_report += get_integrated_articles(days=1)
    
    await bot.send_message(chat_id=GROUP_CHAT_ID, text=full_report, parse_mode='Markdown', disable_web_page_preview=True)
    print("✅ 전송 완료")

if __name__ == "__main__":
    asyncio.run(main())
