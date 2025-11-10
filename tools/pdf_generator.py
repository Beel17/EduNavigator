"""PDF generator for proposals."""
import logging
from pathlib import Path
from weasyprint import HTML, CSS
from markdown import markdown
from config import settings

logger = logging.getLogger(__name__)


def generate_proposal_pdf(markdown_content: str, output_path: str) -> str:
    """
    Generate PDF from markdown content.
    
    Args:
        markdown_content: Markdown text
        output_path: Output file path
    
    Returns:
        Path to generated PDF
    """
    try:
        # Convert markdown to HTML
        html_content = markdown(markdown_content, extensions=['extra', 'nl2br'])
        
        # Wrap in HTML document with styling
        html_doc = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    margin-top: 30px;
                }}
                p {{
                    margin: 15px 0;
                }}
                ul, ol {{
                    margin: 15px 0;
                    padding-left: 30px;
                }}
                code {{
                    background-color: #f4f4f4;
                    padding: 2px 5px;
                    border-radius: 3px;
                }}
                pre {{
                    background-color: #f4f4f4;
                    padding: 15px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate PDF
        HTML(string=html_doc).write_pdf(output_path)
        
        logger.info(f"Generated PDF: {output_path}")
        return str(output_path)
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise

