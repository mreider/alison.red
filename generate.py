#!/usr/bin/env python3
"""
Resume Generator Script
Converts resume.txt to styled HTML resume and PDF
"""

import re
import subprocess
import sys
from typing import List, Dict, Any

def parse_resume_data(filename: str) -> Dict[str, Any]:
    """Parse the resume data from text file"""
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    data = {}

    # Parse basic info - handle both old and new formats
    name_match = re.search(r'NAME: (.+)', content)
    if name_match:
        # Old format
        data['name'] = name_match.group(1)
        data['phone'] = re.search(r'PHONE: (.+)', content).group(1)
        data['email'] = re.search(r'EMAIL: (.+)', content).group(1)
        data['location'] = re.search(r'LOCATION: (.+)', content).group(1)
    else:
        # New format - parse header line
        first_line = content.split('\n')[0]
        # More flexible parsing for the format: "ALISON S. COHEN      Vienna, Austria  ✦  +4367763177110  ✦  alison.cohen@gmail.com"
        parts = first_line.split('✦')
        if len(parts) >= 3:
            # Extract name and location from first part
            first_part = parts[0].strip()
            # Find where location starts (look for capital letter after spaces)
            location_match = re.search(r'(.+?)\s{2,}([A-Z].+)$', first_part)
            if location_match:
                data['name'] = location_match.group(1).strip()
                data['location'] = location_match.group(2).strip()
            else:
                data['name'] = first_part
                data['location'] = "Vienna, Austria"

            data['phone'] = parts[1].strip()
            data['email'] = parts[2].strip()
        else:
            # Fallback parsing
            data['name'] = parts[0].strip() if len(parts) > 0 else "ALISON S. COHEN"
            data['phone'] = parts[1].strip() if len(parts) > 1 else ""
            data['email'] = parts[2].strip() if len(parts) > 2 else ""
            data['location'] = "Vienna, Austria"

    # Parse summary - handle both old and new formats
    summary_match = re.search(r'SUMMARY:\n(.+?)(?=\n[A-Z])', content, re.DOTALL)
    if summary_match:
        data['summary'] = summary_match.group(1).strip()
    else:
        # New format - look for Executive Summary
        exec_summary_match = re.search(r'Executive Summary\n(.+?)(?=\n\n[A-Z])', content, re.DOTALL)
        if exec_summary_match:
            data['summary'] = exec_summary_match.group(1).strip()
        else:
            data['summary'] = ""

    # Parse transition note
    transition_match = re.search(r'TRANSITION NOTE:\n(.+)', content)
    data['transition'] = transition_match.group(1) if transition_match else ""

    # Parse jobs
    data['jobs'] = []

    # Check if we have old format jobs
    if 'JOB TITLE:' in content:
        # Pattern for jobs with bullets (HR roles)
        job_with_bullets_pattern = r'JOB TITLE: (.+?)\nCOMPANY: (.+?)\nDATES: (.+?)\n((?:- .+\n?)+)'
        for match in re.finditer(job_with_bullets_pattern, content):
            title, company, dates, bullets = match.groups()
            bullet_list = [line.strip('- ').strip() for line in bullets.split('\n') if line.strip().startswith('-')]
            data['jobs'].append({
                'title': title,
                'company': company,
                'dates': dates,
                'bullets': bullet_list
            })

        # Pattern for jobs without bullets (counseling roles)
        job_without_bullets_pattern = r'JOB TITLE: (.+?)\nCOMPANY: (.+?)\nDATES: (.+?)(?=\n\n|\nJOB TITLE|\nMATERNITY|\nEARLY|\nCORE|\nEDUCATION|\nPERSONAL|$)'
        for match in re.finditer(job_without_bullets_pattern, content):
            title, company, dates = match.groups()
            # Skip if this job was already found with bullets
            already_exists = any(job['title'] == title.strip() and job['company'] == company.strip() for job in data['jobs'])
            if not already_exists:
                data['jobs'].append({
                    'title': title.strip(),
                    'company': company.strip(),
                    'dates': dates.strip(),
                    'bullets': []
                })
    else:
        # New format parsing
        # Parse Human Resources Experience section
        hr_section_match = re.search(r'Human Resources Experience\n\n(.+?)(?=School Counseling Experience)', content, re.DOTALL)
        if hr_section_match:
            hr_content = hr_section_match.group(1)
            # Split by double newlines to get individual jobs
            job_blocks = re.split(r'\n\n+', hr_content.strip())

            for block in job_blocks:
                if not block.strip():
                    continue
                lines = block.strip().split('\n')

                # First line should have dates and company
                if lines and re.search(r'[A-Z][a-z]+ \d{4}', lines[0]):
                    first_line = lines[0]
                    # Extract dates (everything up to multiple spaces before company)
                    date_match = re.match(r'([A-Z][a-z]+ \d{4}(?:\s*-\s*[A-Z][a-z]+ \d{4})?)\s{2,}(.+)', first_line)
                    if date_match:
                        dates = date_match.group(1).strip()
                        company = date_match.group(2).strip()

                        # Second line should be the title
                        title = lines[1].strip() if len(lines) > 1 else ""

                        # Remaining lines are bullets
                        bullet_list = []
                        for line in lines[2:]:
                            if line.strip().startswith('*'):
                                bullet_list.append(line.strip('* ').strip())

                        data['jobs'].append({
                            'title': title,
                            'company': company,
                            'dates': dates,
                            'bullets': bullet_list
                        })

        # Parse School Counseling Experience section
        school_section_match = re.search(r'School Counseling Experience\n\n(.+?)(?=Education)', content, re.DOTALL)
        if school_section_match:
            school_content = school_section_match.group(1)
            # Split by double newlines to get individual jobs
            job_blocks = re.split(r'\n\n+', school_content.strip())

            for block in job_blocks:
                if not block.strip():
                    continue
                lines = [line.strip() for line in block.strip().split('\n') if line.strip()]

                # Each block should have a date line, so find it
                for i, line in enumerate(lines):
                    # Look for date pattern at start of line - more flexible pattern
                    date_match = re.match(r'([A-Z][a-z]+ \d{4}(?:\s*-\s*[A-Z][a-z]+ \d{4})?)\s+(.+)', line)
                    if date_match:
                        dates = date_match.group(1).strip()
                        # Remove extra spaces and normalize
                        dates = re.sub(r'\s+', ' ', dates)

                        # Company is the second group
                        company_part = date_match.group(2).strip()

                        # Check if there's a next line for title
                        if i + 1 < len(lines):
                            title = lines[i + 1]
                        else:
                            # Special case for maternity leave
                            if "MATERNITY" in company_part.upper():
                                title = company_part
                                company_part = ""
                            else:
                                title = "School Counselor"  # Default if no next line

                        data['jobs'].append({
                            'title': title,
                            'company': company_part,
                            'dates': dates,
                            'bullets': []
                        })
                        break  # Only process one date per block



    # Parse competencies - not used in this resume format
    data['competencies'] = []

    # Parse education from text file
    data['education'] = []
    edu_match = re.search(r'EDUCATION:\n\n(.+?)(?=\n[A-Z][A-Z\s&]+:|$)', content, re.DOTALL)
    if edu_match:
        # Old format
        edu_text = edu_match.group(1).strip()
        lines = edu_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # New format: degree comes first
            if line and not line.startswith('Graduated') and not line.startswith('Pupil Personnel'):
                degree = line
                school = ""
                date = ""
                details = ""

                # Get school from next line
                if i + 1 < len(lines):
                    school = lines[i + 1].strip()

                # Get graduation date from next line
                if i + 2 < len(lines) and lines[i + 2].strip().startswith('Graduated'):
                    date = lines[i + 2].strip().replace('Graduated ', '')
                    i += 1  # Skip the date line

                # Check for additional details (like credentials)
                if i + 2 < len(lines) and lines[i + 2].strip() and not lines[i + 2].strip().startswith('Bachelor') and not lines[i + 2].strip().startswith('Master'):
                    details = lines[i + 2].strip()
                    i += 1  # Skip the details line

                data['education'].append({
                    'degree': degree,
                    'school': school,
                    'date': date,
                    'details': details if details else None
                })
                i += 2  # Skip school line
            else:
                i += 1
    else:
        # New format - simpler structure
        edu_section_match = re.search(r'Education\s*\n\n(.+?)(?=$)', content, re.DOTALL)
        if edu_section_match:
            edu_content = edu_section_match.group(1).strip()
            # Split by double newlines to get individual education entries
            edu_blocks = re.split(r'\n\n+', edu_content)

            for block in edu_blocks:
                if not block.strip():
                    continue
                lines = [line.strip() for line in block.split('\n') if line.strip()]

                if lines:
                    # First line should have date and school
                    first_line = lines[0]
                    date_match = re.match(r'([A-Z][a-z]+ \d{4})\s+(.+)', first_line)
                    if date_match:
                        date = date_match.group(1)
                        school = date_match.group(2)

                        # Next line should be degree
                        degree = lines[1] if len(lines) > 1 else ""

                        # Check for credentials on next line
                        details = lines[2] if len(lines) > 2 else None

                        data['education'].append({
                            'degree': degree,
                            'school': school,
                            'date': date,
                            'details': details
                        })

    # Parse licenses & certifications
    data['certifications'] = []
    cert_match = re.search(r'LICENSES & CERTIFICATIONS:\n\n(.+?)(?=\n[A-Z][A-Z\s&]+:|$)', content, re.DOTALL)
    if cert_match:
        cert_text = cert_match.group(1).strip()
        lines = cert_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # New format: certification name comes first
            if line and not line.startswith('Issued'):
                cert_name = line
                organization = ""
                date = ""

                # Get organization from next line
                if i + 1 < len(lines):
                    organization = lines[i + 1].strip()

                # Get issue date from next line
                if i + 2 < len(lines) and lines[i + 2].strip().startswith('Issued'):
                    date = lines[i + 2].strip().replace('Issued ', '')

                data['certifications'].append({
                    'name': cert_name,
                    'organization': organization,
                    'date': date
                })
                i += 3  # Skip organization and date lines
            else:
                i += 1
    # For new format, certifications are not included

    # Parse personal
    personal_match = re.search(r'PERSONAL:\n(.+)', content, re.DOTALL)
    data['personal'] = personal_match.group(1).strip() if personal_match else ""

    return data

def generate_html(data: Dict[str, Any]) -> str:
    """Generate HTML from parsed data"""

    # Generate jobs HTML
    jobs_html = ""
    austria_jobs = []
    california_jobs = []

    for job in data['jobs']:
        if 'Austria' in job['company']:
            austria_jobs.append(job)
        else:
            california_jobs.append(job)

    # Austria jobs first
    for job in austria_jobs:
        bullets_html = ""
        for bullet in job['bullets']:
            # Add <strong> tags for text before colons
            if ':' in bullet:
                parts = bullet.split(':', 1)
                formatted_bullet = f"<strong>{parts[0]}:</strong>{parts[1]}"
                bullets_html += f"                    <li>{formatted_bullet}</li>\n"
            else:
                bullets_html += f"                    <li>{bullet}</li>\n"

        jobs_html += f"""            <div class="job">
                <div class="job-header">
                    <div>
                        <span class="job-title">{job['title']}</span>
                        <span class="company">{job['company']}</span>
                    </div>
                    <span class="date">{job['dates']}</span>
                </div>
                <ul>
{bullets_html}                </ul>
            </div>

"""

    # Add California jobs
    for job in california_jobs:
        if job['bullets']:  # Jobs with bullet points
            bullets_html = ""
            for bullet in job['bullets']:
                # Add <strong> tags for text before colons
                if ':' in bullet:
                    parts = bullet.split(':', 1)
                    formatted_bullet = f"<strong>{parts[0]}:</strong>{parts[1]}"
                    bullets_html += f"                    <li>{formatted_bullet}</li>\n"
                else:
                    bullets_html += f"                    <li>{bullet}</li>\n"

            jobs_html += f"""            <div class="job">
                <div class="job-header">
                    <div>
                        <span class="job-title">{job['title']}</span>
                        <span class="company">{job['company']}</span>
                    </div>
                    <span class="date">{job['dates']}</span>
                </div>
                <ul>
{bullets_html}                </ul>
            </div>

"""
        else:  # Jobs without bullet points (like school counseling)
            jobs_html += f"""            <div class="job">
                <div class="job-header">
                    <div>
                        <span class="job-title">{job['title']}</span>
                        <span class="company">{job['company']}</span>
                    </div>
                    <span class="date">{job['dates']}</span>
                </div>
            </div>

"""


    # Generate competencies HTML - skip if empty
    comp_html = ""
    if data['competencies']:
        comp_icons = ["🤝", "🌍", "👥", "⚙️"]
        for i, comp in enumerate(data['competencies']):
            icon = comp_icons[i] if i < len(comp_icons) else "✓"
            comp_html += f"                    <div>{icon} {comp}</div>\n"

    # Generate education HTML from parsed data
    edu_html = ""
    for i, edu in enumerate(data['education']):
        edu_html += f"""            <div class="education-item">
                <div class="degree">{edu['degree']}</div>
                <div class="school">{edu['school']}</div>
                <div class="cert-date">{edu['date']}</div>"""
        if edu['details']:
            edu_html += f"""
                <div style="color: #666; font-size: 0.95em; margin-top: 5px;">{edu['details']}</div>"""
        edu_html += """
            </div>

"""

    # Generate certifications HTML
    cert_html = ""
    for cert in data['certifications']:
        cert_html += f"""            <div class="certification-item">
                <div class="cert-name">{cert['name']}</div>
                <div class="cert-org">{cert['organization']}</div>
                <div class="cert-date">Issued {cert['date']}</div>
            </div>

"""

    # Complete HTML template
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data['name']} - Resume</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>👩</text></svg>">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Crimson+Text:wght@400;600&display=swap');

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.45;
            color: #000000;
            font-weight: 400;
            max-width: 8.5in;
            margin: 0 auto;
            padding: 0.4in 0.5in 0.2in 0.5in;
            background: #ffffff;
            font-size: 11pt;
        }}

        .resume-container {{
            background: #ffffff;
            overflow: hidden;
            position: relative;
        }}

        header {{
            padding: 18pt 32pt 14pt 32pt;
            background: #ffffff;
            color: #000000;
            position: relative;
            border-bottom: 1.5pt solid #000000;
            margin-bottom: 14pt;
        }}

        .header-content {{
            display: flex;
            align-items: center;
            gap: 24pt;
        }}

        header img {{
            width: 100pt;
            height: 100pt;
            border-radius: 50%;
            object-fit: cover;
            border: 2pt solid #cccccc;
        }}

        .header-text {{
            flex: 1;
        }}

        h1 {{
            margin: 0 0 10pt 0;
            color: #000000;
            font-family: 'Crimson Text', serif;
            font-size: 22pt;
            font-weight: 700;
            letter-spacing: -0.8pt;
        }}

        .contact-info {{
            display: flex;
            flex-wrap: wrap;
            gap: 18pt;
            margin-top: 8pt;
        }}

        .contact-info span {{
            color: #555555;
            font-size: 11pt;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 5pt;
            padding: 3pt 0;
        }}

        .action-icons {{
            position: absolute;
            top: 20px;
            right: 20px;
            display: flex;
            gap: 12px;
            z-index: 1000;
        }}

        .action-icons a {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
            text-decoration: none;
            padding: 6px;
        }}

        .action-icons a:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}

        .action-icons img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
        }}

        .main-content {{
            padding: 0pt 32pt 0pt 32pt;
        }}

        h2 {{
            color: #000000;
            font-family: 'Crimson Text', serif;
            font-size: 14pt;
            font-weight: 700;
            margin: 16pt 0 10pt 0;
            padding-bottom: 5pt;
            border-bottom: 1.5pt solid #000000;
            letter-spacing: -0.3pt;
            position: relative;
        }}

        h2:first-child {{
            margin-top: 0;
        }}

        .summary {{
            background: #f7f7f7;
            padding: 14pt 16pt;
            margin-bottom: 18pt;
            border-left: 4pt solid #000000;
            border-top: 0.75pt solid #cccccc;
            border-bottom: 0.75pt solid #cccccc;
        }}

        .summary p {{
            margin: 0;
            font-size: 10.5pt;
            line-height: 1.5;
            color: #222222;
            font-weight: 400;
            font-style: italic;
        }}

        .job {{
            margin-bottom: 14pt;
            padding: 0;
            background: #ffffff;
        }}


        .job-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            flex-wrap: wrap;
            margin-bottom: 9pt;
        }}

        .job-title {{
            font-weight: 600;
            color: #000000;
            font-size: 12pt;
            font-family: 'Crimson Text', serif;
            line-height: 1.2;
        }}

        .company {{
            color: #555555;
            font-weight: 500;
            padding-left: 10pt;
            font-size: 10pt;
        }}

        .date {{
            color: #555555;
            font-size: 10pt;
            font-weight: 500;
            font-family: 'Inter', sans-serif;
        }}

        ul {{
            margin: 0 0 8pt 0;
            padding-left: 20pt;
        }}

        li {{
            margin-bottom: 5pt;
            line-height: 1.5;
            color: #333333;
            font-size: 10pt;
            font-weight: 400;
        }}

        li strong {{
            color: #000000;
            font-weight: 600;
        }}


        .education-item {{
            margin-bottom: 8pt;
            padding: 12pt 14pt;
            background: #f7f7f7;
            border: 1pt solid #cccccc;
            border-left: 4pt solid #000000;
        }}

        .education-item:last-child {{
            margin-bottom: 0pt;
        }}

        .degree {{
            font-weight: 600;
            color: #000000;
            font-size: 12pt;
            font-family: 'Crimson Text', serif;
            margin-bottom: 5pt;
            line-height: 1.2;
        }}

        .school {{
            color: #555555;
            font-weight: 600;
            margin-bottom: 4pt;
            text-transform: uppercase;
            font-size: 9pt;
            letter-spacing: 0.8pt;
        }}

        .certification-item {{
            margin-bottom: 15px;
            padding: 18px 20px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 3px solid #34495e;
        }}

        .cert-name {{
            font-weight: 500;
            color: #1a202c;
            font-size: 1.05em;
            margin-bottom: 5px;
        }}

        .cert-org {{
            color: #6b7280;
            font-weight: 400;
            margin-bottom: 3px;
        }}

        .cert-date {{
            color: #000000;
            font-size: 9pt;
            font-weight: 600;
        }}


        h3 {{
            color: #2c3e50;
            font-size: 1.1em;
            font-weight: 500;
            margin: 25px 0 15px 0;
        }}

        .page-break {{
            page-break-before: always;
            break-before: page;
        }}

        section {{
            margin-bottom: 18pt;
        }}

        section:last-child {{
            margin-bottom: 0pt;
        }}

        @media print {{
            .action-icons {{
                display: none !important;
            }}
        }}

    </style>
</head>
<body>
    <div class="resume-container">
        <div class="action-icons">
            <a href="resume.pdf" title="Download PDF" target="_blank">
                <img src="acrobat-logo.png" alt="Download PDF">
            </a>
            <a href="https://www.linkedin.com/in/alison-cohen-4229681a7" title="LinkedIn Profile" target="_blank">
                <img src="linkedin-logo.png" alt="LinkedIn">
            </a>
        </div>
        <header>
            <div class="header-content">
                <img src="alison.jpeg" alt="{data['name']}">
                <div class="header-text">
                    <h1>{data['name']}</h1>
                    <div class="contact-info">
                        <span>{data['location']}</span>
                        <span>{data['email']}</span>
                        <span>{data['phone']}</span>
                    </div>
                </div>
            </div>
        </header>

        <div class="main-content">
            <section class="summary">
                <h2>Professional Summary</h2>
                <p>{data['summary']}</p>
            </section>

            <section>
                <h2>Professional Experience</h2>

{jobs_html}            </section>

            <section>
                <h2>Education</h2>

{edu_html}            </section>


        </div>
    </div>
</body>
</html>"""

    return html_template

def generate_pdf():
    """Generate PDF from HTML using various methods"""

    methods = [
        # Try Chrome/Chromium headless first - macOS path
        ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--headless', '--disable-gpu', '--print-to-pdf=resume.pdf', '--no-margins', '--no-pdf-header-footer', 'index.html'],
        # Try standard PATH locations
        ['google-chrome', '--headless', '--disable-gpu', '--print-to-pdf=resume.pdf', '--no-margins', '--no-pdf-header-footer', 'index.html'],
        ['chromium-browser', '--headless', '--disable-gpu', '--print-to-pdf=resume.pdf', '--no-margins', '--no-pdf-header-footer', 'index.html'],
        ['chrome', '--headless', '--disable-gpu', '--print-to-pdf=resume.pdf', '--no-margins', '--no-pdf-header-footer', 'index.html'],
    ]

    for method in methods:
        try:
            result = subprocess.run(method, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ PDF generated using {method[0]}")
                return True
        except FileNotFoundError:
            continue

    print("⚠️  Could not generate PDF automatically.")
    print("   Please print index.html to PDF manually:")
    print("   1. Open index.html in Chrome/Safari/Firefox")
    print("   2. Press Ctrl+P (or Cmd+P)")
    print("   3. Choose 'Save as PDF'")
    print("   4. Save as 'resume.pdf'")
    return False

def main():
    """Main function to generate resume"""
    try:
        print("Reading resume data...")
        data = parse_resume_data('resume.txt')

        print("Generating HTML...")
        html = generate_html(data)

        print("Writing index.html...")
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html)

        print("✓ HTML resume generated successfully!")

        print("Generating PDF...")
        generate_pdf()

        print("✓ Resume generation complete!")
        print("Files created: index.html, resume.pdf (if successful)")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())