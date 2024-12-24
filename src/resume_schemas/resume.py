from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
import yaml
from pydantic import BaseModel, EmailStr, HttpUrl, Field



class PersonalInformation(BaseModel):
    name: Optional[str]
    surname: Optional[str]
    date_of_birth: Optional[str]
    country: Optional[str]
    city: Optional[str]
    address: Optional[str]
    zip_code: Optional[str] = Field(None, min_length=5, max_length=10)
    phone_prefix: Optional[str]
    phone: Optional[str]
    email: Optional[EmailStr]
    github: Optional[HttpUrl] = None
    linkedin: Optional[HttpUrl] = None


class EducationDetails(BaseModel):
    education_level: Optional[str]
    institution: Optional[str]
    field_of_study: Optional[str]
    final_evaluation_grade: Optional[str]
    start_date: Optional[str]
    year_of_completion: Optional[int]
    exam: Optional[Union[List[Dict[str, str]], Dict[str, str]]] = None


class ExperienceDetails(BaseModel):
    position: Optional[str]
    company: Optional[str]
    employment_period: Optional[str]
    location: Optional[str]
    industry: Optional[str]
    key_responsibilities: Optional[List[Dict[str, str]]] = None
    skills_acquired: Optional[List[str]] = None


class Project(BaseModel):
    name: Optional[str]
    description: Optional[str]
    link: Optional[HttpUrl] = None


class Achievement(BaseModel):
    name: Optional[str]
    description: Optional[str]


class Certifications(BaseModel):
    name: Optional[str]
    description: Optional[str]


class Language(BaseModel):
    language: Optional[str]
    proficiency: Optional[str]


class Availability(BaseModel):
    notice_period: Optional[str]


class SalaryExpectations(BaseModel):
    salary_range_usd: Optional[str]


class SelfIdentification(BaseModel):
    gender: Optional[str]
    pronouns: Optional[str]
    veteran: Optional[str]
    disability: Optional[str]
    ethnicity: Optional[str]


class LegalAuthorization(BaseModel):
    eu_work_authorization: Optional[str]
    us_work_authorization: Optional[str]
    requires_us_visa: Optional[str]
    requires_us_sponsorship: Optional[str]
    requires_eu_visa: Optional[str]
    legally_allowed_to_work_in_eu: Optional[str]
    legally_allowed_to_work_in_us: Optional[str]
    requires_eu_sponsorship: Optional[str]


class Resume(BaseModel):
    personal_information: Optional[PersonalInformation]
    education_details: Optional[List[EducationDetails]] = None
    experience_details: Optional[List[ExperienceDetails]] = None
    projects: Optional[List[Project]] = None
    achievements: Optional[List[Achievement]] = None
    certifications: Optional[List[Certifications]] = None
    languages: Optional[List[Language]] = None
    interests: Optional[List[str]] = None

    @staticmethod
    def normalize_exam_format(exam):
        if isinstance(exam, dict):
            return [{k: v} for k, v in exam.items()]
        return exam

    def from_plain_text(self, yaml_str: str):
        try:
            # Parse the YAML string
            data = yaml.safe_load(yaml_str)

            if 'education_details' in data:
                for ed in data['education_details']:
                    if 'exam' in ed:
                        ed['exam'] = self.normalize_exam_format(ed['exam'])

            # Create an instance of Resume from the parsed data
            super().__init__(**data)
        except yaml.YAMLError as e:
            raise ValueError("Error parsing YAML file.") from e
        except Exception as e:
            raise Exception(f"Unexpected error while parsing YAML: {e}") from e


    def _process_personal_information(self, data: Dict[str, Any]) -> PersonalInformation:
        try:
            return PersonalInformation(**data)
        except TypeError as e:
            raise TypeError(f"Invalid data for PersonalInformation: {e}") from e
        except AttributeError as e:
            raise AttributeError(f"AttributeError in PersonalInformation: {e}") from e
        except Exception as e:
            raise Exception(f"Unexpected error in PersonalInformation processing: {e}") from e

    def _process_education_details(self, data: List[Dict[str, Any]]) -> List[EducationDetails]:
        education_list = []
        for edu in data:
            try:
                exams = [Exam(name=k, grade=v) for k, v in edu.get('exam', {}).items()]
                education = EducationDetails(
                    education_level=edu.get('education_level'),
                    institution=edu.get('institution'),
                    field_of_study=edu.get('field_of_study'),
                    final_evaluation_grade=edu.get('final_evaluation_grade'),
                    start_date=edu.get('start_date'),
                    year_of_completion=edu.get('year_of_completion'),
                    exam=exams
                )
                education_list.append(education)
            except KeyError as e:
                raise KeyError(f"Missing field in education details: {e}") from e
            except TypeError as e:
                raise TypeError(f"Invalid data for Education: {e}") from e
            except AttributeError as e:
                raise AttributeError(f"AttributeError in Education: {e}") from e
            except Exception as e:
                raise Exception(f"Unexpected error in Education processing: {e}") from e
        return education_list

    def _process_experience_details(self, data: List[Dict[str, Any]]) -> List[ExperienceDetails]:
        experience_list = []
        for exp in data:
            try:
                key_responsibilities = [
                    Responsibility(description=list(resp.values())[0])
                    for resp in exp.get('key_responsibilities', [])
                ]
                skills_acquired = [str(skill) for skill in exp.get('skills_acquired', [])]
                experience = ExperienceDetails(
                    position=exp['position'],
                    company=exp['company'],
                    employment_period=exp['employment_period'],
                    location=exp['location'],
                    industry=exp['industry'],
                    key_responsibilities=key_responsibilities,
                    skills_acquired=skills_acquired
                )
                experience_list.append(experience)
            except KeyError as e:
                raise KeyError(f"Missing field in experience details: {e}") from e
            except TypeError as e:
                raise TypeError(f"Invalid data for Experience: {e}") from e
            except AttributeError as e:
                raise AttributeError(f"AttributeError in Experience: {e}") from e
            except Exception as e:
                raise Exception(f"Unexpected error in Experience processing: {e}") from e
        return experience_list

    def to_plain_text(self) -> str:
        def format_list(items):
            if items:
                return "\n".join(f"- {item}" for item in items)
            return "None"

        def format_education_details(details):
            return "\n\n".join(
                f"Education Level: {detail.education_level}\n"
                f"Institution: {detail.institution}\n"
                f"Field of Study: {detail.field_of_study}\n"
                f"Final Evaluation Grade: {detail.final_evaluation_grade}\n"
                f"Start Date: {detail.start_date}\n"
                f"Year of Completion: {detail.year_of_completion}\n"
                f"Exams: {', '.join(f'{exam.name}: {exam.grade}' for exam in detail.exam) if detail.exam else 'None'}"
                for detail in details
            ) if details else "None"

        def format_experience_details(details):
            return "\n\n".join(
                f"Position: {detail.position}\n"
                f"Company: {detail.company}\n"
                f"Employment Period: {detail.employment_period}\n"
                f"Location: {detail.location}\n"
                f"Industry: {detail.industry}\n"
                f"Key Responsibilities: {', '.join(resp['responsibility'] for resp in detail.key_responsibilities) if detail.key_responsibilities else 'None'}\n"
                f"Skills Acquired: {', '.join(detail.skills_acquired) if detail.skills_acquired else 'None'}"
                for detail in details
            ) if details else "None"

        return (
            f"Personal Information: {self.personal_information}\n\n"
            f"Education Details:\n{format_education_details(self.education_details)}\n\n"
            f"Experience Details:\n{format_experience_details(self.experience_details)}\n\n"
            f"Projects:\n{format_list(self.projects)}\n\n"
            f"Achievements:\n{format_list(self.achievements)}\n\n"
            f"Certifications:\n{format_list(self.certifications)}\n\n"
            f"Languages:\n{format_list(self.languages)}\n\n"
            f"Interests:\n{format_list(self.interests)}"
        )
    
@dataclass
class Exam:
    name: str
    grade: str

@dataclass
class Responsibility:
    description: str