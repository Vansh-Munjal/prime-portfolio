from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from jinja2 import Environment, FileSystemLoader
from reportlab.lib.pagesizes import A4
import shutil
import os
from typing import List
import uuid

# Resume parsing
from resume_parser import extract_text_from_pdf, extract_sections

# FastAPI setup
app = FastAPI()
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

UPLOAD_DIR = "uploads"
DOWNLOAD_DIR = "downloads"
# Ensure folders exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# Template & static file setup
templates = Jinja2Templates(directory="templates")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ========== Routes ==========

@app.get("/images/{image_name}")
def get_image(image_name: str):
    image_path = os.path.join("images", image_name)
    if os.path.exists(image_path):
        return FileResponse(image_path)
    return {"error": "Image not found"}

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/form", response_class=HTMLResponse)
async def show_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

@app.post("/submit", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    name: str = Form(...),
    title: str = Form(...),
    summary: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    linkedin: str = Form(""),
    github: str = Form(""),
    resume: UploadFile = File(...),
    photo: UploadFile = File(None)
):
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    # ======== Handle Profile Photo Upload ========
    photo_url = None
    if photo and photo.filename:
        photo_ext = os.path.splitext(photo.filename)[-1].lower()
        if photo_ext not in [".jpg", ".jpeg", ".png"]:
            return templates.TemplateResponse("form.html", {
                "request": request,
                "error": "Profile photo must be a JPG or PNG file."
            })
        photo_filename = f"{uuid.uuid4()}{photo_ext}"
        photo_path = os.path.join(upload_dir, photo_filename)
        with open(photo_path, "wb") as f:
            f.write(await photo.read())
        photo_url = f"/uploads/{photo_filename}"

    # ======== Handle Resume Upload ========
    if not resume.filename.lower().endswith(".pdf"):
        return templates.TemplateResponse("form.html", {
            "request": request,
            "error": "Only PDF resumes are supported."
        })

    resume_filename = f"{uuid.uuid4()}.pdf"
    resume_path = os.path.join(upload_dir, resume_filename)

    with open(resume_path, "wb") as f:
        shutil.copyfileobj(resume.file, f)

    # ======== Resume Text Extraction ========
    try:
        text = extract_text_from_pdf(resume_path)
        if not text.strip():
            raise ValueError("The uploaded resume seems to be empty.")

        extracted = extract_sections(text)

    except Exception as e:
        return templates.TemplateResponse("form.html", {
            "request": request,
            "error": f"Failed to process resume: {str(e)}"
        })

    # ======== Render Portfolio Preview ========
    return templates.TemplateResponse("success.html", {
        "request": request,
        "data": {
            "name": name,
            "title": title,
            "summary": summary,
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "github": github,
            "skills": extracted.get("skills", []),
            "education": extracted.get("education", []),
            "projects": extracted.get("projects", []),
            "photo_url": photo_url
        }
    })

@app.get("/select-template", response_class=HTMLResponse)
async def select_template(request: Request):
    return templates.TemplateResponse("templates.html", {"request": request})

# Route to handle form submission (selected template)
@app.post("/generate-portfolio", response_class=HTMLResponse)
async def generate_portfolio(
    request: Request,
    template: str = Form(...),
    name: str = Form(...),
    title: str = Form(...),
    summary: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    linkedin: str = Form(""),
    github: str = Form(""),
    photo_url: str = Form(""),
    skills: List[str] = Form([]),
    education: List[str] = Form([]),
    projects: List[str] = Form([]),
):
    extracted_data = {
        "name": name,
        "title": title,
        "summary": summary,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "photo_url": photo_url,
        "skills": skills,
        "education": education,
        "projects": projects
    }

    # Render HTML using Jinja2 manually to save file
    env = Environment(loader=FileSystemLoader("templates"))
    template_obj = env.get_template(f"{template}.html")
    rendered_html = template_obj.render(request=request, data=extracted_data)

    # Save the rendered HTML to downloads folder
    html_filename = f"{uuid.uuid4()}.html"
    html_path = os.path.join(DOWNLOAD_DIR, html_filename)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    # Add filename to extracted data for download button
    extracted_data["html_filename"] = html_filename

    return templates.TemplateResponse(f"{template}.html", {
        "request": request,
        "data": extracted_data
    })

@app.get("/download-html/{filename}")
async def download_html(filename: str):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/html", filename="MyPortfolio.html")
    else:
        raise HTTPException(status_code=404, detail="Portfolio HTML not found")
    
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
