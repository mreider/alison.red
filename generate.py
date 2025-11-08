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
        header_match = re.search(r'(.+?)\s+(.+?)\s+✦\s+(.+?)\s+✦\s+(.+)', content.split('\n')[0])
        if header_match:
            data['name'] = header_match.group(1).strip()
            data['location'] = header_match.group(2).strip()
            data['phone'] = header_match.group(3).strip()
            data['email'] = header_match.group(4).strip()
        else:
            # Fallback parsing
            first_line = content.split('\n')[0]
            parts = first_line.split('✦')
            data['name'] = parts[0].strip() if len(parts) > 0 else "Unknown"
            data['phone'] = parts[1].strip() if len(parts) > 1 else ""
            data['email'] = parts[2].strip() if len(parts) > 2 else ""
            data['location'] = "Vienna, Austria"  # Default from context

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
                    # Extract dates (everything up to first uppercase company name)
                    date_match = re.match(r'([A-Z][a-z]+ \d{4}[^A-Z]*)', first_line)
                    if date_match:
                        dates = date_match.group(1).strip()
                        # Company is the rest of the first line
                        company = first_line[len(dates):].strip()

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



    # Parse competencies
    comp_match = re.search(r'CORE COMPETENCIES:\n(.+?)(?=\n[A-Z])', content, re.DOTALL)
    if comp_match:
        comp_text = comp_match.group(1).strip()
        data['competencies'] = [line.strip('• ').strip() for line in comp_text.split('\n') if line.strip().startswith('•')]
    else:
        # For new format, create default competencies from experience
        data['competencies'] = [
            "Strategic HR Leadership & Business Partnership",
            "Global Operations & Cultural Integration",
            "Employee Relations & Workplace Investigations",
            "Process Development & Change Management"
        ]

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


    # Generate competencies HTML
    comp_html = ""
    for comp in data['competencies']:
        comp_html += f"                    <div>• {comp}</div>\n"

    # Generate education HTML from parsed data
    edu_html = ""
    for edu in data['education']:
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
            margin: 40px 0 20px 0;
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
            margin-bottom: 30px;
            border-left: 3px solid #34495e;
        }}

        .summary p {{
            margin: 0;
            font-size: 1.05em;
            line-height: 1.7;
            color: #2c3e50;
        }}

        .job {{
            margin-bottom: 25px;
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
            border-left: 3px solid #34495e;
        }}

        .education-item {{
            margin-bottom: 15px;
            padding: 18px 20px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 3px solid #34495e;
        }}

        .degree {{
            font-weight: 500;
            color: #1a202c;
            font-size: 1.05em;
            margin-bottom: 5px;
        }}

        .school {{
            color: #6b7280;
            font-weight: 400;
            margin-bottom: 3px;
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
            color: #9ca3af;
            font-size: 0.9em;
            font-weight: 400;
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
            margin-bottom: 35px;
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
                padding: 8px 20px 8px 20px !important;
                border-bottom: 1px solid #eaeaea;
            }}
            .header-content {{
                gap: 8px !important;
                align-items: center !important;
            }}
            header img {{
                width: 35px !important;
                height: 35px !important;
            }}
            h1 {{
                font-size: 1.05em !important;
                margin: 0 !important;
                letter-spacing: -0.2px;
            }}
            .contact-info {{
                gap: 6px !important;
                margin-top: 2px !important;
            }}
            .contact-info span {{
                font-size: 0.65em !important;
            }}
            .main-content {{
                padding: 12px 20px;
            }}
            h2 {{
                font-size: 1em;
                margin: 12px 0 6px 0;
                padding-bottom: 3px;
            }}
            h2:first-child {{
                margin-top: 0;
            }}
            .summary {{
                padding: 10px;
                margin-bottom: 12px;
                border-left: 2px solid #34495e;
            }}
            .summary p {{
                font-size: 1em;
                line-height: 1.4;
                margin: 0;
            }}
            .job {{
                margin-bottom: 12px;
                padding-bottom: 0;
                page-break-inside: avoid;
            }}
            .job-header {{
                margin-bottom: 6px;
            }}
            .job-title {{
                font-size: 1em;
            }}
            .company {{
                font-size: 0.9em;
            }}
            .date {{
                font-size: 0.85em;
            }}
            ul {{
                padding-left: 18px;
                margin: 0 0 8px 0;
            }}
            li {{
                margin-bottom: 3px;
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
                padding: 8px 12px !important;
                font-size: 0.85em !important;
                border-left: 2px solid #34495e;
            }}
            .education-item {{
                margin-bottom: 8px;
                padding: 12px 15px;
                page-break-inside: avoid;
                border-left: 2px solid #34495e;
            }}
            .degree {{
                font-size: 0.95em;
                margin-bottom: 3px;
            }}
            .school {{
                font-size: 0.85em;
                margin-bottom: 3px;
            }}
            .cert-date {{
                font-size: 0.8em;
            }}
            section {{
                margin-bottom: 10px;
            }}
            section:last-child {{
                margin-top: 8px !important;
            }}
            h3 {{
                font-size: 0.9em;
                margin: 10px 0 6px 0;
            }}
            .page-break {{
                page-break-before: always !important;
                break-before: page !important;
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