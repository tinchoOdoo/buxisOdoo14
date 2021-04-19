# -*- coding: utf-8 -*-


from odoo import models, _
from odoo import api
from email.utils import formataddr
from odoo.exceptions import UserError


class Message(models.Model):
    _inherit='mail.message'

    @api.model
    def _get_default_author(self):
        return self.author_id  #Deja vacío el autor para que utilice el mail_from del template

    @api.model
    def _get_default_from(self):
        outgoing_mail_alias=self.env['ir.config_parameter'].get_param('usuario.mail.salida', default='crm')

        if self.env.user.alias_name and self.env.user.alias_domain:
            return formataddr((self.env.user.company_id.name, '%s@buxis.com' % outgoing_mail_alias))
        elif self.env.user.email:
            return formataddr((self.env.user.company_id.name, '%s@buxis.com' % outgoing_mail_alias))
        raise UserError(_("Unable to send email, please configure the sender's email address or alias."))
