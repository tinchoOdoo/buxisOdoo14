# -*- coding: utf-8 -*-


from odoo import fields, models, api
from hashlib import sha1
from datetime import datetime
import base64

from odoo.exceptions import Warning, UserError, ValidationError
from odoo.tools.translate import _

class res_partner_tipo_doc(models.Model):
    _name='res.partner.tipo_doc'

    country_id= fields.Many2one('res.country', string= "País", required=True)
    name= fields.Char(string= "Nombre", required=True)
    code= fields.Char(string= "Code", required=True)


class res_country_city(models.Model):
    _name='res.country.city'

    country_id = fields.Many2one('res.country', string="País", required=True, default=lambda self: self.env['res.country'].search([('code','=','UY')]),)
    state_id= fields.Many2one('res.country.state', string="Departamento")
    name= fields.Char(string= "Nombre", required=True)

class res_partner(models.Model):
    _inherit='res.partner'

    nombre = fields.Char(string="Primer Nombre")
    nombre2 = fields.Char(string="Segundo Nombre")
    apellido = fields.Char(string="Primer Apellido")
    apellido2 = fields.Char(string="Segundo Apellido")
    pais_documento_id = fields.Many2one('res.country', string=u"País del documento", default=lambda self: self.env['res.country'].search([('code','=','UY')]),)
    tipo_documento_id = fields.Many2one('res.partner.tipo_doc', string ="Tipo de documento")
    tipo_doc_code = fields.Char(related='tipo_documento_id.code', string='Tipo doc code')
    nro_documento = fields.Char(string=u"Número documento")
    clave = fields.Char(string=u"Clave")

    #@api.multi
    #@api.depends('country_id')
    #def _get_country_code(self):
    #    for partner in self:
    #        partner.country_code=partner.country_id.code

    #@api.multi
    #@api.depends('email')
    #def _get_mail_wrapped(self):
    #    for partner in self:
    #        if partner.email:
    #            partner.email_text3="\n".join(partner.email.split(","))

    #@api.multi
    #@api.depends('city_id')
    #def _get_city_name(self):
    #    for partner in self:
    #        if partner.ciudad_id:
    #            partner.city=partner.ciudad_id.name

    @api.onchange('nombre', 'apellido', 'nombre2', 'apellido2')
    def onchange_nombre(self):
        if self.company_type == 'person' and self.nombre != False and self.apellido != False:
            self.nombre = self.nombre.upper()
            nombres = self.nombre.strip()
            self.apellido = self.apellido.upper()
            apellidos = self.apellido.strip()

            if self.nombre2 != False:
                self.nombre2 = self.nombre2.upper()
                nombres = nombres + " " + self.nombre2.strip()

            if self.apellido2 != False:
                self.apellido2 = self.apellido2.upper()
                apellidos = apellidos + " " + self.apellido2.strip()

            self.name = "%s, %s" % (apellidos, nombres)

    @api.model
    def check_cedula(self, nro_cedula):

        def get_ci_digit(number):
            number = number.strip()[:-1]
            pattern = [2, 9, 8, 7, 6, 3, 4]
            number_list = [int(n) for n in number]
            _r = abs((sum([k * v for k, v in zip(number_list, pattern)]) % 10) - 10)
            if _r == 10:
                return 0
            return _r

        if nro_cedula:
            number = nro_cedula.strip().replace(' ', '').replace('.', '').replace('-', '').zfill(8)

            if not number.isdigit():
                raise ValidationError(u"Cédula %s incorrecta, debe contener solo dígitos" % (number,))
            if len(number) > 8:
                raise ValidationError(u"Cédula %s incorrecta, verificar la cantidad de dígitos" % (number,))
            if number[-1] != str(get_ci_digit(number)):
                raise ValidationError(u"Cédula %s incorrecta, dígito verificador incorrecto" % (number,))

    @api.model
    def check_dni(self, nro_dni):
        if nro_dni and not nro_dni.isdigit():
            raise ValidationError(u"DNI %s incorrecto, debe contener solo dígitos" % (nro_dni,))

    @api.onchange('tipo_documento_id', 'nro_documento')
    def onchange_nro_documento(self):
        if self.tipo_documento_id.code == 'CI' and self.tipo_documento_id.country_id.code == 'UY':
            self.check_cedula(self.nro_documento)
        if self.tipo_documento_id.code == 'DNI' and self.tipo_documento_id.country_id.code == 'AR':
            self.check_dni(self.nro_documento)

    @api.constrains('tipo_documento_id', 'nro_documento')
    def _check_nro_documento(self):
        if self.tipo_documento_id.code == 'CI' and self.tipo_documento_id.country_id.code == 'UY':
            self.check_cedula(self.nro_documento)
        if self.tipo_documento_id.code == 'DNI' and self.tipo_documento_id.country_id.code == 'AR':
            self.check_dni(self.nro_documento)

    @api.onchange('pais_documento_id')
    def onchange_pais_tipo_doc(self):
        self.tipo_documento_id = False

    @api.multi
    def write(self, vals):
        #Valido al Guardar el nro documento
        if 'nro_documento' in vals or 'tipo_documento_id' in vals:
            tipo = ''
            nrodoc=''
            country_id = 0
            #Nro_documento
            if 'nro_documento' in vals:
                nrodoc = vals['nro_documento']
            else:
                if self.nro_documento:
                    nrodoc=self.nro_documento
            #Tipo
            if 'tipo_documento_id' in vals:
                res = self.env['res.partner.tipo_doc'].search([('id', '=', vals['tipo_documento_id'])])
                if res:
                    tipo = res[0]['code']
                    country_id = res[0]['country_id']
            else:
                if self.tipo_documento_id:
                    tipo = self.tipo_documento_id.code
                    country_id = self.tipo_documento_id.country_id
            #236 Uruguay
            if tipo == 'CI' and country_id == 236:
                self.check_cedula(nrodoc)
            #11 Argentina
            if tipo == 'DNI' and country_id == 11:
                self.check_dni(nrodoc)

        return super(res_partner, self).write(vals)