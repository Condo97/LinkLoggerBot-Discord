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
        CLASSIFICATION PROTOCOL:
        Analyze the message and respond with JSON containing:
        {{
            "command": "check_stock|price_history|compare_prices|add_calendar_event|request_summary|other",
            "link_query_days_ago_limit": null|int,
            "link_query_count_limit": null|int,
            "needs_scraping": [link_ids]
        }}

        EXAMPLE RESPONSE:
        {{
            "command": "check_stock",
            "link_query_days_ago_limit": 7,
            "needs_scraping": [42, 15]
        }}

        CONTEXT:
        {''.join(context)}

        MESSAGE TO CLASSIFY:
        {text}
        """

        try:
            response = await self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a classification bot that ONLY outputs valid JSON"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content
            
            # Clean response text
            cleaned_response = response_text.replace('```json', '').replace('```', '').strip()
            print(f"Cleaned classification response: {cleaned_response}")
            
            classification = json.loads(cleaned_response)
            
            # Validate required keys
            required_keys = ['command', 'needs_scraping']
            for key in required_keys:
                if key not in classification:
                    raise KeyError(f"Missing required key: {key}")
                    
            # Ensure list types
            classification['needs_scraping'] = classification.get('needs_scraping', []) or []
            classification['command'] = classification.get('command', 'other').lower()
            
            return classification
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}\nResponse content: {cleaned_response}")
            return {
                "command": "other",
                "link_query_days_ago_limit": None,
                "link_query_count_limit": None,
                "needs_scraping": []
            }
        except KeyError as e:
            print(f"Missing key in classification: {e}")
            return {
                "command": "other",
                "link_query_days_ago_limit": None,
                "link_query_count_limit": None,
                "needs_scraping": []
            }
        except Exception as e:
            print(f"Classification error: {str(e)}")
            return {
                "command": "other",
                "link_query_days_ago_limit": None,
                "link_query_count_limit": None,
                "needs_scraping": []
            }
    
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