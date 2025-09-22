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

    # Parse basic info
    data['name'] = re.search(r'NAME: (.+)', content).group(1)
    data['phone'] = re.search(r'PHONE: (.+)', content).group(1)
    data['email'] = re.search(r'EMAIL: (.+)', content).group(1)
    data['location'] = re.search(r'LOCATION: (.+)', content).group(1)

    # Parse summary
    summary_match = re.search(r'SUMMARY:\n(.+?)(?=\n[A-Z])', content, re.DOTALL)
    data['summary'] = summary_match.group(1).strip()

    # Parse transition note
    transition_match = re.search(r'TRANSITION NOTE:\n(.+)', content)
    data['transition'] = transition_match.group(1) if transition_match else ""

    # Parse jobs
    data['jobs'] = []
    job_pattern = r'JOB TITLE: (.+?)\nCOMPANY: (.+?)\nDATES: (.+?)\n((?:- .+\n?)+)'
    for match in re.finditer(job_pattern, content):
        title, company, dates, bullets = match.groups()
        bullet_list = [line.strip('- ').strip() for line in bullets.split('\n') if line.strip().startswith('-')]
        data['jobs'].append({
            'title': title,
            'company': company,
            'dates': dates,
            'bullets': bullet_list
        })

    # Parse early career
    early_career_match = re.search(r'EARLY CAREER:\n(.+?)(?=\n[A-Z])', content, re.DOTALL)
    if early_career_match:
        early_career_text = early_career_match.group(1).strip()
        data['early_career'] = [line.strip() for line in early_career_text.split('\n') if line.strip()]
    else:
        data['early_career'] = []

    # Parse competencies
    comp_match = re.search(r'CORE COMPETENCIES:\n(.+?)(?=\n[A-Z])', content, re.DOTALL)
    if comp_match:
        comp_text = comp_match.group(1).strip()
        data['competencies'] = [line.strip('• ').strip() for line in comp_text.split('\n') if line.strip().startswith('•')]
    else:
        data['competencies'] = []

    # Parse education from text file
    data['education'] = []
    edu_match = re.search(r'EDUCATION:\n\n(.+?)(?=\n[A-Z][A-Z]+:|$)', content, re.DOTALL)
    if edu_match:
        edu_text = edu_match.group(1).strip()
        # Pattern to match: "August 2000         SAN JOSE STATE UNIVERSITY"
        # followed by degree and credential lines
        lines = edu_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r'^[A-Za-z]+ \d{4}\s+[A-Z]', line):  # Date and school line
                parts = re.split(r'\s{2,}', line)  # Split on multiple spaces
                if len(parts) >= 2:
                    date = parts[0]
                    school = parts[1]
                    # Get degree from next line
                    degree = ""
                    details = ""
                    if i + 1 < len(lines):
                        degree = lines[i + 1].strip()
                    if i + 2 < len(lines) and lines[i + 2].strip() and not re.match(r'^[A-Za-z]+ \d{4}\s+[A-Z]', lines[i + 2]):
                        details = lines[i + 2].strip()
                        i += 1  # Skip the details line

                    data['education'].append({
                        'degree': degree,
                        'school': f"{school}, {date.split()[-1]}",  # School, Year format
                        'details': details if details else None
                    })
                    i += 2  # Skip degree line
                else:
                    i += 1
            else:
                i += 1

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
                        <span class="company">| {job['company']}</span>
                    </div>
                    <span class="date">{job['dates']}</span>
                </div>
                <ul>
{bullets_html}                </ul>
            </div>

"""

    # Add transition callout
    if data['transition']:
        jobs_html += f"""            <div class="transition-callout">
                <div class="transition-title">🌍 Career transition and international move</div>
                <div class="transition-subtitle">{data['transition']}</div>
            </div>

"""

    # California jobs
    for job in california_jobs:
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
                        <span class="company">| {job['company']}</span>
                    </div>
                    <span class="date">{job['dates']}</span>
                </div>
                <ul>
{bullets_html}                </ul>
            </div>

"""

    # Early career section
    if data['early_career']:
        jobs_html += """            <h3>Early Career Experience</h3>
            <ul style="list-style-type: none; padding-left: 0;">
"""
        for career in data['early_career']:
            # Parse format: "Title, Company (dates)"
            parts = career.split(' (')
            if len(parts) == 2:
                title_company = parts[0]
                dates = parts[1].rstrip(')')
                if ', ' in title_company:
                    title_parts = title_company.split(', ', 1)
                    title = title_parts[0]
                    company = title_parts[1]
                    jobs_html += f'                <li style="font-weight: 400; margin-bottom: 5px;"><span style="font-weight: 500;">{title}</span>, {company} ({dates})</li>\n'
        jobs_html += "            </ul>\n"

    # Generate competencies HTML
    comp_html = ""
    for comp in data['competencies']:
        comp_html += f"                    <div>• {comp}</div>\n"

    # Generate education HTML from parsed data
    edu_html = ""
    for edu in data['education']:
        edu_html += f"""            <div class="education-item">
                <div class="degree">{edu['degree']}</div>
                <div class="school">{edu['school']}</div>"""
        if edu['details']:
            edu_html += f"""
                <div style="color: #666; font-size: 0.95em;">{edu['details']}</div>"""
        edu_html += """
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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.7;
            color: #2c3e50;
            font-weight: 400;
            max-width: 920px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #fcfcfc;
        }}

        .resume-container {{
            background: #ffffff;
            box-shadow: 0 2px 20px rgba(0,0,0,0.06), 0 8px 40px rgba(0,0,0,0.03);
            border: 1px solid #f0f0f0;
            overflow: hidden;
            position: relative;
        }}

        header {{
            padding: 60px 50px 50px 50px;
            background: #ffffff;
            border-bottom: 1px solid #eaeaea;
        }}

        .header-content {{
            display: flex;
            align-items: center;
            gap: 40px;
        }}

        header img {{
            width: 110px;
            height: 110px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #f8f9fa;
        }}

        .header-text {{
            flex: 1;
        }}

        h1 {{
            margin: 0 0 15px 0;
            color: #1a202c;
            font-size: 2.4em;
            font-weight: 300;
            letter-spacing: -0.8px;
        }}

        .contact-info {{
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            margin-top: 15px;
        }}

        .contact-info span {{
            color: #6b7280;
            font-size: 0.95em;
            font-weight: 400;
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
            padding: 50px;
        }}

        h2 {{
            color: #1a202c;
            font-size: 1.3em;
            font-weight: 500;
            margin: 45px 0 25px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid #eaeaea;
            letter-spacing: -0.2px;
        }}

        h2:first-child {{
            margin-top: 0;
        }}

        .summary {{
            background: #f8f9fa;
            padding: 25px;
            margin-bottom: 35px;
            border-left: 3px solid #34495e;
        }}

        .summary p {{
            margin: 0;
            font-size: 1.05em;
            line-height: 1.7;
            color: #2c3e50;
        }}

        .job {{
            margin-bottom: 30px;
        }}

        .job-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }}

        .job-title {{
            font-weight: 500;
            color: #1a202c;
            font-size: 1.1em;
        }}

        .company {{
            color: #6b7280;
            font-weight: 400;
            padding-left: 8px;
        }}

        .date {{
            color: #9ca3af;
            font-size: 0.9em;
            font-weight: 400;
        }}

        ul {{
            margin: 0;
            padding-left: 22px;
        }}

        li {{
            margin-bottom: 8px;
            line-height: 1.65;
            color: #4a5568;
        }}

        li strong {{
            color: #2c3e50;
            font-weight: 500;
        }}

        .competencies {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 20px;
        }}

        .competencies div {{
            color: #2c3e50;
            font-weight: 400;
            padding: 16px 20px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 3px solid #e9ecef;
        }}

        .education-item {{
            margin-bottom: 18px;
        }}

        .degree {{
            font-weight: 500;
            color: #1a202c;
            font-size: 1.05em;
        }}

        .school {{
            color: #6b7280;
            font-weight: 400;
            margin-top: 3px;
        }}

        .transition-callout {{
            text-align: center;
            margin: 35px 0;
            padding: 25px;
            background: #f8f9fa;
            border: 1px solid #eaeaea;
            position: relative;
        }}

        .transition-title {{
            font-size: 1.1em;
            font-weight: 500;
            margin-bottom: 8px;
            color: #2c3e50;
        }}

        .transition-subtitle {{
            font-size: 0.95em;
            color: #6b7280;
        }}

        h3 {{
            color: #2c3e50;
            font-size: 1.1em;
            font-weight: 500;
            margin: 25px 0 15px 0;
        }}

        section {{
            margin-bottom: 30px;
        }}

        section:last-child {{
            margin-top: 25px;
        }}

        @media print {{
            .action-icons {{
                display: none !important;
            }}
            body {{
                background: white;
                padding: 0;
                margin: 0;
                font-size: 13px;
                line-height: 1.4;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            .resume-container {{
                box-shadow: none;
                border: none;
                max-width: none;
            }}
            header {{
                padding: 5px 25px 5px 25px !important;
            }}
            .header-content {{
                gap: 10px !important;
                align-items: center !important;
            }}
            header img {{
                width: 40px !important;
                height: 40px !important;
            }}
            h1 {{
                font-size: 1.1em !important;
                margin: 0 !important;
                letter-spacing: -0.2px;
            }}
            .contact-info {{
                gap: 8px !important;
                margin-top: 2px !important;
            }}
            .contact-info span {{
                font-size: 0.7em !important;
            }}
            .main-content {{
                padding: 20px 25px;
            }}
            h2 {{
                font-size: 1.1em;
                margin: 20px 0 12px 0;
                padding-bottom: 4px;
            }}
            h2:first-child {{
                margin-top: 0;
            }}
            .summary {{
                padding: 15px;
                margin-bottom: 20px;
            }}
            .summary p {{
                font-size: 0.95em;
                line-height: 1.4;
            }}
            .job {{
                margin-bottom: 18px;
                padding-bottom: 15px;
                page-break-inside: avoid;
            }}
            .job-header {{
                margin-bottom: 8px;
            }}
            .job-title {{
                font-size: 1em;
            }}
            .date {{
                font-size: 0.8em;
            }}
            ul {{
                padding-left: 18px;
            }}
            li {{
                margin-bottom: 4px;
                line-height: 1.3;
                font-size: 0.9em;
            }}
            .competencies {{
                display: grid !important;
                grid-template-columns: 1fr 1fr !important;
                gap: 6px !important;
                margin-top: 8px !important;
            }}
            .competencies div {{
                padding: 6px 10px !important;
                font-size: 0.8em !important;
            }}
            .education-item {{
                margin-bottom: 10px;
                page-break-inside: avoid;
            }}
            .degree {{
                font-size: 0.95em;
            }}
            .school {{
                font-size: 0.85em;
            }}
            .transition-callout {{
                margin: 15px 0;
                padding: 12px;
                page-break-inside: avoid;
            }}
            .transition-title {{
                font-size: 0.95em;
                margin-bottom: 4px;
            }}
            .transition-subtitle {{
                font-size: 0.85em;
            }}
            .transition-context {{
                font-size: 0.8em;
                margin-top: 3px;
            }}
            section {{
                margin-bottom: 15px;
            }}
            section:last-child {{
                margin-top: 15px !important;
            }}
            h3 {{
                font-size: 1em;
                margin: 15px 0 10px 0;
            }}
            /* Personal section styling for print */
            section:last-child p {{
                font-size: 0.8em !important;
            }}
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 20px 15px;
            }}
            header {{
                padding: 40px 30px 35px 30px;
            }}
            .header-content {{
                flex-direction: column;
                text-align: center;
                gap: 25px;
            }}
            header img {{
                width: 95px;
                height: 95px;
            }}
            h1 {{
                font-size: 2em;
            }}
            .contact-info {{
                justify-content: center;
                gap: 18px;
            }}
            .main-content {{
                padding: 35px 30px;
            }}
            .job-header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 6px;
            }}
            .competencies {{
                grid-template-columns: 1fr;
            }}
        }}

        @media (max-width: 480px) {{
            header {{
                padding: 30px 25px;
            }}
            .main-content {{
                padding: 30px 25px;
            }}
            h1 {{
                font-size: 1.8em;
            }}
            .contact-info {{
                flex-direction: column;
                gap: 12px;
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
                        <span>📍 {data['location']}</span>
                        <span>✉️ {data['email']}</span>
                        <span>📱 {data['phone']}</span>
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
                <h2>Core Competencies</h2>
                <div class="competencies">
{comp_html}                </div>
            </section>

            <section>
                <h2>Education & Certifications</h2>

{edu_html}            </section>

            <section>
                <h2>Personal</h2>
                <p style="color: #6b7280; font-size: 0.95em; line-height: 1.6;">{data['personal']}</p>
            </section>
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