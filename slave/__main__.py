import logging
import sys
import os

# Add the parent directory to the path to find shared config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from still_capture import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Shutting down slave service...")
    except Exception as e:
        logging.error(f"Unexpected error in slave service: {e}")
