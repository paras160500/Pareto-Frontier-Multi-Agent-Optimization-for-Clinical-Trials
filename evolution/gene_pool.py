"""
    SOP Gene Pool.
    It stores every GuildSOP tried so far along with its evaluation percentage.
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

from typing import List, Dict, Any, Optional

from guild.sop import GuildSOP
from evalution.gauntlet import EvaluationResult


# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Class Generation Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

class SOPGenePool:
    """A class to store and manage a collection of GuildSOPs and their evaluations."""

    def __init__(self):
        self.pool: List[Dict[str, Any]] = []
        self.version_counter = 0

    def add(self, sop: GuildSOP, eval_result: EvaluationResult, parent_version: Optional[int] = None):
        self.version_counter += 1
        entry = {
            "version": self.version_counter,
            "sop": sop,
            "evaluation": eval_result,
            "parent": parent_version,
        }
        self.pool.append(entry)
        print(f"Added SOP v{self.version_counter} to the gene pool.")

    def get_latest_entry(self) -> Optional[Dict[str, Any]]:
        return self.pool[-1] if self.pool else None