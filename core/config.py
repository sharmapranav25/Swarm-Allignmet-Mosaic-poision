"""Defaults for the working ten-worker ticketing experiment."""
from dataclasses import asdict, dataclass


@dataclass
class RunConfig:
    model: str = "qwen3.5-397b"
    seed: int = 1
    days: int = 2
    n_naive: int = 3
    n_restrained: int = 4
    n_rogue: int = 3
    tickets_per_day: int = 100
    use_briefs: bool = True
    world_version: str = "ticketing-mosaic-v1"
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
