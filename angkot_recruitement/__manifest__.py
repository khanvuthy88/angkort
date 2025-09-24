# -*- coding: utf-8 -*-
{
    'name': "Angkot Recruitment Enhancement",

    'summary': "Enhanced recruitment module with job portal features for Next.js integration",

    'description': """
Angkot Recruitment Enhancement
=============================

This module extends the standard Odoo hr_recruitment functionality to provide enhanced features
suitable for modern job portal integration, particularly with Next.js frontend applications.

Key Features:
-------------
* Enhanced job posting with additional fields (job type, experience level, education level)
* Salary management with flexible salary types (range, fixed, negotiable)
* Job categories and tags for better job classification
* Featured and urgent job flags for job portal highlighting
* Remote work support
* Application deadline and external application URL support
* Company information fields (logo, website, phone, description)
* Job responsibilities, requirements, and benefits management
* Computed fields for better frontend integration

Technical Enhancements:
-----------------------
* Job category model for functional job classification
* Computed salary display fields
* Job tags processing for skill-based filtering
* Enhanced job properties for custom job attributes
* Better integration with Odoo's industry classification

This module is designed to work seamlessly with modern job portal frontends,
providing all necessary fields and functionality for a comprehensive job board experience.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr_recruitment'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/hr_job_category_data.xml',
        'views/hr_job_category_views.xml',
        'views/hr_job_views.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

