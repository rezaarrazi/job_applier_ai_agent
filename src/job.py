# from dataclasses import dataclass
from pydantic import BaseModel
from src.logging import logger
from typing import List, Optional, Tuple, Dict

# @dataclass
class Job(BaseModel):
    role: str = ""
    company: str = ""
    location: Optional[str] = None
    salary: Optional[str] = None
    link: str = ""
    description: str = ""
    responsibilities: str = ""
    apply_method: Optional[str] = None
    summarize_job_description: str = ""
    recruiter_link: Optional[str] = None
    fit_score: float
    # resume_path: str = ""
    # cover_letter_path: str = ""

    def formatted_job_information(self):
        """
        Formats the job information as a markdown string.
        """
        logger.debug(f"Formatting job information for job: {self.role} at {self.company}")
        job_information = f"""
        # Job Description
        ## Job Information 
        - Position: {self.role}
        - At: {self.company}
        - Location: {self.location}
        - Recruiter Profile: {self.recruiter_link or 'Not available'}
        
        ## Description
        {self.description or 'No description provided.'}
        
        ## Responsibilities
        {self.responsibilities or 'No description provided.'}
        """

        formatted_information = job_information.strip()
        logger.debug(f"Formatted job information: {formatted_information}")
        return formatted_information
    
class ExperienceLevel(BaseModel):
    internship: bool
    entry: bool
    associate: bool
    mid_senior_level: bool
    director: bool
    executive: bool

class JobTypes(BaseModel):
    full_time: bool
    contract: bool
    part_time: bool
    temporary: bool
    internship: bool
    other: bool
    volunteer: bool

class DateFilter(BaseModel):
    all_time: bool
    month: bool
    week: bool
    hours_24: bool

class JobPreferences(BaseModel):
    remote: bool
    hybrid: bool
    onsite: bool
    experience_level: ExperienceLevel
    job_types: JobTypes
    date: DateFilter
    positions: List[str]
    locations: List[str]
    apply_once_at_company: bool
    distance: int
    company_blacklist: List[str]
    title_blacklist: List[str]
    location_blacklist: List[str]
    
    def to_plain_text(self) -> str:
        return (
            f"Remote: {self.remote}\n"
            f"Hybrid: {self.hybrid}\n"
            f"Onsite: {self.onsite}\n"
            f"Experience Level:\n"
            f"  Internship: {self.experience_level.internship}\n"
            f"  Entry: {self.experience_level.entry}\n"
            f"  Associate: {self.experience_level.associate}\n"
            f"  Mid-Senior Level: {self.experience_level.mid_senior_level}\n"
            f"  Director: {self.experience_level.director}\n"
            f"  Executive: {self.experience_level.executive}\n"
            f"Job Types:\n"
            f"  Full Time: {self.job_types.full_time}\n"
            f"  Contract: {self.job_types.contract}\n"
            f"  Part Time: {self.job_types.part_time}\n"
            f"  Temporary: {self.job_types.temporary}\n"
            f"  Internship: {self.job_types.internship}\n"
            f"  Other: {self.job_types.other}\n"
            f"  Volunteer: {self.job_types.volunteer}\n"
            f"Date Filter:\n"
            f"  All Time: {self.date.all_time}\n"
            f"  Month: {self.date.month}\n"
            f"  Week: {self.date.week}\n"
            f"  24 Hours: {self.date.hours_24}\n"
            f"Positions: {', '.join(self.positions)}\n"
            f"Locations: {', '.join(self.locations)}\n"
            f"Apply Once at Company: {self.apply_once_at_company}\n"
            f"Distance: {self.distance}\n"
            f"Company Blacklist: {', '.join(self.company_blacklist)}\n"
            f"Title Blacklist: {', '.join(self.title_blacklist)}\n"
            f"Location Blacklist: {', '.join(self.location_blacklist)}"
        )