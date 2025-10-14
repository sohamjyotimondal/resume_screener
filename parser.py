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


# Simplified Pydantic Models for Resume Components


class ExternalLinks(BaseModel):
    """External profile links and websites."""

    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    github: Optional[str] = Field(None, description="GitHub profile URL")
    portfolio: Optional[str] = Field(None, description="Personal portfolio/website URL")
    other: Optional[List[str]] = Field(
        default_factory=list, description="Other relevant links"
    )


class ContactInfo(BaseModel):
    """Basic contact information."""

    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="City, State/Country")


class Education(BaseModel):
    """Educational qualification."""

    institution: str = Field(..., description="School/University name")
    degree: str = Field(..., description="Degree obtained")
    field_of_study: Optional[str] = Field(None, description="Major/Field of study")
    graduation_year: Optional[str] = Field(None, description="Graduation year or date")


class WorkExperience(BaseModel):
    """Work experience entry."""

    company: str = Field(..., description="Company name")
    position: str = Field(..., description="Job title")
    duration: Optional[str] = Field(
        None, description="Duration (e.g., '2020-2023' or '2 years')"
    )
    description: Optional[str] = Field(
        None, description="Brief job description and achievements"
    )


class Project(BaseModel):
    """Project details."""

    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    technologies: Optional[List[str]] = Field(
        default_factory=list, description="Technologies used"
    )
    url: Optional[str] = Field(None, description="Project URL/link")


class Certification(BaseModel):
    """Certification details."""

    name: str = Field(..., description="Certification name")
    issuer: str = Field(..., description="Issuing organization")
    date: Optional[str] = Field(None, description="Issue date or year")


class Resume(BaseModel):
    """Simplified resume data structure."""

    # Basic Information
    full_name: str = Field(..., description="Full name of the candidate")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="City, State/Country")

    # External Links
    external_links: Optional[ExternalLinks] = Field(
        None, description="LinkedIn, GitHub, portfolio, and other professional links"
    )

    # Professional Summary
    summary: Optional[str] = Field(
        None, description="Professional summary or objective"
    )

    # Skills
    skills: List[str] = Field(
        default_factory=list, description="List of technical and professional skills"
    )

    # Experience
    work_experience: List[WorkExperience] = Field(
        default_factory=list, description="Work experience history"
    )

    # Education
    education: List[Education] = Field(
        default_factory=list, description="Educational background"
    )

    # Projects
    projects: List[Project] = Field(
        default_factory=list, description="Notable projects"
    )

    # Certifications
    certifications: List[Certification] = Field(
        default_factory=list, description="Professional certifications"
    )


class ResumeParser:
    """Main resume parser class using Instructor for structured extraction."""

    def __init__(
        self,
        api_key: str = None,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.1,
    ):
        # Initialize Groq client and patch it with Instructor
        groq_client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
        self.client = instructor.from_groq(groq_client)
        self.model = model
        self.temperature = temperature
        logger.info(f"Initialized ResumeParser with Groq model: {model}")

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        with open(file_path, "rb") as file:
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
        """Parse resume text into structured data."""

        system_prompt = """
        You are an expert resume parser. Extract information from resumes accurately and structure it cleanly.
        
        EXTRACTION GUIDELINES:
        1. Extract name, email, phone, and location from contact info
        2. Find LinkedIn, GitHub, portfolio URLs and other external links
        3. Extract professional summary/objective
        4. List all skills mentioned (technical and soft skills combined)
        5. Parse work experience with company, position, duration, and key achievements
        6. Extract education with institution, degree, field, and graduation year
        7. Find projects with descriptions and technologies used
        8. Extract certifications with issuer and date
        9. Use null/empty for missing information
        10. Keep descriptions concise but informative
        """

        user_prompt = f"""
        Parse this resume and extract the information:
        
        RESUME TEXT:
        {resume_text}
        
        Extract all available information including:
        - Name and contact details (email, phone, location)
        - External links (LinkedIn, GitHub, portfolio, etc.)
        - Professional summary
        - Skills
        - Work experience
        - Education
        - Projects
        - Certifications
        """

        try:
            parsed_resume = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                response_model=Resume,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_retries=3,
            )

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
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_string)

        return json_string


if __name__ == "__main__":
    # Test the parser with resume_f.pdf
    print("=" * 60)
    print("Testing Resume Parser with Groq + Instructor")
    print("=" * 60)

    try:
        # Initialize parser
        parser = ResumeParser()
        print("\n✓ Parser initialized successfully")

        # Extract text from PDF
        pdf_path = "resume_f.pdf"
        print(f"\n📄 Extracting text from: {pdf_path}")
        resume_text = parser.extract_text_from_pdf(pdf_path)
        print(f"✓ Extracted {len(resume_text)} characters")
        print(f"\nFirst 500 characters:\n{resume_text[:500]}...")

        # Parse resume
        print("\n🤖 Parsing resume with Groq LLM...")
        parsed_resume = parser.parse_resume(resume_text)
        print("✓ Resume parsed successfully!")

        # Display key information
        print("\n" + "=" * 60)
        print("PARSED RESUME SUMMARY")
        print("=" * 60)
        print(f"\n👤 Name: {parsed_resume.full_name}")
        print(f"📧 Email: {parsed_resume.email or 'Not provided'}")
        print(f"📱 Phone: {parsed_resume.phone or 'Not provided'}")
        print(f"📍 Location: {parsed_resume.location or 'Not provided'}")

        # External Links
        if parsed_resume.external_links:
            print("\n🔗 External Links:")
            if parsed_resume.external_links.linkedin:
                print(f"   LinkedIn: {parsed_resume.external_links.linkedin}")
            if parsed_resume.external_links.github:
                print(f"   GitHub: {parsed_resume.external_links.github}")
            if parsed_resume.external_links.portfolio:
                print(f"   Portfolio: {parsed_resume.external_links.portfolio}")
            if parsed_resume.external_links.other:
                for link in parsed_resume.external_links.other:
                    print(f"   Other: {link}")

        if parsed_resume.summary:
            print(f"\n📝 Summary: {parsed_resume.summary[:200]}...")

        print(f"\n🎓 Education: {len(parsed_resume.education)} entries")
        for edu in parsed_resume.education:
            print(f"   - {edu.degree} from {edu.institution}")
            if edu.graduation_year:
                print(f"     Year: {edu.graduation_year}")

        print(f"\n💼 Work Experience: {len(parsed_resume.work_experience)} positions")
        for exp in parsed_resume.work_experience:
            print(f"   - {exp.position} at {exp.company}")
            if exp.duration:
                print(f"     Duration: {exp.duration}")

        print(f"\n🛠️  Skills: {len(parsed_resume.skills)} skills")
        for i, skill in enumerate(parsed_resume.skills[:15], 1):  # Show first 15
            print(f"   {i}. {skill}")

        if len(parsed_resume.skills) > 15:
            print(f"   ... and {len(parsed_resume.skills) - 15} more")

        print(f"\n🚀 Projects: {len(parsed_resume.projects)} projects")
        for proj in parsed_resume.projects:
            print(f"   - {proj.name}")

        print(
            f"\n📜 Certifications: {len(parsed_resume.certifications)} certifications"
        )
        for cert in parsed_resume.certifications:
            print(f"   - {cert.name} from {cert.issuer}")

        # Export to JSON
        output_path = "parsed_resume.json"
        json_output = parser.export_to_json(parsed_resume, output_path)
        print(f"\n✓ Full results exported to: {output_path}")

        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"\n❌ Error: resume_f.pdf not found in current directory")
        print(f"   Make sure the file exists at: {os.path.abspath('resume_f.pdf')}")
    except Exception as e:
        print(f"\n❌ Error during parsing: {e}")
        import traceback

        traceback.print_exc()
