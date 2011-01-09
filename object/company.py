# -*- coding: utf-8 -*-
##############################################################################
#
#    account_3rd_party_generat module for OpenERP, Module to generate account number
#                                                  for customer and supplier
#    Copyright (C) 2010-2011 SYLEAM (<http://www.syleam.fr/>)
#              Christophe CHAUVET <christophe.chauvet@syleam.fr>
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

from osv import osv
from osv import fields


class AccountGeneratorType(osv.osv):
    _name = 'account.generator.type'
    _description = 'Account generator customize per type'

    _columns = {
        'partner_type': fields.selection([('customer', 'Customer'), ('supplier', 'Supplier')], 'Type', required=True, help='Select the type of partner'),
        'name': fields.char('Name', size=64, required=True, help='Name appear on the partner form'),
        'default_value': fields.boolean('Default value', help='Default value for this type'),
        'ir_sequence_id': fields.many2one('ir.sequence', 'Sequence', help='Sequence use to generate the code'),
        'account_template_id': fields.many2one('account.account.template', 'Account template', help='Account use to create the new one'),
        'account_parent_id': fields.many2one('account.account', 'Parent account', help='Select the parent account of the new account générate'),
        'company_id': fields.many2one('res.company', 'Company', help='Company where this configuraiton is apply', required=True),
    }

    _defaults = {
        'default_value': lambda *a: False,
        'ir_sequence_id': lambda *a: False,
        'account_template_id': lambda *a: False,
        'account_parent_id': lambda *a: False,
    }

AccountGeneratorType()


class ResCompany(osv.osv):
    _inherit = 'res.company'

    _columns = {
        'account_generator_type_ids': fields.one2many('account.generator.type', 'company_id', 'Account generator type'),
    }


ResCompany()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
