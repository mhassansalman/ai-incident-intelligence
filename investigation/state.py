""" State module for the investigation LangGraph.

Reuses canonical IncidentState from common/incident_models.py and
map_v0_json_to_incident_state for V0-to-V1 mapping. root_cause starts
as None; inconclusive is a legitimate terminal result after investigation.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Union

from common.incident_models import IncidentState, map_v0_json_to_incident_state