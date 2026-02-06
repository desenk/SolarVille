# Branch: unified-main
# File: discovery.py

import logging
from typing import List
from core.device_types import PiDevice

class PeerDiscovery:
    def __init__(self):
        self.known_peers: List[PiDevice] = []