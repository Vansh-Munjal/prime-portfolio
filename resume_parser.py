import fitz  # PyMuPDF
import re

def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_sections(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    sections = {
        "skills": [],
        "projects": [],
        "education": []
    }

    section_patterns = {
        "skills": re.compile(r"^\s*(skills|technical\s+skills)\s*$", re.IGNORECASE),
        "projects": re.compile(r"^\s*(projects|academic\s+projects|major\s+projects)\s*$", re.IGNORECASE),
        "education": re.compile(r"^\s*(education|academic\s+background)\s*$", re.IGNORECASE),
    }

    stop_keywords = re.compile(r"^\s*(experience|certifications|internships|profile|achievements)\s*$", re.IGNORECASE)

    current_section = None

    for line in lines:
        if section_patterns["skills"].match(line):
            current_section = "skills"
            continue
        elif section_patterns["projects"].match(line):
            current_section = "projects"
            continue
        elif section_patterns["education"].match(line):
            current_section = "education"
            continue
        elif stop_keywords.match(line):
            current_section = None
            continue

        if current_section:
            sections[current_section].append(line)

    return sections
