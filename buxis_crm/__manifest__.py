# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'BUXIS CRM',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Leads, Opportunities, Activities',
    'description': """Modificaciones a Odoo para Buxis
                    """,
    'author': 'Martin Ibarra',
    'depends': [
        'base_setup',
        'crm',
        'crm_claim',
        'base',
        'calendar',
        'sales_team',
    ],
    'data': [
        'views/res_partner_view.xml',
        'views/crm_claim_view.xml',

        'data/crm_claim_data.xml',
    ],
    'demo': [],
    'test': [],
    'css': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
