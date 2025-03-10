from dotenv import load_dotenv
import logging
from pathlib import Path
import sys
from os.path import dirname, abspath
from backend.utils import write_md_to_word

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging with both file and console handlers for comprehensive logging coverage
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # File handler for general application logs - persists logs for future reference
        logging.FileHandler('logs/app.log'),
        # Stream handler for console output - provides real-time monitoring
        logging.StreamHandler()
    ]
)

# Suppress verbose fontTools logging to keep logs focused on application-specific messages
logging.getLogger('fontTools').setLevel(logging.WARNING)
logging.getLogger('fontTools.subset').setLevel(logging.WARNING)
logging.getLogger('fontTools.ttLib').setLevel(logging.WARNING)

# Create logger instance for this module
logger = logging.getLogger(__name__)

# Add the project root to Python path to ensure proper module imports
project_root = dirname(abspath(__file__))
sys.path.append(project_root)

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gpt_researcher import GPTResearcher
from backend.server.server import app

# Initialize FastAPI application
app = FastAPI()

# Configure CORS middleware to allow cross-origin requests
# This is essential for web clients to interact with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,  # Allows cookies in cross-origin requests
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/api/research")
async def research(request: dict):
    """Endpoint to conduct research based on the provided query.
    
    Args:
        request (dict): Contains the research query and optional parameters
            - query (str): The research topic or question
    
    Returns:
        dict: Contains either:
            - result (str): The research report if successful
            - error (str): Error message if the research failed
    """
    try:
        # Initialize researcher with the query
        researcher = GPTResearcher(query=request["query"])
        # Conduct the research asynchronously
        await researcher.conduct_research()
        # Generate and return the research report
        result = await researcher.write_report()
        return {"result": result}
    except Exception as e:
        # Return any errors that occurred during the research process
        return {"error": str(e)}

        # Generate DOCX file
        sanitized_filename = f"task_{int(time.time())}_{request.query[:50]}"
        docx_path = await write_md_to_word(report, sanitized_filename)

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
