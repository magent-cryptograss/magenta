#!/usr/bin/env python3
"""
Live conversation watcher for Claude Code JSONL logs.

Monitors JSONL files for new lines and imports them in real-time.
"""

import os
import sys
import time
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add magenta directory to path and change to it
MAGENTA_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(MAGENTA_DIR))
os.chdir(MAGENTA_DIR)

# Set up logging
LOG_DIR = MAGENTA_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "watcher.log"

# Create logger
logger = logging.getLogger("watcher")
logger.setLevel(logging.INFO)

# Console handler (for tmux/screen viewing)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(console_formatter)

# File handler with rotation (max 10MB, keep 5 old files)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Django setup
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'memory_viewer.settings')
django.setup()

from conversations.models import Era, Message
from importers_and_parsers.claude_code_v2 import import_line_from_claude_code_v2
from watcher.heap_assignment import assign_heap_to_message


class ConversationWatcher(FileSystemEventHandler):
    """Watch JSONL files and import new messages."""

    def __init__(self, watch_dir, era):
        """
        Initialize watcher.

        Args:
            watch_dir: Directory to watch (e.g., /home/magent/.claude/project-logs/)
            era: Era instance to import into
        """
        self.watch_dir = Path(watch_dir)
        self.era = era
        self.file_positions = {}  # Track last position read for each file
        self.current_heap = None  # Track current heap for edge cases

        logger.info(f"Watcher initialized for {watch_dir}")
        logger.info(f"Importing into era: {era.name} ({era.id})")

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        filepath = Path(event.src_path)

        # Only watch .jsonl files
        if filepath.suffix != '.jsonl':
            return

        logger.debug(f"File modified: {filepath.name}")
        self.process_new_lines(filepath)

    def process_new_lines(self, filepath):
        """Process new lines added to file since last read."""
        # Get last known position
        last_position = self.file_positions.get(str(filepath), 0)

        try:
            with open(filepath, 'r') as f:
                # Seek to last position
                f.seek(last_position)

                # Read new lines
                line_count = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    line_count += 1
                    try:
                        self.import_line(line, filepath.name)
                    except KeyError as e:
                        # Unknown format - save as raw data for later analysis
                        self.save_unparseable_line(line, filepath.name, str(e))
                    except Exception as e:
                        logger.error(f"Error importing line from {filepath.name}: {e}", exc_info=True)
                        # Also save this as unparseable
                        self.save_unparseable_line(line, filepath.name, str(e))

                # Update position
                self.file_positions[str(filepath)] = f.tell()

                if line_count > 0:
                    logger.info(f"Processed {line_count} new lines from {filepath.name}")

        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}", exc_info=True)

    def save_unparseable_line(self, line, filename, error_msg):
        """
        Save unparseable content for later analysis.

        Args:
            line: JSONL line that couldn't be parsed
            filename: Source filename
            error_msg: Error message
        """
        from conversations.models import RawImportedContent
        from django.contrib.contenttypes.models import ContentType
        import json

        try:
            # Try to get UUID if present
            data = json.loads(line)
            uuid_str = data.get('uuid', None)

            # Save as RawImportedContent without linking to a specific object
            raw = RawImportedContent.objects.create(
                raw_data=data,
                content_type=None,
                object_id=None
            )
            logger.warning(f"Unparseable line saved as RawImportedContent {raw.id} from {filename} (error: {error_msg})")
        except Exception as e:
            logger.error(f"Failed to save unparseable line from {filename}: {e}")

    def import_line(self, line, filename):
        """
        Import a single JSONL line.

        Args:
            line: JSONL line string
            filename: Source filename
        """
        from constant_sorrow.constants import EVENT_TYPE_WE_DO_NOT_HANDLE_YET

        # Parse and create message using existing logic
        event, created = import_line_from_claude_code_v2(line, self.era, filename)

        # Check if this is an event type we don't handle yet
        if event is EVENT_TYPE_WE_DO_NOT_HANDLE_YET:
            logger.debug(f"Skipping unhandled event type from {filename}")
            return

        if not created:
            logger.debug(f"Already imported: {event.id}")
            return

        # If it's a Message (not CompactingAction or Summary), assign heap
        if isinstance(event, Message):
            heap = assign_heap_to_message(event, self.era, self.current_heap)
            self.current_heap = heap  # Update current heap tracker
            logger.debug(f"Imported message {str(event.id)[:8]} → heap {str(heap.id)[:8]}")
        else:
            logger.info(f"Imported {event.__class__.__name__} {str(event.id)[:8]}")

    def scan_existing_files(self):
        """Scan existing files to establish baseline positions."""
        logger.info("Scanning existing files...")

        file_count = 0
        for filepath in self.watch_dir.glob('*.jsonl'):
            # Just seek to end - we only want NEW lines from this point forward
            with open(filepath, 'r') as f:
                f.seek(0, 2)  # Seek to end
                self.file_positions[str(filepath)] = f.tell()

            logger.debug(f"Tracking {filepath.name} from position {self.file_positions[str(filepath)]}")
            file_count += 1

        logger.info(f"Tracking {file_count} JSONL files")


def main():
    """Run the watcher service."""
    # Configuration
    WATCH_DIR = os.getenv('CLAUDE_LOGS_DIR', '/home/magent/.claude/project-logs')
    ERA_NAME = os.getenv('WATCHER_ERA_NAME', 'Current Working Era (Era N)')

    # Support for multi-user directories
    # If WATCH_DIR contains multiple colon-separated paths, watch all of them
    watch_dirs = [Path(d.strip()) for d in WATCH_DIR.split(':') if d.strip()]

    # Get or create era
    era, created = Era.objects.get_or_create(name=ERA_NAME)
    if created:
        logger.info(f"Created new era: {ERA_NAME}")
    else:
        logger.info(f"Using existing era: {ERA_NAME}")

    # Create observer
    observer = Observer()

    # Set up watchers for each directory
    for watch_dir in watch_dirs:
        if not watch_dir.exists():
            logger.warning(f"Watch directory does not exist: {watch_dir}")
            continue

        logger.info(f"Setting up watcher for: {watch_dir}")
        watcher = ConversationWatcher(watch_dir, era)

        # Scan existing files to establish baseline
        watcher.scan_existing_files()

        # Schedule observer for this directory
        observer.schedule(watcher, str(watch_dir), recursive=False)

    # Start observing all directories
    observer.start()

    logger.info(f"Watching {len(watch_dirs)} directories for new messages...")
    logger.info("Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Stopping watcher...")

    observer.join()


if __name__ == '__main__':
    main()
