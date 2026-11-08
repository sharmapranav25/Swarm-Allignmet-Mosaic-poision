"""Defaults for the website-maintenance world. Deliberately separate from
core/config.py's RunConfig (ticketing-specific fields) per BUILD_CONTRACT.md:
new worlds get their own config rather than overloading ticketing's."""
from dataclasses import asdict, dataclass


@dataclass
class WebsiteConfig:
    model: str = "qwen3.5-397b"
    seed: int = 1
    days: int = 2
    total_incidents: int = 10000
    batch_size: int = 10
    use_briefs: bool = True
    world_version: str = "website-breach-v1"
    max_tool_calls_per_turn: int = 10
    wall_clock_limit_s: float = 3600.0
    api_timeout_s: float = 180.0
    max_output_tokens: int = 8000
    history_days_kept: int = 6
    llm_retries: int = 3
    out_dir: str = "runs"
    run_id: str = ""

    def to_dict(self):
        return asdict(self)
