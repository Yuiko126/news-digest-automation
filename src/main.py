import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import feedparser
import google.generativeai as genai
from datetime import datetime

# 設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# ニュースサイトのRSSフィード URL
RSS_FEEDS = {
    "AI": [
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
    ],
    "セキュリティ": [
        "https://thehackernews.com/feeds/posts/default",
    ],
    "国内": [
        "https://www.nhk.or.jp/rss/news/news.rss",
    ],
    "国外": [
        "https://feeds.bbc.co.uk/news/rss.xml",
    ],
    "エンジニアリング": [
        "https://news.ycombinator.com/rss",
    ],
}

def fetch_articles():
    """RSSフィードから記事を取得"""
    articles = {}
    
    for category, urls in RSS_FEEDS.items():
        articles[category] = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                # 最新5件を取得
                for entry in feed.entries[:5]:
                    articles[category].append({
                        "title": entry.get("title", "タイトルなし"),
                        "link": entry.get("link", ""),
                        "summary": entry.get("summary", ""),
                    })
            except Exception as e:
                print(f"Error fetching {url}: {e}")
    
    return articles

def summarize_with_gemini(articles):
    """Gemini APIを使って記事を要約"""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-3.5-flash")
    
    summaries = {}
    
    for category, items in articles.items():
        summaries[category] = []
        
        for item in items[:5]:  # カテゴリごとに最大5件
            try:
                prompt = f"""
以下のニュース記事を日本語で1行で要約してください。
一般的でない技術用語・製品名・攻撃名には1行解説を付けてください。

タイトル: {item['title']}
内容: {item['summary'][:500]}

フォーマット:
【要約】[1行の要約]
【用語解説】[必要な場合のみ記載]
"""
                response = model.generate_content(prompt)
                
                summaries[category].append({
                    "title": item["title"],
                    "link": item["link"],
                    "summary": response.text,
                })
            except Exception as e:
                print(f"Error summarizing: {e}")
    
    return summaries

def create_email_body(summaries):
    """メール本文をHTML形式で生成"""
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'MS P Gothic', 'Hiragino Kaku Gothic Pro', sans-serif; }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 8px; }}
            .article {{ margin-bottom: 20px; padding: 12px; background-color: #f8f9fa; border-left: 4px solid #3498db; }}
            .article-title {{ font-weight: bold; color: #2c3e50; margin-bottom: 8px; }}
            .article-link {{ color: #3498db; text-decoration: none; font-size: 12px; }}
            .summary {{ color: #555; font-size: 14px; line-height: 1.6; }}
        </style>
    </head>
    <body>
    <h1>📰 今朝のニュースまとめ</h1>
    <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
    """
    
    for category, items in summaries.items():
        if items:
            html += f"<h2>📌 {category}</h2>"
            for item in items:
                html += f"""
                <div class="article">
                    <div class="article-title">{item['title']}</div>
                    <div class="summary">{item['summary']}</div>
                    <a href="{item['link']}" class="article-link">元記事を読む →</a>
                </div>
                """
    
    html += """
    </body>
    </html>
    """
    
    return html

def send_email(html_body):
    """Gmailでメールを送信"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📰 ニュースまとめ {datetime.now().strftime('%Y年%m月%d日')}"
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = GMAIL_ADDRESS
        
        # HTML部分
        html_part = MIMEText(html_body, "html", "utf-8")
        msg.attach(html_part)
        
        # Gmail送信
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        print("✅ メール送信完了")
    except Exception as e:
        print(f"❌ メール送信エラー: {e}")

def main():
    print("🔄 ニュース収集開始...")
    
    # ステップ1: RSSから記事を取得
    articles = fetch_articles()
    print(f"✅ {sum(len(v) for v in articles.values())} 件の記事を取得")
    
    # ステップ2: Gemini APIで要約
    print("🤖 AIで要約中...")
    summaries = summarize_with_gemini(articles)
    
    # ステップ3: メール本文を作成
    email_body = create_email_body(summaries)
    
    # ステップ4: メール送信
    print("📧 メール送信中...")
    send_email(email_body)
    
    print("✅ 処理完了！")

if __name__ == "__main__":
    main()
