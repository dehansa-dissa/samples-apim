import os
from dotenv import load_dotenv

load_dotenv()

RETRY_COUNT = int(os.getenv("RETRY_COUNT", 1))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", 1))  # in seconds
TIMEOUT = int(os.getenv("TIMEOUT", 60))  # in seconds
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 15))
PROCESS_RESOURCE_DELAY = int(os.getenv("PROCESS_RESOURCE_DELAY", 1))
