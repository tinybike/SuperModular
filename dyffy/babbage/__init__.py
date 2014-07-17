import sys
import cdecimal
sys.modules["decimal"] = cdecimal
from .babbage import Babbage