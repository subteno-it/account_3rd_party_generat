# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 SISTHEO
#                  2010-2011 Christophe Chauvet <christophe.chauvet@syleam.fr>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, api, fields


class wizard_install_third_part_accounts(models.TransientModel):
    _name = 'wizard.install.third.part.accounts'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id.id)
    receivable_id = fields.Many2one('account.account', string='Account receivable', domain=[('type', '=', 'view')], required=True, default=lambda self: self._default_account_id('receivable'))
    payable_id = fields.Many2one('account.account', string='Account payable', domain=[('type', '=', 'view')], required=True, default=lambda self: self._default_account_id('payable'))

    @api.model
    def _default_account_id(self, account_type):
        account_type_id = self.env['account.account.type'].search([('code', '=', account_type)])
        account_id = self.env['account.account'].search([('type', '=', 'view'), ('user_type', 'in', account_type_id)])
        if account_id:
            return account_id.id
        return False

    @api.model
    def _set_property(self, field_name, account, company):
        """
        Set/Reset default properties
        """
        property_obj = self.env['ir.property']
        field = self.env['ir.model.fields'].search([('name', '=', field_name), ('model', '=', 'res.partner')])
        value = account and 'account.account,' + str(account.id) or False

        properties = property_obj.search([('field_id', '=', field.id), ('res_id', '=', False), ('company_id', '=', company.id)])
        if properties:
            properties.write({'value': value})
        else:
            property_obj.create({
                'name': field_name,
                'company_id': company.id,
                'fields_id': field.id,
                'value': value,
            })

    @api.multi
    def action_start_install(self):
        """
        Create the properties : specify default account (payable and receivable) for partners
        """
        self._set_property('property_account_receivable', self.receivable_id, self.company_id)
        self._set_property('property_account_payable', self.payable_id, self.company_id)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.actions.configuration.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
