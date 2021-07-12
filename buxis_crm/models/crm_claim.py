# -*- coding: utf-8 -*-

import datetime
import logging
from odoo import _, fields, models
from odoo import api
from odoo.exceptions import ValidationError
from lxml import etree

_logger=logging.getLogger(__name__)


class crm_claim_forma_contacto(models.Model):
    _name = 'crm.claim.forma_contacto'
    _description = 'Claim Forma de Contacto'

    name = fields.Char('Forma contacto', required=True)
    code = fields.Char('Código', required=True)


class crm_claim_tag(models.Model):
    _name = 'crm.claim.tag'
    _description = 'Claim Etiquetas'

    name = fields.Char('Nombre', required=True)


class crm_claim(models.Model):
    _inherit = 'crm.claim'
    _order = "priority desc, date desc"

    def assign_and_sendmail(self, obj, user_id, template, subscribe=False ):

        partner=self.env['res.users'].sudo().browse(user_id).partner_id
        if partner and user_id!=self.env.user.id:
            res=self.env['ir.model.data'].search_read([('model','=','mail.template'),('name','=',template)],['res_id'])
            template_id=res and res[0] and res[0]['res_id']
            template=self.env['mail.template'].browse(template_id)
            claim_id = obj.ids and isinstance(obj.ids, list) and obj.ids[0] or False
            if template and claim_id:
                template.sudo().send_mail(claim_id, force_send=True, raise_exception=False)
            else:
                email_from=self.env['mail.message'].sudo()._get_default_from()
                message = self.env['mail.message'].sudo().create({
                    'subject': _('Assigned to claim from %s: %s') % (obj.partner_id and obj.partner_id.name or _('Unknown'), obj.name or ''),
                    'body': _('<div><p>Hola %s,</p><p>Has sido asignado(a) a resolver el reclamo "%s" from: %s.</p></div>') % (partner.name, obj.name or '', obj.partner_id and obj.partner_id.name or _('Desconocido')),
                    'record_name': obj.name,
                    'email_from': email_from,
                    'reply_to': email_from,
                    'model': 'crm.claim',
                    'res_id': obj.id,
                    'no_auto_thread': True,
                })
                partner.with_context(auto_delete=True).sudo()._notify(message, force_send=True, user_signature=True)

        if partner and subscribe:
            self.message_subscribe([partner.id])

    def sendmail(self, obj, user_ids, template, subscribe=False ):

        # Obtener template y reclamo
        res=self.env['ir.model.data'].search_read([('model','=','mail.template'),('name','=',template)],['res_id'])
        template_id=res and res[0] and res[0]['res_id'] or False
        obj_template=template_id and self.env['mail.template'].browse(template_id) or False
        claim_id = obj.ids and isinstance(obj.ids, list) and obj.ids[0] or False

        # Si se encuentra template, se asume que el template es un único mail con envío a múltiples destinatarios
        if obj_template and claim_id:
            obj_template.sudo().send_mail(claim_id, force_send=True, raise_exception=False)

        else:
            # Se itera para hacer un envío por usuario, solamente si no hay template definido
            for user_id in user_ids:
                partner=self.env['res.users'].sudo().browse(user_id).partner_id
                if partner and user_id!=self.env.user.id:
                    email_from=self.env['mail.message'].sudo()._get_default_from()
                    message = self.env['mail.message'].sudo().create({
                        'subject': _('New claim from %s: %s') % (obj.partner_id and obj.partner_id.name or _('Unknown'), obj.name or ''),
                        'body': _('<div><p>Hola %s,</p><p>Hay un nuevo reclamo "%s" from: %s.</p></div>') % (partner.name, obj.name or '', obj.partner_id and obj.partner_id.name or _('Desconocido')),
                        'record_name': obj.name,
                        'email_from': email_from,
                        'reply_to': email_from,
                        'model': 'crm.claim',
                        'res_id': obj.id,
                        'no_auto_thread': True,
                    })
                    partner.with_context(auto_delete=True).sudo()._notify(message, force_send=True, user_signature=True)

        # En caso que se indique Suscribir a los notificados
        if subscribe:
            for user_id in user_ids:
                partner=self.env['res.users'].sudo().browse(user_id).partner_id
                if partner :
                    self.message_subscribe([partner.id])


    partner_id= fields.Many2one(tracking=True)
    partner_phone= fields.Char(related='partner_id.phone', string=u"Teléfono", readonly=True, store=False, compute_sudo=True)
    partner_mobile = fields.Char(related='partner_id.mobile', string=u"Celular", readonly=True, store=False, compute_sudo=True)
    partner_parent_id = fields.Many2one(related='partner_id.parent_id', string=u"Empresa", store=True)
    forma_contacto_id= fields.Many2one('crm.claim.forma_contacto', string="Forma Contacto") #, required=True)
    tag_ids= fields.Many2many('crm.claim.tag', string="Etiquetas")
    causas= fields.Char(string="Causas principales")
    fecha_cierre= fields.Date(string="Fecha de cierre")
    tiempo_efectivo= fields.Float(string="Esfuerzo (hs)", compute='compute_tiempo_efectivo', store=True)
    email_from= fields.Text(string="Mail")
    can_edit = fields.Boolean(compute='_check_can_edit', string="Can Edit")
    select_user_ids = fields.Many2many('res.users', compute="_get_select_user_ids", string="Users to select from")
    select_users_cnt = fields.Integer(string='Select users cnt', compute="_get_select_user_ids" )
    select_user_ids_txt = fields.Text(compute="_get_select_user_ids", string="Users to select from")
    select_category_ids= fields.Many2many('crm.claim.category', compute="_get_select_category_ids", string="Categories to select from")
    #team_id= fields.Many2one('crm.team', 'Equipo de atención', oldname='section_id', select=True, tracking=True, help="Responsible sales team. Define Responsible user and Email account for mail gateway.", required=True)
    team_id = fields.Many2one('crm.team', 'Equipo de atención', tracking=True,
                              help="Responsible sales team. Define Responsible user and Email account for mail gateway.",
                              required=True)
    name=fields.Char('Claim Subject', required=True, tracking=True, size=100)

    stage_id = fields.Many2one('crm.claim.stage', 'Stage', tracking=True, domain=[])
    time_ids = fields.One2many('crm.claim.time', 'claim_id', 'Tiempos')
    notificado = fields.Boolean('Contacto notificado')

    @api.model
    def default_get(self, fields):
        _logger.warning(u'=====================================> 1')
        res = super(crm_claim, self).default_get(fields)

        _logger.warning(u'=====================================> 2')

        res['select_category_ids']=self._get_default_category_ids()
        res['team_id'] = self._get_default_team()

        if not res['team_id']:
            res['user_id'] = False

        _logger.warning(u'=====================================> 2.2')

        #if self.env.user.sale_team_id.name == 'Clientes':
        #    res['partner_id'] = self.env.user.partner_id.id
        
        return res

    @api.model
    def create(self, vals):
        _logger.warning(u'=====================================> 3')
        
        #interfaz_user=self.env.user.has_group('buxis_crm.Interfaz')
        #self_no_create=self.with_context(mail_create_nosubscribe=interfaz_user)
        #obj = super(crm_claim, self_no_create).create(vals)
        obj = super(crm_claim, self).create(vals)

        if 'user_id' in vals and vals.get('user_id'):
            self.assign_and_sendmail( obj, vals.get('user_id'), 'email_template_aviso_asignacion_reclamo', subscribe=True)

        # Subscripción automática del contacto
        if obj.partner_id:
            obj.message_subscribe([obj.partner_id.id])

        _logger.warning(u'=====================================> 3.3')

        return obj

    def write(self, vals):
        #_logger.warning(u'=====================================> 4')
        if 'partner_id' in vals:
            partner = self.env['res.partner'].search([('id', '=', vals['partner_id'])], limit=1)
            vals['partner_phone'] = partner.phone
            vals['partner_parent_id'] = partner.parent_id
            vals['partner_mobile'] = partner.mobile

            if partner.email:
                vals['email_from'] = "\n".join(partner.email.split(","))

        if 'team_id' in vals:
            stage_id= self.env['crm.claim.stage'].search([], limit=1, order='sequence')
            vals['stage_id'] = stage_id and stage_id.id or False

        stage = self.env['crm.claim.stage'].search([('name', '=', 'Finalizado')], limit=1)

        #Se completa fecha de cierre en el caso de que se finalice con esa fecha en blanco
        if stage and vals.get('fecha_cierre', True) and vals.get('stage_id', False) == stage.id:
            vals['fecha_cierre'] = datetime.datetime.now()

        # Cierre automático en caso de completar fecha de cierre
        if stage and vals.get('fecha_cierre', False) and vals.get('stage_id', False) != stage.id and not all([row.stage_id.id == stage.id for row in self]):
            vals['stage_id'] = stage.id

        res= super(crm_claim, self).write(vals)

        # Add new responsible as follower, and Notify
        if 'user_id' in vals and vals.get('user_id'):
            self.assign_and_sendmail( self, vals.get('user_id'), 'email_template_aviso_asignacion_reclamo', subscribe=True )

        # Subscripción automática del contacto
        for claim in self:
            if claim.partner_id and claim.partner_id not in [flw.partner_id for flw in claim.message_follower_ids]:
                claim.message_subscribe([claim.partner_id.id])

        return res

    def _check_can_edit(self):
        _logger.warning(u'=====================================> 5')
        for claim in self:
            claim.can_edit= claim.team_id and len([member for member in claim.team_id.member_ids if member==self.env.user])>0 or False

    @api.onchange('partner_id')
    def onchange_partner_id(self):
    #def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        #_logger.warning(u'=====================================> Se ejecuta onchange')

        vals = {'partner_parent_id': False, 'partner_mobile': False, 'partner_phone': False, 'email_form': False, 'tipo_doc_contacto': False, 'nro_doc_contacto': False}
        doms = {}
        partner_id = self.partner_id

        if not partner_id:
            return {'value': vals}
        partner = self.env['res.partner'].browse(partner_id.id)
        vals['partner_parent_id'] = partner.parent_id
        vals['partner_mobile'] = partner.mobile
        vals['partner_phone'] = partner.phone
        if partner.email:
            vals['email_from'] = "\n".join(partner.email.split(","))
        else:
            vals['email_from'] = False

        return {'value': vals }

    @api.depends('team_id')
    def _get_select_user_ids(self):
        _logger.warning(u'=====================================> 9')
        for claim in self:
            # definir lista como la lista de miembros del equipo
            if claim.team_id:
                select_user_ids = claim.team_id.member_ids
            # Si no está definido el equipo, lista vacía
            else:
                select_user_ids = []
            s = ','.join([str(usr.partner_id.id) for usr in select_user_ids if usr.partner_id])
            _logger.warning(u'Lista ===============================> ' + s)
            user_ids = select_user_ids and select_user_ids.ids or []
            _logger.warning(u'=====================================> 9.1')
            _logger.warning(u'=====================================> 9.2')
            s = ','.join([str(usr) for usr in user_ids if usr])
            _logger.warning(u'user_ids =====================================> 9.2.1 '+ s)
            claim.select_user_ids = [(6, 0, user_ids or [])]
            _logger.warning(u'=====================================> 9.2')
            claim.select_user_ids_txt = ",".join([str(usr.partner_id.id) for usr in select_user_ids if usr.partner_id])
            if claim.user_id and claim.user_id.id not in user_ids:
                claim.user_id = False
            claim.select_users_cnt=len(claim.select_user_ids)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        _logger.warning(u'=====================================> 10')
        context = self._context or {}

        if context.get('apply_team_filter'):
            filter = ['|', ('message_partner_ids', 'in', [self.env.user.partner_id.id]), '|', ('team_id.user_id', '=', self.env.user.id), ('create_uid', '=', self.env.uid)]

            if self.env.user.partner_id.parent_id:
                filter = ['|', ('partner_parent_id', '=', self.env.user.partner_id.parent_id.id)] + filter

            #access_team_ids=[]

            #if self.env.user.multi_team_ids:#self.env.user.sale_team_id:
            #    access_team_ids+=self.env.user.multi_team_ids.mapped('access_team_ids').ids

            #if access_team_ids:
            #    filter=['|',('team_id','in',access_team_ids)]+filter
            if args:
                args=['&']+args+filter
            else:
                args += filter
        return super(crm_claim, self).search(args, offset, limit, order, count=count)

    #@api.depends('categ_id', 'create_date')
    #def _get_select_team_ids(self):
    #    #_logger.warning(u'=====================================> 11')

    #    for claim in self:
    #        if isinstance(claim.id, (int,long)):
    #            # Si la reclamación está creada, tomar como base el equipo asignado a la reclamación
    #            base_teams = claim.team_id
    #            delegate_teams = claim.team_id

    #            # Ver a que equipos se puede delegar desde los equipos base
    #            for team in base_teams:
    #                for restrict in team.delegate_restrict_ids:
    #                    delegate_teams |= restrict.to_team_id
    #            claim.select_team_ids = [(6, 0, delegate_teams.ids or [-1])]

    #        else:
    #            claim.select_team_ids = [(6, 0, self._get_default_teams() or [-1])]


    def _get_select_category_ids(self):
        _logger.warning(u'=====================================> 12')
        self.select_category_ids = self._get_default_category_ids()

    @api.model
    def _get_default_category_ids(self):
        _logger.warning(u'=====================================> 13')
        category_ids = []

        category_ids = self.env['crm.claim.category'].search([]).ids
        return [(6, 0, category_ids or [-1])]

    @api.model
    def _get_default_team(self):
        _logger.warning(u'=====================================> 14')
        # Si la reclamación aún no está creada, tomar como base los equipos a los que pertenece el usuario
        #team_id = self.env.user.sale_team_id | self.env['crm.team'].search([('user_id', '=', self.env.user.id)])
        team_id = self.env.user.sale_team_id.id | False

#        # Ver a que equipos se puede delegar desde los equipos base
#        #for team in delegate_teams:
#        #    for restrict in team.delegate_restrict_ids:
#        #        delegate_teams |= restrict.to_team_id
        return team_id

    @api.depends('time_ids','time_ids.time')
    def compute_tiempo_efectivo(self):
        #_logger.warning(u'=====================================> 16')
        for claim in self:
            claim.tiempo_efectivo = sum(claim.time_ids.mapped('time'))

    #@api.model
    #def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #    #_logger.warning(u'=====================================> 17')
    #    res = super(crm_claim, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    #    if view_type=='form' and self.user_has_groups('buxis_crm.sin_acceso_contactos'): ## grupo o grupos separados por coma, sin espacios
    #        doc = etree.XML(res['arch'])
    #        for node in doc.xpath("//field[@name='partner_id']"):
    #            node.set('options', "{'no_open': true, 'no_create_edit': True}")
    #        res['arch'] = etree.tostring(doc)
    #    return res

    def get_email_from(self):
        #_logger.warning(u'=====================================> 18')
        self.ensure_one()
        if self.email_from:
            return self.email_from.split('<')[-1].split('>')[0]
        return False

    @api.returns('self', lambda value: value.id)
    def message_post(self, body='', subject=None, message_type='notification',
                     subtype=None, parent_id=False, attachments=None,
                     content_subtype='html', **kwargs):
        body_aux=body
        if self.ids and len(self.ids)==1 and not kwargs.get('subtype_id') \
           and not self.partner_id and self._context.get('default_model')=='crm.claim' \
           and self._context.get('default_res_id') and not self._context.get('default_is_log'):
            email_from = self.env['mail.message']._get_default_from()
            email_to = kwargs.pop('email_to', None) or self.get_email_from()
            if email_from and email_to:
                author = self.env['mail.message']._get_default_author()
                signature = ""
                if author and author.user_ids and author.user_ids[0].signature:
                    signature = author.user_ids[0].signature
                elif author:
                    signature = "<p>-- <br/>%s</p>" % author.name
                if signature:
                    #body += "<br/>%s" % (signature.strip())
                    body += signature.strip()
                ctx = dict(self._context or {}, mail_post_autofollow=False)
                for key in ctx.keys():
                    if key.startswith('default_'):
                        ctx.pop(key, None)
                self.env['mail.mail'].sudo().with_context(ctx).create({
                        'model': 'crm.claim',
                        'res_id': None, # private message
                        'subject': subject or 'Re: %s' % (self.name),
                        'body_html': body,
                        'parent_id': parent_id,
                        'email_from': email_from,
                        'email_to': email_to,
                        'attachment_ids': [(6, 0, kwargs.get('attachment_ids', []))]
                }).send()
        return super(crm_claim, self).message_post(body=body_aux, subject=subject, message_type=message_type,
                 subtype=subtype, parent_id=parent_id, attachments=attachments,
                 content_subtype=content_subtype, **kwargs)

# Tiempo efectivo dedicado a la resolución
class crm_claim_time(models.Model):
    _name='crm.claim.time'
    _description = 'Claim Tiempo'

    claim_id = fields.Many2one('crm.claim', 'Reclamación', required=True, ondelete='cascade')
    team_id = fields.Many2one('crm.team', 'Equipo')
    stage_id= fields.Many2one('crm.claim.stage', 'Etapa', related='claim_id.stage_id', store=True)
    categ_id = fields.Many2one('crm.claim.category', 'Categoría', related='claim_id.categ_id', store=True)
    partner_id = fields.Many2one('res.partner', 'Contacto', related='claim_id.partner_id', store=True)
    priority = fields.Selection( related='claim_id.priority', string='Prioridad', store=True)
    can_edit_time = fields.Boolean('Puede editar?', compute='compute_can_edit_time')
    user_id = fields.Many2one('res.users', 'Usuario', default=lambda s: s.env.user.id)
    date = fields.Date('Fecha', required=True, default=fields.Date.context_today)
    time = fields.Float('Horas', required=True)
    notes = fields.Text('Notas')

    @api.constrains('date')
    def check_date(self):
        if self.date and fields.Date.from_string(self.date).year<1900:
            raise ValidationError('El año debe ser mayor o igual a 1900...')

    @api.model
    def default_get(self, fields_list):
        res=super(crm_claim_time, self).default_get(fields_list)
        res['team_id']=self.env.user.sale_team_id and self.env.user.sale_team_id.id or False
        return res

    @api.depends('user_id')
    def compute_can_edit_time(self):
        for row in self:
            row.can_edit_time = not (row.user_id and row.user_id!=self.env.user)

    @api.onchange('claim_id')
    def onchange_claim(self):
        return {'domain':{'user_id':[('id','=',self.env.user.id)]}}

    @api.onchange('user_id')
    def onchange_user(self):
        if self.user_id:
            self.team_id = self.user_id.sale_team_id
        else:
            self.team_id=False
        return self._get_select_user_ids()

    @api.constrains('user_id', 'team_id')
    def check_user_team(self):
        if not self.user_id and not self.team_id:
            raise ValidationError('Debe seleccionar un usuario o un equipo...')

class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def get_mail_values(self, res_ids):
        results = super(MailComposer, self).get_mail_values(res_ids)
        if self.model == 'crm.claim' and not self.is_log:
            for res_id, mail_values in results.items():
                record = self.env['crm.claim'].browse(res_id)
                if not record.partner_id and record.get_email_from():
                    mail_values.update({ 'email_to': record.get_email_from() })
        return results
