# link_categorizer.py
class LinkCategorizer:
    CATEGORIES = [
        "Product/Service",
        "News/Media",
        "Academic/Research",
        "Technology/Tutorial",
        "Entertainment",
        "Educational/Guide",
        "Business/Finance",
        "Health/Medical",
        "Government/Legal",
        "Social Media/Forum",
        "Tool/Utility",
        "Travel/Tourism",
        "Science/Environment",
        "Opinion/Blog",
        "E-learning/Course",
        "Software/App",
        "PDF/Document",
        "Career/Job Listing",
        "Creative Arts",
        "Nonprofit/Activism"
    ]

    @staticmethod
    def format_categorized(links_by_category: dict) -> str:
        """Format categorized links into a readable table"""
        if not links_by_category:
            return "No links found in database"

        output = "**Categorized Links**\n\n"
        print(links_by_category)
        for category, links in links_by_category.items():
            if category and links:
                output += f"**{category.upper()}** ({len(links)} links):\n"
                for link in links:
                    output += f"- [{link['link_id']}] {link['web_url']}\n"
                    output += f"  Summary: {link['summary'][:150]}...\n"
                output += "\n"
        return output[:2000]  # Respect Discord message limits