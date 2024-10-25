from pydantic import BaseModel, Field
from typing import List

class Feedback(BaseModel):
    areas_well_done: List[str] = Field(default_factory=list, description="Summary of areas where the student performed well.")
    areas_to_improve: List[str] = Field(default_factory=list, description="Summary of areas where the student can improve.")
