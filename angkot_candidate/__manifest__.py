# -*- coding: utf-8 -*-
{
    'name': "angkot_candidate",

    'summary': "Candidate onboarding document checklist with portal uploads and HR review",

    'description': """
Candidate document collection workflow for recruitment:
- Candidate uploads PDF/image documents from the portal
- Encharge officers monitor progress
- HR reviews and accepts/rejects submissions
    """,

    'author': "OpenAI",
    'website': "https://www.odoo.com",
    'category': 'Human Resources/Recruitment',
    'version': '18.0.1.0.0',

    'depends': ['hr_recruitment', 'portal'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/candidate_document_type_data.xml',
        'views/candidate_document_views.xml',
        'views/hr_candidate_views.xml',
        'views/res_users_views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
}
