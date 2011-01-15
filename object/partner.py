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

from osv import osv
from osv import fields
from tools.translate import _
from modificators import Modificator


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _user_company(self, cr, uid, context):
        """
        Return the company id for the connected user
        """
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.id

    def _customer_type(self, cr, uid, context=None):
        """
        Search all configuration on the company for the customer
        """
        if context is None:
            context = {}
        args = [
            ('company_id', '=', self._user_company(cr, uid, context=context)),
            ('partner_type', '=', 'customer'),
        ]
        acc_type_obj = self.pool.get('account.generator.type')
        type_ids = acc_type_obj.search(cr, uid, args, context=context)
        res = []
        if type_ids:
            for t in acc_type_obj.browse(cr, uid, type_ids, context=context):
                res.append((t.code, t.name))
        return res

    def _supplier_type(self, cr, uid, context=None):
        """
        Search all configuration on the company for the supplier
        """
        if context is None:
            context = {}
        args = [
            ('company_id', '=', self._user_company(cr, uid, context=context)),
            ('partner_type', '=', 'supplier'),
        ]
        acc_type_obj = self.pool.get('account.generator.type')
        type_ids = acc_type_obj.search(cr, uid, args, context=context)
        res = []
        if type_ids:
            for t in acc_type_obj.browse(cr, uid, type_ids, context=context):
                res.append((t.code, t.name))
        return res

    def _partner_default_value(self, cr, uid, field='customer', context=None):
        """
        Search the default context
        """
        if context is None:
            context = {}
        args = [
            ('company_id', '=', self._user_company(cr, uid, context=context)),
            ('partner_type', '=', field),
            ('default_value', '=', True),
        ]
        acc_type_obj = self.pool.get('account.generator.type')
        type_ids = acc_type_obj.search(cr, uid, args, context=context)
        if not type_ids:
            return False
        elif len(type_ids) > 1:
            context = self.pool.get('res.users').context_get(cr, uid)
            raise osv.except_osv(_('Error'), _('Too many default value define for %s type') % _(field))

        t = acc_type_obj.browse(cr, uid, type_ids[0], context=context)
        return t.code

    def _customer_default_value(self, cr, uid, context=None):
        return self._partner_default_value(cr, uid, 'customer', context=context)

    def _supplier_default_value(self, cr, uid, context=None):
        return self._partner_default_value(cr, uid, 'supplier', context=context)

    _columns = {
        'customer_type': fields.selection(_customer_type, 'Customer type'),
        'supplier_type': fields.selection(_supplier_type, 'Supplier type'),
    }

    _defaults = {
        'customer': lambda *a: 0,   # Do not compute account number if not necessary
        'customer_type': _customer_default_value,
        'supplier_type': _supplier_default_value,
    }

    #----------------------------------------------------------
    #   Private methods C&S
    #----------------------------------------------------------
    def _get_compute_account_number(self, cr, uid, partner, seq_patern):
        """Compute account code based on partner and sequence

        :param partner: current partner
        :type  partner: osv.osv.browse
        :param seq_patern: the sequence witch will be use as a pattern/template
        :type  seq_patern: str

        :return: the account code/number
        :rtype: str
        """
        if seq_patern.find('{') >= 0:
            prefix = seq_patern[:seq_patern.index('{')]
            suffix = seq_patern[seq_patern.index('}') + 1:]
            body = seq_patern[len(prefix) + 1:][:len(seq_patern) - len(prefix) - len(suffix) - 2]

            ar_args = body.split('|')
            # partner field is always first
            if isinstance(partner, dict):
                partner_value = partner.get(ar_args[0], '')
            else:
                partner_value = getattr(partner, ar_args[0])

            if partner_value:
                # Modificators
                mdf = Modificator(partner_value)
                for i in range(1, len(ar_args)):
                    mdf_funct = getattr(mdf, ar_args[i])
                    partner_value = mdf_funct()
                    mdf.setval(partner_value)
            account_number = "%s%s%s" % (prefix or '', partner_value or '', suffix or '')
        else:
            account_number = seq_patern

        # is there internal sequence ?
        pos_iseq = account_number.find('#')
        if pos_iseq >= 0:
            nzf = account_number.count('#')
            rootpart = account_number[:pos_iseq]
            # verify if root of this number is existing
            arAcc_ids = self.pool.get('account.account').search(cr, uid, [('code', 'like', rootpart)])
            cnt = len(arAcc_ids)
            next_inc = ("%0d" % int(cnt + 1)).zfill(nzf)
            account_number = account_number.replace('#' * nzf, next_inc)

        return account_number

    def _create_account_from_template(self, cr, uid, acc_value=None, acc_company=None, acc_tmpl=None, acc_parent=False, context=None):
        """
        Compose a new account the template define on the company

        :param acc_tmpt: The account template configuration
        :type  acc_tmpl: osv.osv.browse
        :param acc_parent: The parent account to link the new account
        :type  acc_parent: integer
        :return: New account configuration
        :rtype: dict
        """
        new_account = {
            'name': acc_value.get('acc_name','Unknown'),
            'code': acc_value.get('acc_number','CODE'),
            'parent_id': acc_parent,
            'company_id': acc_company,
            'user_type': acc_tmpl.user_type.id,
            'reconcile': True,
            'check_history': True,
            'currency_id': acc_tmpl.currency_id and acc_tmpl.currency_id.id or False,
            'active': True,
            'type': acc_tmpl.type,
            'tax_ids': [(6, 0, [x.id for x in acc_tmpl.tax_ids])],
        }
        return new_account

    def _create_new_account(self, cr, uid, type=None, data=None, context=None):
        """
        Create the a new account base on a company configuration

        :param type: Type of the partner (customer or supplier)
        :type  type: str
        :param data: dict of create value
        :type  data: dict
        :return: the id of the new account
        :rtype: integer
        """
        if context is None:
            context = {}

        if data is None:
            data = {}

        company_id = data.get('company_id',  self._user_company(cr, uid, context=context))
        args = [
            ('company_id', '=', company_id),
            ('partner_type', '=', type),
        ]

        if type == 'customer':
            args.append(('code', '=', data.get('customer_type')))
        elif type == 'supplier':
            args.append(('code', '=', data.get('supplier_type')))

        acc_type_obj = self.pool.get('account.generator.type')
        type_ids = acc_type_obj.search(cr, uid, args, context=context)
        if type_ids and len(type_ids) == 1:
            gen = acc_type_obj.browse(cr, uid, type_ids[0], context=context)
            gen_dict = {
                'acc_name': data.get('name', 'Unknown'),
                'acc_number': self._get_compute_account_number(cr, uid, data, gen.ir_sequence_id.prefix),
            }
            new_acc = self._create_account_from_template(cr, uid, acc_value=gen_dict, acc_company=company_id,
                            acc_tmpl=gen.account_template_id, acc_parent=gen.account_parent_id.id, context=context)
            return self.pool.get('account.account').create(cr, uid, new_acc, context=context)
        return False

    def create(self, cr, uid, data, context=None):
        """
        When create a customer and supplier, we create the account code
        and affect it to this partner
        """
        if context is None:
            context = {}

        if not context.get('skip_account_customer', False):
            acc_obj = self.pool.get('account.account')
            if data.get('customer', 0) == 1:
                account = acc_obj.read(cr, uid, data.get('property_account_receivable'), ['type'], context=context)
                if account['type'] == 'view':
                    data['property_account_receivable'] = self._create_new_account(cr, uid, 'customer', data, context=context)
            elif data.get('supplier', 0) == 1:
                account = acc_obj.read(cr, uid, data.get('property_account_payable'), ['type'], context=context)
                if account['type'] == 'view':
                    data['property_account_payable'] = self._create_new_account(cr, uid, 'supplier', data, context=context)
        return super(res_partner, self).create(cr, uid, data, context)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}

        print 'vals ', vals
        # Compute account code if customer case is check
        # or if the customer account change
        if vals.get('customer', 0) == 1 or vals.get('property_account_receivable'):
            pass

        # Compute account code if supplier case is check
        # or if the customer account change
        if vals.get('supplier', 0) == 1 or vals.get('property_account_payable'):
            pass

        return super(res_partner, self).write(cr, uid, ids, vals, context=context)

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
