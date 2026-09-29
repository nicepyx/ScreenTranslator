"""UI scene names map to existing pipeline tuning knobs."""
from ..constants import USAGE_MODES

# Meetings share the tested low-latency streaming parameters of courses.
SCENE_PRESETS = {**USAGE_MODES, "meeting": {**USAGE_MODES["course"], "label": "会议 · 低延迟"}}
