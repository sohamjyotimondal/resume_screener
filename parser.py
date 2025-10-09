"""
Comprehensive Resume Parser using Instructor Library
This module provides structured extraction of resume data using LLMs and Pydantic models.
"""

import instructor
from pydantic import BaseModel, Field, EmailStr, HttpUrl, validator
from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime, date
from enum import Enum
import re
import json
from groq import Groq
import PyPDF2
import docx
import io
from pathlib import Path
import logging
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enums for standardized data
class EducationLevel(str, Enum):
    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"
    CERTIFICATE = "certificate"
    DIPLOMA = "diploma"
    PROFESSIONAL = "professional"

class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    VP = "vp"
    EXECUTIVE = "executive"

class SkillProficiency(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    VOLUNTEER = "volunteer"

# Detailed Pydantic Models for Resume Components

class ContactInfo(BaseModel):
    """Contact information from the resume."""
    email: Optional[EmailStr] = Field(
        None,
        description="Primary email address of the candidate"
    )
    phone: Optional[str] = Field(
        None,
        description="Primary phone number in any format"
    )
    secondary_phone: Optional[str] = Field(
        None,
        description="Secondary or mobile phone number if different from primary"
    )
    address: Optional[str] = Field(
        None,
        description="Full address including street, city, state, and postal code"
    )
    city: Optional[str] = Field(
        None,
        description="City of residence"
    )
    state: Optional[str] = Field(
        None,
        description="State or province of residence"
    )
    country: Optional[str] = Field(
        None,
        description="Country of residence"
    )
    postal_code: Optional[str] = Field(
        None,
        description="ZIP or postal code"
    )

    @validator('phone', 'secondary_phone')
    def validate_phone(cls, v):
        if v and len(re.sub(r'[^0-9]', '', v)) < 10:
            raise ValueError('Phone number must contain at least 10 digits')
        return v

class SocialLinks(BaseModel):
    """Social media and professional links."""
    linkedin: Optional[HttpUrl] = Field(
        None,
        description="LinkedIn profile URL"
    )
    github: Optional[HttpUrl] = Field(
        None,
        description="GitHub profile URL"
    )
    portfolio: Optional[HttpUrl] = Field(
        None,
        description="Personal portfolio or website URL"
    )
    twitter: Optional[HttpUrl] = Field(
        None,
        description="Twitter profile URL"
    )
    other_links: Optional[List[HttpUrl]] = Field(
        default_factory=list,
        description="Any other professional or relevant links"
    )

class Skill(BaseModel):
    """Individual skill with proficiency level."""
    name: str = Field(
        ...,
        description="Name of the skill or technology"
    )
    category: Optional[str] = Field(
        None,
        description="Category of skill (e.g., programming, database, framework)"
    )
    proficiency: Optional[SkillProficiency] = Field(
        None,
        description="Proficiency level of the skill"
    )
    years_of_experience: Optional[float] = Field(
        None,
        ge=0,
        description="Number of years of experience with this skill"
    )
    is_primary: Optional[bool] = Field(
        False,
        description="Whether this is a primary/core skill"
    )

class Education(BaseModel):
    """Educational qualification details."""
    institution: str = Field(
        ...,
        description="Name of the educational institution"
    )
    degree: str = Field(
        ...,
        description="Degree or qualification obtained"
    )
    field_of_study: Optional[str] = Field(
        None,
        description="Major, specialization, or field of study"
    )
    level: Optional[EducationLevel] = Field(
        None,
        description="Level of education"
    )
    start_date: Optional[date] = Field(
        None,
        description="Start date of the education"
    )
    end_date: Optional[date] = Field(
        None,
        description="End date or expected graduation date"
    )
    gpa: Optional[float] = Field(
        None,
        ge=0.0,
        le=4.0,
        description="GPA on a 4.0 scale"
    )
    grade: Optional[str] = Field(
        None,
        description="Grade or class (e.g., First Class, Distinction)"
    )
    location: Optional[str] = Field(
        None,
        description="Location of the institution"
    )
    honors: Optional[List[str]] = Field(
        default_factory=list,
        description="Academic honors, awards, or recognitions"
    )
    relevant_coursework: Optional[List[str]] = Field(
        default_factory=list,
        description="Relevant courses or subjects studied"
    )
    thesis_title: Optional[str] = Field(
        None,
        description="Title of thesis or major project if applicable"
    )
    is_current: bool = Field(
        False,
        description="Whether this education is currently ongoing"
    )

class WorkExperience(BaseModel):
    """Work experience details."""
    company: str = Field(
        ...,
        description="Name of the company or organization"
    )
    position: str = Field(
        ...,
        description="Job title or position held"
    )
    department: Optional[str] = Field(
        None,
        description="Department or division within the company"
    )
    employment_type: Optional[EmploymentType] = Field(
        None,
        description="Type of employment"
    )
    start_date: Optional[date] = Field(
        None,
        description="Start date of employment"
    )
    end_date: Optional[date] = Field(
        None,
        description="End date of employment (None if current)"
    )
    location: Optional[str] = Field(
        None,
        description="Location of the job (city, state/country)"
    )
    description: Optional[str] = Field(
        None,
        description="Overall job description or summary"
    )
    responsibilities: Optional[List[str]] = Field(
        default_factory=list,
        description="List of key responsibilities and duties"
    )
    achievements: Optional[List[str]] = Field(
        default_factory=list,
        description="List of key achievements and accomplishments"
    )
    technologies_used: Optional[List[str]] = Field(
        default_factory=list,
        description="Technologies, tools, or skills used in this role"
    )
    team_size: Optional[int] = Field(
        None,
        ge=1,
        description="Size of the team managed or worked with"
    )
    is_current: bool = Field(
        False,
        description="Whether this is the current position"
    )

class Project(BaseModel):
    """Project details from resume."""
    name: str = Field(
        ...,
        description="Name or title of the project"
    )
    description: str = Field(
        ...,
        description="Detailed description of the project"
    )
    technologies: Optional[List[str]] = Field(
        default_factory=list,
        description="Technologies, frameworks, or tools used"
    )
    role: Optional[str] = Field(
        None,
        description="Role or responsibility in the project"
    )
    start_date: Optional[date] = Field(
        None,
        description="Project start date"
    )
    end_date: Optional[date] = Field(
        None,
        description="Project end date"
    )
    url: Optional[HttpUrl] = Field(
        None,
        description="URL to project demo, repository, or documentation"
    )
    achievements: Optional[List[str]] = Field(
        default_factory=list,
        description="Key achievements or outcomes of the project"
    )
    is_professional: bool = Field(
        False,
        description="Whether this was a professional/work project"
    )

class Certification(BaseModel):
    """Professional certifications and licenses."""
    name: str = Field(
        ...,
        description="Name of the certification"
    )
    issuing_organization: str = Field(
        ...,
        description="Organization that issued the certification"
    )
    issue_date: Optional[date] = Field(
        None,
        description="Date when certification was issued"
    )
    expiration_date: Optional[date] = Field(
        None,
        description="Date when certification expires"
    )
    credential_id: Optional[str] = Field(
        None,
        description="Certification ID or credential number"
    )
    url: Optional[HttpUrl] = Field(
        None,
        description="URL to verify the certification"
    )
    is_active: bool = Field(
        True,
        description="Whether the certification is currently active"
    )

class Language(BaseModel):
    """Language proficiency information."""
    language: str = Field(
        ...,
        description="Name of the language"
    )
    proficiency: Optional[str] = Field(
        None,
        description="Proficiency level (e.g., Native, Fluent, Intermediate, Basic)"
    )
    is_native: bool = Field(
        False,
        description="Whether this is a native language"
    )

class Resume(BaseModel):
    """Complete resume data structure with comprehensive fields."""
    
    # Basic Information
    full_name: str = Field(
        ...,
        description="Full name of the candidate as it appears on the resume"
    )
    
    professional_title: Optional[str] = Field(
        None,
        description="Professional title or desired position"
    )
    
    # Contact and Links
    contact_info: ContactInfo = Field(
        ...,
        description="Contact information including email, phone, and address"
    )
    
    social_links: Optional[SocialLinks] = Field(
        None,
        description="Social media and professional profile links"
    )
    
    # Summary and Objective
    professional_summary: Optional[str] = Field(
        None,
        description="Professional summary or objective statement from the resume"
    )
    
    # Skills
    technical_skills: List[Skill] = Field(
        default_factory=list,
        description="Technical skills, programming languages, tools, and technologies"
    )
    
    soft_skills: List[str] = Field(
        default_factory=list,
        description="Soft skills and interpersonal abilities"
    )
    
    # Experience
    work_experience: List[WorkExperience] = Field(
        default_factory=list,
        description="Professional work experience history"
    )
    
    total_years_experience: Optional[float] = Field(
        None,
        ge=0,
        description="Total years of professional experience"
    )
    
    experience_level: Optional[ExperienceLevel] = Field(
        None,
        description="Overall experience level of the candidate"
    )
    
    # Education
    education: List[Education] = Field(
        default_factory=list,
        description="Educational background and qualifications"
    )
    
    highest_education_level: Optional[EducationLevel] = Field(
        None,
        description="Highest level of education achieved"
    )
    
    # Projects and Additional Information
    projects: List[Project] = Field(
        default_factory=list,
        description="Personal, academic, or professional projects"
    )
    
    certifications: List[Certification] = Field(
        default_factory=list,
        description="Professional certifications and licenses"
    )
    
    languages: List[Language] = Field(
        default_factory=list,
        description="Language proficiencies"
    )
    
    # Metadata
    keywords: List[str] = Field(
        default_factory=list,
        description="Key terms and keywords extracted from the resume"
    )
    
    parsing_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score of the parsing accuracy"
    )

class ResumeParser:
    """Main resume parser class using Instructor for structured extraction."""
    
    def __init__(self, api_key: str, model: str = "gpt-4", temperature: float = 0.1):
        self.client =  Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model
        self.temperature = temperature
        logger.info(f"Initialized ResumeParser with model: {model}")
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        doc = docx.Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    
    def parse_resume(self, resume_text: str) -> Resume:
        """Parse resume text into structured data using comprehensive prompting."""
        
        system_prompt = """
        You are an expert HR professional and resume parser. Extract comprehensive, 
        structured information from the resume text with high accuracy.
        
        EXTRACTION GUIDELINES:
        1. Extract ALL relevant information present in the resume
        2. For dates, use YYYY-MM-DD format when possible
        3. Categorize skills appropriately (technical vs soft skills)  
        4. Parse work experience with detailed responsibilities and achievements
        5. Include education with proper degree classification
        6. Extract projects, certifications, and contact information thoroughly
        7. Maintain data integrity - use null for unclear information
        8. Calculate experience levels based on years and roles
        9. Extract keywords and technical terms mentioned
        10. Ensure contact information is properly formatted
        
        SKILL CLASSIFICATION:
        - Technical: Programming languages, frameworks, databases, tools, software
        - Soft: Leadership, communication, teamwork, problem-solving
        
        EXPERIENCE LEVELS:
        - entry: 0-2 years
        - junior: 2-4 years
        - mid: 4-7 years  
        - senior: 7-12 years
        - lead/manager: 10+ years with leadership
        
        Extract comprehensive data ensuring no important details are missed.
        """
        
        user_prompt = f"""
        Parse this resume and extract all information into the structured format:
        
        RESUME TEXT:
        {resume_text}
        
        Extract:
        - Personal and contact information
        - Professional summary/objective
        - Complete work experience with achievements
        - Educational background and qualifications
        - Technical and soft skills with proficiency
        - Projects with technologies and outcomes
        - Certifications and validity periods
        - Languages, awards, and additional information
        """
        
        try:
            parsed_resume = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                response_model=Resume,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_retries=3
            )
            
            # Set parsing confidence
            parsed_resume.parsing_confidence = 0.9
            
            logger.info("Resume parsing completed successfully")
            return parsed_resume
            
        except Exception as e:
            logger.error(f"Error during resume parsing: {e}")
            raise
    
    def export_to_json(self, resume: Resume, file_path: str = None) -> str:
        """Export parsed resume to JSON format."""
        json_data = resume.model_dump(exclude_none=True)
        json_string = json.dumps(json_data, indent=2, default=str)
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_string)
                
        return json_string
