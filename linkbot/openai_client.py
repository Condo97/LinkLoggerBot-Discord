from openai import AsyncOpenAI
import json
from config import OPENROUTER_API_KEY, DEEPSEEK_MODEL

class ChatClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    
    async def classify(self, text: str, context: list) -> dict:
        prompt = f"""
        Classify the following message and return JSON format:
        Available commands: check_stock, price_history, compare_prices, 
                          add_calendar_event, request_summary, other
        
        Context:
        {''.join(context)}
        
        Message: {text}
        """
        
        response = await self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "You are a classification bot that outputs JSON"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    async def completion(self, text: str, context: list) -> str:
        messages = [
            {"role": "system", "content": "You are a helpful shopping assistant. Use the following context:"},
            {"role": "system", "content": "\n".join(context)},
            {"role": "user", "content": text}
        ]
        
        response = await self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content