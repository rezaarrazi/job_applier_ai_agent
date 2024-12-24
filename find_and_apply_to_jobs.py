"""
Find and apply to jobs.

@dev You need to add OPENAI_API_KEY to your environment variables.

Also you have to install PyPDF2 to read pdf files: pip install PyPDF2
"""

import csv
import os
import re
import sys
from pathlib import Path

from browser_use.browser.browser import Browser, BrowserConfig

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from typing import List, Optional, Tuple, Dict

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from pydantic import BaseModel, SecretStr

from browser_use import ActionResult, Agent, Controller
from browser_use.browser.context import BrowserContext

load_dotenv()
import logging

logger = logging.getLogger(__name__)
# full screen mode
controller = Controller()

import base64
import sys
from pathlib import Path
import traceback

import inquirer
import yaml
import re
from src.libs.resume_and_cover_builder import ResumeFacade, ResumeGenerator, StyleManager
from src.resume_schemas.resume import Resume
from src.logging import logger
from src.utils.chrome_utils import init_browser
from src.utils.constants import (
    PLAIN_TEXT_RESUME_YAML,
    SECRETS_YAML,
    WORK_PREFERENCES_YAML,
)
from src.job import Job, JobPreferences

# CV = Path.cwd() / 'Resume - M. Reza Arrazi.pdf'
# print(f"CV: {CV}")

llm_api_key = os.getenv("OPENAI_API_KEY")
resume = None
job_preferences = None

output_folder = None

class ConfigError(Exception):
    """Custom exception for configuration-related errors."""
    pass


class ConfigValidator:
    """Validates configuration and secrets YAML files."""

    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    REQUIRED_CONFIG_KEYS = {
        "remote": bool,
        "experience_level": dict,
        "job_types": dict,
        "date": dict,
        "positions": list,
        "locations": list,
        "location_blacklist": list,
        "distance": int,
        "company_blacklist": list,
        "title_blacklist": list,
    }
    EXPERIENCE_LEVELS = [
        "internship",
        "entry",
        "associate",
        "mid_senior_level",
        "director",
        "executive",
    ]
    JOB_TYPES = [
        "full_time",
        "contract",
        "part_time",
        "temporary",
        "internship",
        "other",
        "volunteer",
    ]
    DATE_FILTERS = ["all_time", "month", "week", "hours_24"]
    APPROVED_DISTANCES = {0, 5, 10, 25, 50, 100}

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate the format of an email address."""
        return bool(ConfigValidator.EMAIL_REGEX.match(email))

    @staticmethod
    def load_yaml(yaml_path: Path) -> dict:
        """Load and parse a YAML file."""
        try:
            with open(yaml_path, "r") as stream:
                return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Error reading YAML file {yaml_path}: {exc}")
        except FileNotFoundError:
            raise ConfigError(f"YAML file not found: {yaml_path}")

    @classmethod
    def validate_config(cls, config_yaml_path: Path) -> dict:
        """Validate the main configuration YAML file."""
        parameters = cls.load_yaml(config_yaml_path)
        # Check for required keys and their types
        for key, expected_type in cls.REQUIRED_CONFIG_KEYS.items():
            if key not in parameters:
                if key in ["company_blacklist", "title_blacklist", "location_blacklist"]:
                    parameters[key] = []
                else:
                    raise ConfigError(f"Missing required key '{key}' in {config_yaml_path}")
            elif not isinstance(parameters[key], expected_type):
                if key in ["company_blacklist", "title_blacklist", "location_blacklist"] and parameters[key] is None:
                    parameters[key] = []
                else:
                    raise ConfigError(
                        f"Invalid type for key '{key}' in {config_yaml_path}. Expected {expected_type.__name__}."
                    )
        cls._validate_experience_levels(parameters["experience_level"], config_yaml_path)
        cls._validate_job_types(parameters["job_types"], config_yaml_path)
        cls._validate_date_filters(parameters["date"], config_yaml_path)
        cls._validate_list_of_strings(parameters, ["positions", "locations"], config_yaml_path)
        cls._validate_distance(parameters["distance"], config_yaml_path)
        cls._validate_blacklists(parameters, config_yaml_path)
        return parameters

    @classmethod
    def _validate_experience_levels(cls, experience_levels: dict, config_path: Path):
        """Ensure experience levels are booleans."""
        for level in cls.EXPERIENCE_LEVELS:
            if not isinstance(experience_levels.get(level), bool):
                raise ConfigError(
                    f"Experience level '{level}' must be a boolean in {config_path}"
                )

    @classmethod
    def _validate_job_types(cls, job_types: dict, config_path: Path):
        """Ensure job types are booleans."""
        for job_type in cls.JOB_TYPES:
            if not isinstance(job_types.get(job_type), bool):
                raise ConfigError(
                    f"Job type '{job_type}' must be a boolean in {config_path}"
                )

    @classmethod
    def _validate_date_filters(cls, date_filters: dict, config_path: Path):
        """Ensure date filters are booleans."""
        for date_filter in cls.DATE_FILTERS:
            if not isinstance(date_filters.get(date_filter), bool):
                raise ConfigError(
                    f"Date filter '{date_filter}' must be a boolean in {config_path}"
                )

    @classmethod
    def _validate_list_of_strings(cls, parameters: dict, keys: list, config_path: Path):
        """Ensure specified keys are lists of strings."""
        for key in keys:
            if not all(isinstance(item, str) for item in parameters[key]):
                raise ConfigError(
                    f"'{key}' must be a list of strings in {config_path}"
                )

    @classmethod
    def _validate_distance(cls, distance: int, config_path: Path):
        """Validate the distance value."""
        if distance not in cls.APPROVED_DISTANCES:
            raise ConfigError(
                f"Invalid distance value '{distance}' in {config_path}. Must be one of: {cls.APPROVED_DISTANCES}"
            )

    @classmethod
    def _validate_blacklists(cls, parameters: dict, config_path: Path):
        """Ensure blacklists are lists."""
        for blacklist in ["company_blacklist", "title_blacklist", "location_blacklist"]:
            if not isinstance(parameters.get(blacklist), list):
                raise ConfigError(
                    f"'{blacklist}' must be a list in {config_path}"
                )
            if parameters[blacklist] is None:
                parameters[blacklist] = []

    @staticmethod
    def validate_secrets(secrets_yaml_path: Path) -> str:
        """Validate the secrets YAML file and retrieve the LLM API key."""
        secrets = ConfigValidator.load_yaml(secrets_yaml_path)
        mandatory_secrets = ["llm_api_key"]

        for secret in mandatory_secrets:
            if secret not in secrets:
                raise ConfigError(f"Missing secret '{secret}' in {secrets_yaml_path}")

            if not secrets[secret]:
                raise ConfigError(f"Secret '{secret}' cannot be empty in {secrets_yaml_path}")

        return secrets["llm_api_key"]


class FileManager:
    """Handles file system operations and validations."""

    REQUIRED_FILES = [SECRETS_YAML, WORK_PREFERENCES_YAML, PLAIN_TEXT_RESUME_YAML]

    @staticmethod
    def validate_data_folder(app_data_folder: Path) -> Tuple[Path, Path, Path, Path]:
        """Validate the existence of the data folder and required files."""
        if not app_data_folder.is_dir():
            raise FileNotFoundError(f"Data folder not found: {app_data_folder}")

        missing_files = [file for file in FileManager.REQUIRED_FILES if not (app_data_folder / file).exists()]
        if missing_files:
            raise FileNotFoundError(f"Missing files in data folder: {', '.join(missing_files)}")

        output_folder = app_data_folder / "output"
        output_folder.mkdir(exist_ok=True)

        return (
            app_data_folder / SECRETS_YAML,
            app_data_folder / WORK_PREFERENCES_YAML,
            app_data_folder / PLAIN_TEXT_RESUME_YAML,
            output_folder,
        )

    @staticmethod
    def get_uploads(plain_text_resume_file: Path) -> Dict[str, Path]:
        """Convert resume file paths to a dictionary."""
        if not plain_text_resume_file.exists():
            raise FileNotFoundError(f"Plain text resume file not found: {plain_text_resume_file}")

        uploads = {"plainTextResume": plain_text_resume_file}

        return uploads

@controller.action(
	'Create tailored cover letter based on job descriptions', param_model=Job
)
def create_cover_letter(job: Job):
    """
    Logic to create a CV.
    """
    try:
        logger.info("Generating a CV based on provided parameters.")

        style_manager = StyleManager()
        available_styles = style_manager.get_styles()

        if not available_styles:
            logger.warning("No styles available. Proceeding without style selection.")
        else:
            # Present style choices to the user
            choices = style_manager.format_choices(available_styles)
            questions = [
                inquirer.List(
                    "style",
                    message="Select a style for the resume:",
                    choices=choices,
                )
            ]
            style_answer = inquirer.prompt(questions)
            if style_answer and "style" in style_answer:
                selected_choice = style_answer["style"]
                for style_name, (file_name, author_link) in available_styles.items():
                    if selected_choice.startswith(style_name):
                        style_manager.set_selected_style(style_name)
                        logger.info(f"Selected style: {style_name}")
                        break
            else:
                logger.warning("No style selected. Proceeding with default style.")
        resume_generator = ResumeGenerator()
        resume_object = resume
        driver = init_browser()
        resume_generator.set_resume_object(resume_object)
        resume_facade = ResumeFacade(            
            api_key=llm_api_key,
            style_manager=style_manager,
            resume_generator=resume_generator,
            resume_object=resume_object,
            output_path=Path("data_folder/output"),
        )
        resume_facade.set_driver(driver)

        resume_facade.update_job(job)
        result_base64, suggested_name = resume_facade.create_cover_letter()         

        # Decodifica Base64 in dati binari
        try:
            pdf_data = base64.b64decode(result_base64)
        except base64.binascii.Error as e:
            logger.error("Error decoding Base64: %s", e)
            raise

        # Definisci il percorso della cartella di output utilizzando `suggested_name`
        output_dir = Path(output_folder) / suggested_name

        # Crea la cartella se non esiste
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cartella di output creata o già esistente: {output_dir}")
        except IOError as e:
            logger.error("Error creating output directory: %s", e)
            raise
        
        output_path = output_dir / "cover_letter_tailored.pdf"
        try:
            with open(output_path, "wb") as file:
                file.write(pdf_data)
            print(f"\033[92mCover letter saved in: {output_path}\033[0m")
            logger.info(f"CV salvato in: {output_path}")
        except IOError as e:
            logger.error("Error writing file: %s", e)
            raise
    except Exception as e:
        logger.exception(f"An error occurred while creating the CV: {e}")
        raise

@controller.action(
	'Create tailored CV based on job descriptions', param_model=Job
	)
def create_resume_pdf_job_tailored(job: Job):
	"""
	Logic to create a CV.
	"""
	try:
		logger.info("Generating a CV based on provided parameters.")

		style_manager = StyleManager()
		available_styles = style_manager.get_styles()

		if not available_styles:
			logger.warning("No styles available. Proceeding without style selection.")
		else:
			# Present style choices to the user
			choices = style_manager.format_choices(available_styles)
			questions = [
				inquirer.List(
					"style",
					message="Select a style for the resume:",
					choices=choices,
				)
			]
			style_answer = inquirer.prompt(questions)
			if style_answer and "style" in style_answer:
				selected_choice = style_answer["style"]
				for style_name, (file_name, author_link) in available_styles.items():
					if selected_choice.startswith(style_name):
						style_manager.set_selected_style(style_name)
						logger.info(f"Selected style: {style_name}")
						break
			else:
				logger.warning("No style selected. Proceeding with default style.")
		resume_generator = ResumeGenerator()
		resume_object = resume
		driver = init_browser()
		resume_generator.set_resume_object(resume_object)
		resume_facade = ResumeFacade(            
			api_key=llm_api_key,
			style_manager=style_manager,
			resume_generator=resume_generator,
			resume_object=resume_object,
			output_path=Path("data_folder/output"),
		)
		resume_facade.set_driver(driver)
		
		resume_facade.update_job(job)
		result_base64, suggested_name = resume_facade.create_resume_pdf_job_tailored()         

		# Decodifica Base64 in dati binari
		try:
			pdf_data = base64.b64decode(result_base64)
		except base64.binascii.Error as e:
			logger.error("Error decoding Base64: %s", e)
			raise

		# Definisci il percorso della cartella di output utilizzando `suggested_name`
		output_dir = Path(output_folder) / suggested_name

		# Crea la cartella se non esiste
		try:
			output_dir.mkdir(parents=True, exist_ok=True)
			logger.info(f"Cartella di output creata o già esistente: {output_dir}")
		except IOError as e:
			logger.error("Error creating output directory: %s", e)
			raise
		
		output_path = output_dir / "resume_tailored.pdf"
		try:
			with open(output_path, "wb") as file:
				file.write(pdf_data)
			print(f"\033[92mResume saved in: {output_path}\033[0m")
			logger.info(f"CV salvato in: {output_path}")
		except IOError as e:
			logger.error("Error writing file: %s", e)
			raise
	except Exception as e:
		logger.exception(f"An error occurred while creating the CV: {e}")
		raise

@controller.action(
	'Save jobs to file - with a score how well it fits to my profile', param_model=Job
)
def save_jobs(job: Job):
	with open('jobs.csv', 'a', newline='') as f:
		writer = csv.writer(f)
		writer.writerow(job.__dict__.values())

	return 'Saved job to file'


@controller.action('Read jobs from file')
def read_jobs():
	with open('jobs.csv', 'r') as f:
		return f.read()


# @controller.action('Read my cv for context to fill forms')
# def read_cv():
# 	pdf = PdfReader(CV)
# 	text = ''
# 	for page in pdf.pages:
# 		text += page.extract_text() or ''
# 	logger.info(f'Read cv with {len(text)} characters')
# 	return ActionResult(extracted_content=text, include_in_memory=True)

@controller.action('Read my cv for context to fill forms')
def read_cv():
	# Load the plain text resume
	plain_text_resume = resume.to_plain_text()
		
	logger.info(f'Read cv with {len(plain_text_resume)} characters')
	return ActionResult(extracted_content=plain_text_resume, include_in_memory=True)

@controller.action('Read my job preferences to find jobs')
def read_job_preferences():
    # Load the plain text job preferences
	job_preferences_text = job_preferences.to_plain_text()
    	
	logger.info(f'Read job preferences with {len(job_preferences_text)} characters')
	return ActionResult(extracted_content=job_preferences_text, include_in_memory=True)

@controller.action(
	'Upload cv to element - call this function to upload if element is not found, try with different index of the same upload element',
	requires_browser=True,
)
async def upload_cv(index: int, browser: BrowserContext):
	logger.info(f'Uploading file to index {index}')
	
	path = output_folder / 'resume_tailored.pdf'
	dom_el = await browser.get_dom_element_by_index(index)

	if dom_el is None:
		return ActionResult(error=f'No element found at index {index}')

	file_upload_dom_el = dom_el.get_file_upload_element()

	if file_upload_dom_el is None:
		logger.info(f'No file upload element found at index {index}')
		return ActionResult(error=f'No file upload element found at index {index}')

	file_upload_el = await browser.get_locate_element(file_upload_dom_el)

	if file_upload_el is None:
		logger.info(f'No file upload element found at index {index}')
		return ActionResult(error=f'No file upload element found at index {index}')

	try:
		await file_upload_el.set_input_files(path)
		msg = f'Successfully uploaded file to index {index}'
		logger.info(msg)
		return ActionResult(extracted_content=msg)
	except Exception as e:
		logger.debug(f'Error in set_input_files: {str(e)}')
		return ActionResult(error=f'Failed to upload file to index {index}')


browser = Browser(
	config=BrowserConfig(
		chrome_instance_path='/usr/bin/google-chrome',
		disable_security=True,
	)
)

def load_job_preferences_from_yaml(file_path: str) -> JobPreferences:
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
    return JobPreferences(**data)

def load_resume_from_yaml(file_path: str) -> Resume:
	with open(file_path, 'r') as file:
		data = yaml.safe_load(file)
          
	return Resume(**data)

async def main():
	try:
		# Define and validate the data folder
		data_folder = Path("data_folder")
        
		global output_folder
		secrets_file, job_preferences_file, plain_text_resume_file, output_folder = FileManager.validate_data_folder(data_folder)

		global resume
		resume = load_resume_from_yaml(plain_text_resume_file)
		global job_preferences
		job_preferences = load_job_preferences_from_yaml(job_preferences_file)

		# # Validate configuration and secrets
		# config = ConfigValidator.validate_config(job_preferences_file)

		# # Prepare parameters
		# config["uploads"] = FileManager.get_uploads(plain_text_resume_file)
		# config["outputFileDirectory"] = output_folder
			
		# ground_task = (
		# 	'You are a professional job finder. '
		# 	'1. Read my cv with read_cv'
		# 	'2. Read the saved jobs file '
		# 	'3. start applying to the first link of Amazon '
		# 	'You can navigate through pages e.g. by scrolling '
		# 	'Make sure to be on the english version of the page'
		# )
		ground_task = (
			'You are a professional job finder. \n'
			'1. Read my cv with read_cv\n'
			'2. Read my job preferences to find the desired job type and location with read_job_preferences\n'
			'3. find jobs based on my job preferences and location, search at linkedin: https://www.linkedin.com/jobs/'
			' . to read the job description and responsibilities you need to click the job list on the left side one by one. You can navigate through pages e.g. by scrolling on the right side. repeat this step for atleast 5 different jobs\n'
			'4. Save jobs to file - with a score how well it fits to my profile, considering the job description and responsibilities to match my experience and skills\n'
			'5. Read the saved jobs file\n'
			'6. start applying to the most suitable job based on the score\n'
			'7. genereate a resume tailored for the job description with create_resume_pdf_job_tailored\n'
            '8. genereate a cover letter tailored for the job description with create_cover_letter\n'
            '9. Choose "Apply With LinkedIn" if available\n'
		)
		tasks = [
				ground_task
			]
		# model = AzureChatOpenAI(
		# 	model='gpt-4o',
		# 	api_version='2024-10-21',
		# 	azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', ''),
		# 	api_key=SecretStr(os.getenv('AZURE_OPENAI_KEY', '')),
		# )
		model = ChatOpenAI(
			model="gpt-4o",
			temperature=0,
			max_tokens=None,
			timeout=None,
			max_retries=2,
			# api_key="...",  # if you prefer to pass api key in directly instaed of using env vars
			# base_url="...",
			# organization="...",
			# other params...
		)

		agents = []
		for task in tasks:
			agent = Agent(task=task, llm=model, controller=controller, browser=browser)
			agents.append(agent)

		await asyncio.gather(*[agent.run() for agent in agents])

		# # Interactive prompt for user to select actions
		# selected_actions = prompt_user_action()

		# # Handle selected actions and execute them
		# handle_inquiries(selected_actions, config, llm_api_key)

	except ConfigError as ce:
		logger.error(f"Configuration error: {ce}")
		logger.error(
		"Refer to the configuration guide for troubleshooting: "
		"https://github.com/feder-cr/Auto_Jobs_Applier_AIHawk?tab=readme-ov-file#configuration"
	)
	except FileNotFoundError as fnf:
		logger.error(f"File not found: {fnf}")
		logger.error("Ensure all required files are present in the data folder.")
	except RuntimeError as re:
		logger.error(f"Runtime error: {re}")
		logger.debug(traceback.format_exc())
	except Exception as e:
		print(f"An unexpected error occurred: {e}")
		logger.exception(f"An unexpected error occurred: {e}")
          
if __name__ == '__main__':
	print('Starting the main function')
	asyncio.run(main())
