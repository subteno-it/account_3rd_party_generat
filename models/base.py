# -*- coding: utf-8 -*-
##############################################################################
#
#    account_3rd_party_generat module for OpenERP, Module to generate account number
#                                                  for customer and supplier
#    Copyright (C) 2010-2011 SYLEAM (<http://www.syleam.fr/>)
#              Christophe CHAUVET <christophe.chauvet@syleam.fr>
#              Sylvain Garancher <sylvain.garancher@syleam.fr>
#
#    This file is a part of account_3rd_party_generat
#
#    account_3rd_party_generat is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    account_3rd_party_generat is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, api, fields, exceptions
from openerp.tools.translate import _
from modificators import Modificator


class AccountGeneratorType(models.Model):
    _name = 'account.generator.type'
    _description = 'Account generator customize per type'

    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
    ], string='Type', required=True, help='Select the type of partner')
    code = fields.Char(string='Code', size=16, required=True, help='Code use to store value in the database')
    name = fields.Char(string='Name', size=64, required=True, translate=True, help='Name appear on the partner form')
    default_value = fields.Boolean(string='Default value', help='Default value for this type')
    lock_partner_name = fields.Boolean(string='Lock partner name', help='Partner\'s name is locked when his account has at least one account move')
    ir_sequence_id = fields.Many2one('ir.sequence', string='Sequence', help='Sequence use to generate the code')
    account_template_id = fields.Many2one('account.account.template', string='Account template', help='Account use to create the new one')
    account_parent_id = fields.Many2one('account.account', string='Parent account', help='Select the parent account of the new account generate')
    account_reference_id = fields.Many2one('account.account', string='Account reference', help='If no sequence define, this account reference is choose all the time')
    company_id = fields.Many2one('res.company', string='Company', help='Company where this configuration is apply', required=True)
    field_select = fields.Selection([
        ('none', ''),
        ('name', 'name'),
        ('ref', 'ref'),
    ], string='Select Field', help='Select the field where the code be generate')
    code_pre = fields.Char(string='Code Prefix', size=64)
    code_suf = fields.Char(string='Code Suffix', size=64)
    code_seq_id = fields.Many2one('ir.sequence', string='Sequence', domain=[('code', '=', 'res.partner')])

    @api.constrains('partner_type', 'default_value')
    def check_default_values_count(self):
        if len(self.search([
                ('partner_type', '=', 'customer'),
                ('default_value', '=', True),
                ('company_id', '=', self.company_id.id),
            ])) > 1 or len(self.search([
                ('partner_type', '=', 'supplier'),
                ('default_value', '=', True),
                ('company_id', '=', self.company_id.id),
            ])) > 1:
            raise exceptions.Warning(_('Error'), _('The default value must be unique per partner type !'))

    @api.onchange('partner_type')
    @api.multi
    def onchange_partner_type(self):
        """
        When partner type change, we must change domain for:
        - account_template_id
        - account_parent_id
        """
        if not self.partner_type:
            domain = {
                'account_template_id': [('id', '=', 0)],
                'account_parent_id': [('id', '=', 0)],
                'account_reference_id': [('id', '=', 0)],
            }
        elif self.partner_type == 'customer':
            domain = {
                'account_template_id': [('type', '=', 'receivable')],
                'account_parent_id': [('type', 'in', ('view', 'receivable'))],
                'account_reference_id': [('type', '=', 'receivable')],
            }
        elif self.partner_type == 'supplier':
            domain = {
                'account_template_id': [('type', '=', 'payable')],
                'account_parent_id': [('type', 'in', ('view', 'payable'))],
                'account_reference_id': [('type', '=', 'payable')],
            }

        return {'value': {}, 'domain': domain}


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_generator_type_ids = fields.One2many('account.generator.type', 'company_id', string='Account generator type')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_type = fields.Many2one('account.generator.type', string='Customer type', domain=[('partner_type', '=', 'customer')], company_dependent=True, help='Customer account type')
    supplier_type = fields.Many2one('account.generator.type', string='Supplier type', domain=[('partner_type', '=', 'supplier')], company_dependent=True, help='Supplier account type')
    force_create_customer_account = fields.Boolean('Force create account', help='If set, OpenERP will generate a new acount for this customer')
    force_create_supplier_account = fields.Boolean('Force create account', help='If set, OpenERP will generate a new acount for this supplier')

    _defaults = {
        'customer': False,
    }

    @api.model
    def default_get(self, fields_list):
        values = super(ResPartner, self).default_get(fields_list)
        values.update(
            customer_type=self.env['account.generator.type'].search([
                ('partner_type', '=', 'customer'),
                ('default_value', '=', True),
                ('company_id', '=', self.env.user.company_id.id),
            ]).id,
            supplier_type=self.env['account.generator.type'].search([
                ('partner_type', '=', 'supplier'),
                ('default_value', '=', True),
                ('company_id', '=', self.env.user.company_id.id),
            ]).id,
        )
        return values

    @api.model
    def _get_compute_account_number(self, partner, sequence):
        """Compute account code based on partner and sequence

        :param partner: current partner
        :type  partner: osv.osv.browse
        :param sequence: the sequence witch will be use as a pattern/template
        :type  sequence: osv.osv.browse

        :return: the account code/number
        :rtype: str
        """
        seq_patern = sequence.prefix
        if seq_patern.find('{') >= 0:
            prefix = seq_patern[:seq_patern.index('{')]
            suffix = seq_patern[seq_patern.index('}') + 1:]
            body = seq_patern[len(prefix) + 1:][:len(seq_patern) - len(prefix) - len(suffix) - 2]
            ar_args = body.split('|')

            # partner field is always first
            partner_value = getattr(partner, ar_args[0])
            if partner_value:
                # Modificators
                mdf = Modificator(partner_value)
                for i in range(1, len(ar_args)):
                    mdf_funct = getattr(mdf, ar_args[i])
                    partner_value = mdf_funct()
                    mdf.setval(partner_value)

            account_number = '%s%s%s' % (prefix or '', partner_value or '', suffix or '')
            # is there internal sequence ?
            pos_iseq = account_number.find('#')
            if pos_iseq >= 0:
                rootpart = account_number[:pos_iseq]
                nzf = sequence.padding - len(rootpart)
                # verify if root of this number is existing
                next_inc = ('%d' % sequence.number_next).zfill(nzf)
                account_number = account_number.replace('#', next_inc)
                # Increments sequence number
                sequence.number_next = sequence.number_next + sequence.number_increment
        else:
            seq_obj = self.env['ir.sequence']
            account_number = seq_obj.next_by_id(sequence.id)

        return account_number

    @api.model
    def _create_account_from_template(self, name, number, template, parent):
        """
        Compose a new account the template define on the company

        :param acc_tmpt: The account template configuration
        :type  acc_tmpl: osv.osv.browse
        :param acc_parent: The parent account to link the new account
        :type  acc_parent: integer
        :return: New account configuration
        :rtype: dict
        """
        return {
            'name': name,
            'code': number,
            'parent_id': parent.id,
            'user_type': template.user_type.id,
            'reconcile': True,
            'currency_id': template.currency_id and template.currency_id.id or False,
            'active': True,
            'type': template.type,
            'tax_ids': [(6, 0, [x.id for x in template.tax_ids])],
        }

    @api.model
    def _create_new_account(self, account_generator, partner):
        """
        Create the a new account base on a company configuration

        :param type: Type of the partner (customer or supplier)
        :type  type: str
        :param data: dict of create value
        :type  data: dict
        :return: the id of the new account
        :rtype: integer
        """
        if account_generator.ir_sequence_id:
            account_data = self._create_account_from_template(
                partner.name,
                self._get_compute_account_number(partner, account_generator.ir_sequence_id),
                account_generator.account_template_id,
                account_generator.account_parent_id,
            )
            return self.env['account.account'].create(account_data)
        else:
            return account_generator.account_reference_id

    @api.model
    def create(self, vals):
        """
        When create a customer and supplier, we create the account code
        and affect it to this partner
        """
        res = super(ResPartner, self).create(vals)
        res.write({'force_create_customer_account': True, 'force_create_supplier_account': True})
        return res

    @api.multi
    def write(self, vals):
        ir_property_obj = self.env['ir.property']
        model_fields_obj = self.env['ir.model.fields']

        # Check if name is allowed to be modified
        if 'name' in vals:
            account_move_line_obj = self.env['account.move.line']
            for partner in self:
                if partner.customer and self.customer_type.lock_partner_name and account_move_line_obj.search([('account_id', '=', partner.property_account_receivable.id)]):
                    raise exceptions.Warning(_('Error'), _('You cannot change partner\'s name when his account has moves'))
                if partner.supplier and self.supplier_type.lock_partner_name and account_move_line_obj.search([('account_id', '=', partner.property_account_payable.id)]):
                    raise exceptions.Warning(_('Error'), _('You cannot change partner\'s name when his account has moves'))

        # Call super for standard behaviour
        res = super(ResPartner, self).write(vals)

        # Search customer and supplier fields, to be able to check if there is a default value while searching on ir.property
        customer_field = model_fields_obj.search([('model', '=', 'res.partner'), ('name', '=', 'property_account_receivable')])[0]
        supplier_field = model_fields_obj.search([('model', '=', 'res.partner'), ('name', '=', 'property_account_payable')])[0]

        for partner in self:
            vals = {}

            if partner.customer and partner.customer_type and partner.force_create_customer_account:
                # Create a new account only if the partner is using the default account
                ir_properties = ir_property_obj.search([('fields_id', '=', customer_field.id), ('res_id', '=', False)])
                if ir_properties and ir_properties[0].value_reference == 'account.account,%d' % partner.property_account_receivable.id:
                    vals.update(
                        property_account_receivable=self._create_new_account(partner.customer_type, partner),
                        force_create_customer_account=False,
                    )

            if partner.supplier and partner.supplier_type and partner.force_create_supplier_account:
                # Create a new account only if the partner is using the default account
                ir_properties = ir_property_obj.search([('fields_id', '=', supplier_field.id), ('res_id', '=', False)])
                if ir_properties and ir_properties[0].value_reference == 'account.account,%d' % partner.property_account_payable.id:
                    vals.update(
                        property_account_payable=self._create_new_account(partner.supplier_type, partner),
                        force_create_supplier_account=False,
                    )

            super(ResPartner, partner).write(vals)

        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
