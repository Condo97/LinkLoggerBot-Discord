import re

class BacktickScrubber:
    @staticmethod
    def scrub_json_backticks(s):
        # Split the string into parts using triple backticks
        parts = s.split('```')
        
        # If there are fewer than 2 triple backticks, return the original string stripped
        if len(parts) < 3:
            return s.strip()
        
        # Extract the content between the first and last triple backticks
        content = '```'.join(parts[1:-1])  # Handles edge cases with multiple triple backticks
        
        # Remove any leading language specifier (e.g., "json") followed by optional whitespace
        content = re.sub(r'^\s*\w+\s*\n?', '', content, count=1, flags=re.IGNORECASE)
        
        return content.strip()
    # def scrub_json_backticks(s):
    #         # Pattern for cases where content starts after a newline following opening ```
    #         pattern_with_newline = re.compile(r'^\s*```[^\n]*\n(.*?)```\s*$', re.DOTALL)
    #         match = pattern_with_newline.match(s)
    #         if match:
    #             return match.group(1).strip()
            
    #         # Pattern for cases where content is on the same line as opening ```
    #         pattern_same_line = re.compile(r'^\s*```[^\n]*([^\n]+)```\s*$')
    #         match = pattern_same_line.match(s)
    #         if match:
    #             return match.group(1).strip()
            
    #         # If neither pattern matches, return the original string stripped
    #         return s.strip()