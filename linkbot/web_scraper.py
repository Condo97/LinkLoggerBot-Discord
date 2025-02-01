# web_scraper.py
import aiohttp
from bs4 import BeautifulSoup

class WebScraper:
    @staticmethod
    async def get_web_content(url: str) -> str:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return ""
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    for element in soup(['script', 'style', 'nav', 'footer']):
                        element.decompose()
                        
                    text = soup.get_text(separator='\n', strip=True)
                    return text[:10000]  # Limit to 10k characters
        except Exception as e:
            print(f"Scraping error: {str(e)}")
            return ""