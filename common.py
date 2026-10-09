"""Shared config: reads Neo4j credentials from password.txt in the project root."""
import os
import sys
import unicodedata
from pathlib import Path

from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent
PASSWORD_FILE = ROOT / "password.txt"
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")


def load_auth():
    """password.txt formats:
         one line  -> password (user defaults to 'neo4j')
         two lines -> username, then password
    """
    if not PASSWORD_FILE.exists():
        sys.exit(f"Missing {PASSWORD_FILE.name} in project root - see README.md")
    lines = [l.strip() for l in PASSWORD_FILE.read_text().splitlines() if l.strip()]
    if not lines:
        sys.exit(f"{PASSWORD_FILE.name} is empty")
    return ("neo4j", lines[0]) if len(lines) == 1 else (lines[0], lines[1])


def get_driver():
    # notifications off: otherwise every query on a not-yet-existing label/type prints a warning
    driver = GraphDatabase.driver(NEO4J_URI, auth=load_auth(), notifications_min_severity="OFF")
    driver.verify_connectivity()
    return driver


def to_url(src):
    """Turn a local file path into a file:// URL; leave http(s) URLs as-is."""
    if src.startswith(("http://", "https://", "file://")):
        return src
    # NFC: macOS file names can be NFD, which would make the same path produce two different URLs
    return Path(unicodedata.normalize("NFC", str(Path(src).resolve()))).as_uri()
