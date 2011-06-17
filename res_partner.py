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

    def _get_company_id(self, cr, uid, data=None, context=None):
        """
        Return the company_id for data, or connected user if not found in data
        """
        if context is None:
            context = {}

        # Retrieve company_id
        fields = self.pool.get('res.partner').fields_get(cr, uid, ['company_id'], context=context)
        if 'company_id' in fields:
            company_id = getattr(data, 'company_id', False)
            if company_id:
                company_id = company_id.id
        else:
            company_id = self._user_company(cr, uid, context=context)

        return company_id

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

    def _partner_default_code(self, cr, uid, type=None, context=None):
        """
        Create the a new code base on a company configuration

        :param type: Type of the partner (customer or supplier)
        :type  type: str
        :param data: dict of create value
        :type  data: dict
        :return: the new code
        :type: char
        """
        if context is None:
            context = {}

        if data is None:
            data = {}

        company_id = getattr(data, 'company_id', False) or  self._user_company(cr, uid, context=context)
        args = [
            ('company_id', '=', company_id),
            ('partner_type', '=', type),
        ]

        if type == 'customer':
            args.append(('code', '=', data.customer_type))
        elif type == 'supplier':
            args.append(('code', '=', data.supplier_type))

        acc_type_obj = self.pool.get('account.generator.type')
        type_ids = acc_type_obj.search(cr, uid, args, context=context)
        if type_ids and len(type_ids) == 1:
            gen = acc_type_obj.browse(cr, uid, type_ids[0], context=context)
            if gen.ir_sequence_id:
                return self.pool.get('account.account').create(cr, uid, new_acc, context=context)
            else:
                return gen.account_reference_id and gen.account_reference_id.id or False
        return False


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
    def _get_compute_account_number(self, cr, uid, partner, sequence):
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
            account_number = "%s%s%s" % (prefix or '', partner_value or '', suffix or '')
            # is there internal sequence ?
            pos_iseq = account_number.find('#')
            if pos_iseq >= 0:
                rootpart = account_number[:pos_iseq]
                nzf = sequence.padding - len(rootpart)
                # verify if root of this number is existing
                next_inc = ("%d" % sequence.number_next).zfill(nzf)
                account_number = account_number.replace('#', next_inc)

                # Increments sequence number
                self.pool.get('ir.sequence').write(cr, uid, [sequence.id], {'number_next': sequence.number_next + sequence.number_increment})
        else:
            seq_obj = self.pool.get('ir.sequence')
            account_number = seq_obj.get_id(cr, uid, sequence.id)

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

    def _get_acc_type_id(self, cr, uid, company_id, type=None, data=None, context=None):
        """
        Retrieve account id
        Returns account id or False
        """
        if context is None:
            context = {}

        if data is None:
            data = {}

        # Set args to select account type
        args = [
            ('company_id', '=', company_id),
            ('partner_type', '=', type),
        ]
        if type == 'customer':
            args.append(('code', '=', data.customer_type))
        elif type == 'supplier':
            args.append(('code', '=', data.supplier_type))

        # Retrieve account type id
        acc_type_obj = self.pool.get('account.generator.type')
        type_ids = acc_type_obj.search(cr, uid, args, context=context)

        # If only one ID is found, return it
        if type_ids and len(type_ids) == 1:
            return type_ids[0]

        # No ID found or more than one, return False (error)
        return False


    def _create_new_account(self, cr, uid, company_id, type=None, data=None, context=None):
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

        type_id = self._get_acc_type_id(cr, uid, company_id, type, data, context=context)
        if type_id:
            acc_type_obj = self.pool.get('account.generator.type')
            gen = acc_type_obj.browse(cr, uid, type_id, context=context)
            if gen.ir_sequence_id:
                gen_dict = {
                    'acc_name': data.name,
                    'acc_number': self._get_compute_account_number(cr, uid, data, gen.ir_sequence_id),
                }
                new_acc = self._create_account_from_template(cr, uid, acc_value=gen_dict, acc_company=company_id,
                                acc_tmpl=gen.account_template_id, acc_parent=gen.account_parent_id.id, context=context)
                return self.pool.get('account.account').create(cr, uid, new_acc, context=context)
            else:
                return gen.account_reference_id and gen.account_reference_id.id or False
        return False

    def create(self, cr, uid, data, context=None):
        """
        When create a customer and supplier, we create the account code
        and affect it to this partner
        """
        if context is None:
            context = {}

        res = super(res_partner, self).create(cr, uid, data, context)
        self.write(cr, uid, [res], {}, context=context)
        return res

    def write(self, cr, uid, ids, vals=None, context=None):
        if context is None:
            context = {}

        if vals is None:
            vals = {}

        partners = self.browse(cr, uid, ids, context=context)
        acc_move_line_obj = self.pool.get('account.move.line')
        if 'name' in vals:
            # Check if name is allowed to be modified
            for pnr in partners:
                company_id = self._get_company_id(cr, uid, pnr, context=context)
                if (pnr.customer or vals.get('customer', 0) == 1):
                    acc_type_id = self._get_acc_type_id(cr, uid, company_id, 'customer', pnr, context=context)
                    if acc_type_id:
                        locked = self.pool.get('account.generator.type').read(cr, uid, [acc_type_id], ['lock_partner_name'], context=context)
                        # Check if account type locks partner's name and if partner account has at leasr one move
                        if (len(locked) == 1) \
                            and ('lock_partner_name' in locked[0]) \
                            and locked[0]['lock_partner_name'] \
                            and acc_move_line_obj.search(cr, uid, [('account_id', '=', pnr.property_account_receivable.id)], context=context):
                                raise osv.except_osv(_('Error'), _('You cannot change partner\'s name when his account has moves'))

                if (pnr.supplier or vals.get('supplier', 0) == 1):
                    acc_type_id = self._get_acc_type_id(cr, uid, company_id, 'supplier', pnr, context=context)
                    if acc_type_id:
                        locked = self.pool.get('account.generator.type').read(cr, uid, [acc_type_id], ['lock_partner_name'], context=context)
                        # Check if account type locks partner's name and if partner account has at leasr one move
                        if (len(locked) == 1) \
                            and ('lock_partner_name' in locked[0]) \
                            and locked[0]['lock_partner_name'] \
                            and acc_move_line_obj.search(cr, uid, [('account_id', '=', pnr.property_account_payable.id)], context=context):
                                raise osv.except_osv(_('Error'), _('You cannot change partner\'s name when his account has moves'))

        res= True
        if not context.get('skip_account_customer', False):
            for pnr in partners:
                company_id = self._get_company_id(cr, uid, pnr, context=context)
                ir_property_obj = self.pool.get('ir.property')
                if (pnr.customer or vals.get('customer', 0) == 1):
                    ir_property_ids = ir_property_obj.search(cr, uid, [('name', '=', 'property_account_receivable'), ('res_id', '=', False)], offset=0, limit=1, order=None, context=context)
                    ir_property = ir_property_obj.browse(cr, uid, ir_property_ids[0], context=context)
                    if ir_property.value_reference.id == pnr.property_account_receivable.id:
                        vals['property_account_receivable'] = self._create_new_account(cr, uid, company_id, 'customer', pnr, context=context)

                if (pnr.supplier or vals.get('supplier', 0) == 1):
                    ir_property_ids = ir_property_obj.search(cr, uid, [('name', '=', 'property_account_payable'), ('res_id', '=', False)], offset=0, limit=1, order=None, context=context)
                    ir_property = ir_property_obj.browse(cr, uid, ir_property_ids[0], context=context)
                    if ir_property.value_reference.id == pnr.property_account_payable.id:
                        vals['property_account_payable'] = self._create_new_account(cr, uid, company_id, 'supplier', pnr, context=context)

                if not super(res_partner, self).write(cr, uid, [pnr.id], vals, context=context):
                    res = False

        return res

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
