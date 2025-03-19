# openai_client.py (updated with error handling)
from openai import AsyncOpenAI
import json
from typing import Dict, Any
from linkbot.config import OPENROUTER_API_KEY, DEEPSEEK_MODEL
from linkbot.backtick_scrubber import BacktickScrubber
from linkbot.link_categorizer import LinkCategorizer

class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )

    async def classify_command(self, query: str) -> Dict[str, Any]:
        """Classify user command with robust error handling"""
        default_response = {"command_type": "NONE"}
        # tools = [{
        #     "type": "function",
        #     "function:": {
        #         "name": "classify_user_intent",
        #         "description": "Determine how to process user request",
        #         "parameters": {
        #             "type": "object",
        #             "properties": {
        #                 "command_type": {
        #                     "type": "string",
        #                     "enum": ["SEARCH_AND_SCRAPE", "SEARCH", "NONE"],
        #                     "description": "Type of command to execute. Search functionality searches a database of links using the user's query from optional timeframe_days ago and/or/neither optional returning max_results. Scrape adds additional functionality to scrape the websites for updated data but adds delay and token cost so use if necessary."
        #                 },
        #                 "timeframe_days": {
        #                     "type": "integer",
        #                     "description": "Time window to search in days null to only limit by max_results or both null to include all results"
        #                 },
        #                 "max_results": {
        #                     "type": "integer",
        #                     "description": "Maximum number of results to return if needed null to only limit by timeframe_days or both null to include all results"
        #                 }
        #             },
        #             "required": ["command_type"]
        #         }
        #     }
        # }]

        system_prompt = """
Determine how to process the user request.

CommandTypes
{
    SEARCH_AND_SCRAPE,
    SEARCH,
    NONE
}

JSON OUTPUT:
{
    "command_type": CommandTypes as string,
    "timeframe_days": integer,
    "max_results": integer
}

REQUIRED: command_type
OPTIONAL: timeframe_days, max_results

command_type is the type of command to execute. Search functionality searches a database of links using the user's query from optional timeframe_days ago and/or/neither optional returning max_results. Scrape adds additional functionality to scrape the websites for updated data but adds delay and token cost so use if necessary. None does no operation. They all are to form another chat input for another call to DeepSeek so none will just do the operation with only the prompt while the others will use the prompt with their collected data.

timeframe_days is the time window to search in days null to only limit by max_results or both null to include all results

max_results is the maximum number of results to return if needed null to only limit by timeframe_days or both null to include all results
        """

        try:
            response = await self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                response_format={
                    'type': 'json_object'
                }
                # tools=tools,
                # tool_choice=[{"name": "classify_user_intent"}]
            )
        except Exception as e:
            print(f"API request failed: {str(e)}")
            return default_response

        try:
            if not response or not response.choices:
                return default_response
            
            message = BacktickScrubber.scrub_json_backticks(response.choices[0].message.content)
            if not message:
                return default_response

            args = json.loads(message)
            return {
                "command_type": args.get("command_type", "NONE"),
                "timeframe_days": args.get("timeframe_days"),
                "max_results": args.get("max_results")
            }
        except json.JSONDecodeError:
            print("Failed to parse function arguments")
            return default_response
        except (KeyError, IndexError, AttributeError) as e:
            print(f"Invalid response structure: {str(e)}")
            return default_response

    async def generate_summary(self, content: str) -> tuple[str, str]:
        """Generate summary and category for content"""
        system_msg = f"""Analyze this content and provide:
1. Concise summary (max 200 words)
2. Category from: {", ".join(LinkCategorizer.CATEGORIES)}

Respond ONLY with JSON format: {{"summary": "...", "category": "..."}}"""

        try:
            response = await self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": content[:10000]}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            result = json.loads(response.choices[0].message.content)
            return (
                result.get("summary", "No summary available"),
                result.get("category", "other").lower()
            )
        except Exception as e:
            print(f"Summary generation error: {str(e)}")
            return ("No summary available", "other")

    async def filter_relevant_links(self, query: str, links: list[str]) -> list[int]:
        # tools = [{
        #     "type": "function",
        #     "function:": {
        #         "name": "return_relevant_links",
        #         "description": "Return IDs of relevant links based on query",
        #         "parameters": {
        #             "type": "object",
        #             "properties": {
        #                 "link_ids": {
        #                     "type": "array",
        #                     "items": {"type": "integer"},
        #                     "description": "Relevant link IDs"
        #                 }
        #             },
        #             "required": ["link_ids"]
        #         }
        #     }
        # }]
        system_prompt = """
Return IDs of relevant links based on query.

JSON OUTPUT:
{
    "link_ids": string[]
}

REQUIRED: link_ids

link_ids are the relevant link IDs.
        """

        response = await self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}\nLinks:\n{chr(10).join(links)}"}
            ]
        )

        print("Response\n", response)
        
        message = BacktickScrubber.scrub_json_backticks(response.choices[0].message.content)

        print("Message:\n", message)
        if message:
            args = json.loads(message)
            return args.get("link_ids", [])
        return []
        

    async def generate_response(self, query: str, context: list[str]) -> str:
        print(context)

        messages = [{
            "role": "system",
            "content": "You are a helpful assistant. Use provided context where relevant. Always cite links when given, make sure they are in discord format as hyperlinks."
        }]
        
        if context:
            messages.append({
                "role": "system",
                "content": "CONTEXT:\n" + "\n\n".join(context)
            })
            
        messages.append({"role": "user", "content": query})
        
        response = await self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.6,
            max_tokens=3500
        )
        return response.choices[0].message.content