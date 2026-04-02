import logging
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import asyncio
import random
from deep_translator import GoogleTranslator
from telegram import Bot

# --- [설정 영역] ---
TOKEN = "8480650074:AAHkyapxigLVh9FNquAeJ2fbLHu_jZOOwOo"
GROUP_CHAT_ID = "-1003800425149" 

# --- [데이터 수집 함수: 시황 및 주가] ---

def get_market_status():
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    date_str, time_str = now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')
    
    u_display = "데이터 확인 불가"
    fx_display = "연결 중..."

    # 1. 환율
    try:
        fx = yf.Ticker("USDKRW=X")
        fx_data = fx.history(period="3d")
        if not fx_data.empty:
            c_fx = fx_data['Close'].iloc[-1]
            p_fx = fx_data['Close'].iloc[-2]
            fx_chg = ((c_fx - p_fx) / p_fx) * 100
            fx_display = f"₩{c_fx:,.2f} ({fx_chg:+.2f}%)"
    except: fx_display = "서버 지연"

    # 2. 우라늄 가격 (이중 백업)
    try:
        u_ticker = yf.Ticker("UX=F")
        u_data = u_ticker.history(period="7d")
        if not u_data.empty:
            u_p, u_prev = u_data['Close'].iloc[-1], u_data['Close'].iloc[-2]
            u_chg = ((u_p - u_prev) / u_prev) * 100
            u_display = f"${u_p:,.2f} ({u_chg:+.2f}%)"
        else: raise ValueError()
    except:
        try:
            url = "https://www.investing.com/commodities/uranium-futures"
            headers = {'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(110, 125)}.0.0.0 Safari/537.36'}
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            price_tag = soup.select_one('[data-test="instrument-price-last"]')
            u_display = f"${price_tag.text} (실시간)" if price_tag else "조회 지연"
        except: u_display = "인덱스 참조 불가"

    # 3. 주요 종목
    stock_report = ""
    stocks = {"TSLA": "테슬라", "NVDA": "엔비디아", "QQQ": "나스닥100", "CCJ": "카메코", "SMR": "뉴스케일", "SRUUF": "우라늄신탁"}
    for ticker, name in stocks.items():
        try:
            s = yf.Ticker(ticker)
            s_d = s.history(period="3d")
            if not s_d.empty:
                c_s, p_s = s_d['Close'].iloc[-1], s_d['Close'].iloc[-2]
                s_chg = ((c_s - p_s) / p_s) * 100
                stock_report += f"🔹{name}: `${c_s:.2f}` ({s_chg:+.2f}%)\n"
        except: continue

    return (f"☢️ **[금융 시황 리포트]**\n"
            f"📅 `{date_str} {time_str}`\n\n"
            f"💰 **우라늄:** `{u_display}`\n"
            f"💵 **환율:** `{fx_display}`\n\n"
            f"📈 **주요 종목**\n{stock_report}")

# --- [뉴스 수집 함수: 무조건 추출 로직] ---

def fetch_news_unlimited(category="uranium"):
    """구글 뉴스 RSS가 막힐 경우를 대비해 검색 엔진 및 다중 언어 쿼리 사용"""
    news_list = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # 카테고리별 쿼리 조합
    if category == "uranium":
        queries = ["uranium+market+news", "nuclear+energy+Cameco", "SMR+technology+investment", "우라늄+뉴스", "원자력+정책"]
    else:
        queries = ["Nasdaq+index+analysis", "Federal+Reserve+rates", "US+Tech+Stock+News", "미국+증시+전망"]

    for q in queries:
        # 영어(US)와 한국어(KR)를 번갈아 검색하여 무조건 데이터를 확보
        hl_gl = [("en-US", "US"), ("ko-KR", "KR")]
        for hl, gl in hl_gl:
            url = f"https://news.google.com/rss/search?q={q}+when:7d&hl={hl}&gl={gl}&ceid={gl}:{hl.split('-')[0]}"
            try:
                res = requests.get(url, headers=headers, timeout=12)
                soup = BeautifulSoup(res.content, 'xml')
                items = soup.find_all('item', limit=8)
                for item in items:
                    title = item.title.text
                    link = item.link.text
                    # 중복 제거
                    if not any(n['link'] == link for n in news_list):
                        news_list.append({'title': title, 'link': link, 'lang': hl.split('-')[0]})
                if len(news_list) >= 10: break
            except: continue
        if len(news_list) >= 10: break
    
    return news_list

async def main():
    bot = Bot(token=TOKEN)
    tr_to_ko = GoogleTranslator(source='auto', target='ko') # 언어 자동 감지 번역
    
    print("🚀 뉴스 무제한 수집 모드 가동...")
    
    # 1. 시황 파트
    status_part = get_market_status()
    
    # 2. 증시 뉴스 파트
    market_news = fetch_news_unlimited("market")
    m_report = "🇺🇸 **[미국 증시 & 매크로 요약]**\n"
    for i, n in enumerate(market_news[:5]):
        title = tr_to_ko.translate(n['title']) if n['lang'] == 'en' else n['title']
        m_report += f"{i+1}. {title}\n🔗 [원문]({n['link']})\n\n"
    if not market_news: m_report += "📭 최신 증시 데이터 없음\n\n"

    # 3. 우라늄 뉴스 파트
    uranium_news = fetch_news_unlimited("uranium")
    u_report = "📰 **[우라늄 & 원자력 인사이트]**\n"
    for i, n in enumerate(uranium_news[:5]):
        title = tr_to_ko.translate(n['title']) if n['lang'] == 'en' else n['title']
        u_report += f"{i+1}. {title}\n🔗 [원문]({n['link']})\n\n"
    if not uranium_news: u_report += "📭 최신 섹터 데이터 없음\n\n"

    full_report = "🌅 **[무제한 검색] 오늘의 통합 브리핑**\n\n" + status_part + "\n" + m_report + u_report
    
    # 메시지 전송 (길이 초과 방지)
    try:
        await bot.send_message(chat_id=GROUP_CHAT_ID, text=full_report[:4000], parse_mode='Markdown', disable_web_page_preview=True)
        print("✅ 전송 성공")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())
