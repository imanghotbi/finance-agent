import json
import os

from src.core.logger import logger
## TODO delete later
async def mock_data():
    """
    MOCK implementation of run_orchestrator.
    Loads data from symbol_info.json instead of running the pipeline.
    """
    
    # Path to the mock file
    mock_file_path = "symbol_info.json"
    
    if not os.path.exists(mock_file_path):
        logger.error(f"❌ Mock file '{mock_file_path}' not found!")
        return {}

    try:
        with open(mock_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        logger.error(f'error happen: {e}')