import aiohttp
from bs4 import BeautifulSoup

class WebScraper:
    @staticmethod
    async def get_web_content(url: str) -> str:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    # Clean up content
                    for script in soup(["script", "style"]):
                        script.decompose()
                    return soup.get_text(separator=' ', strip=True)[:5000]  # Limit to 5k chars
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return ""