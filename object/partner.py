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
from modificators import *
from tools.misc import debug


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
                res.append((t.name.replace(' ', '_').lower(), t.name))
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
                res.append((t.name.replace(' ', '_').lower(), t.name))
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
        elif len(type_ids) > 2:
            raise osv.except_osv(_('Error'), _('Too many default value define for %s type') % _(field))

        t = acc_type_obj.browse(cr, uid, type_ids[0], context=context)
        return t.name.replace(' ', '_').lower()

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

    def _get_account_model(self, cr, uid, model_name):
        """
        Retreive default property for partner's account. This will be use as template / default values.

        :param model_name: the name of the property
        :type  model_name: str
        :return: the account (object)
        :rtype: osv.osv.browse
        """
        property_obj = self.pool.get('ir.property')
        #FIXME OpenERP is creating bad properties with res_id setted, so by luck we can retreive the original one
        property_id = property_obj.search(cr, uid, [('name', '=', model_name), ('res_id', '=', False)])
        if not property_id or len(property_id) != 1:
            #raise osv.except_osv(_('Error !'),_('You need to define ONE default account number in properties for %s' % model_name))
            return False
        property_data = self.pool.get('ir.property').browse(cr, uid, property_id)[0]
        account_id = int(property_data.value.split(',')[1])
        account_data = self.pool.get('account.account').browse(cr, uid, account_id)
        return account_data

    def _get_data_account_model(self, brobj_account):
        """
        Retreive account values from template.

        :param brobj_account: account template datas/values
        :type  brobj_account: osv.osv.browse
        :return: the account values
        :rtype: dict
        """
        #FIXME there may be a better way to transfert data form parent to child's pattern
        data_account_model = {
            'currency_id': brobj_account.currency_id.id,
            'user_type': brobj_account.user_type.id,
            'parent_id': brobj_account.id,
            'reconcile': brobj_account.reconcile,
            'shortcut': brobj_account.shortcut,
            'company_currency_id': brobj_account.company_currency_id.id,
            'company_id': brobj_account.company_id.id,
            'active': True,
            'parent_left': brobj_account.parent_left,
            'parent_right': brobj_account.parent_right,
            'currency_mode': brobj_account.currency_mode,
            'check_history': brobj_account.check_history,
        }
        return data_account_model

    def _get_account_sequence(self, cr, uid, seq_name):
        """
        Retrieve sequence value (next number)

        :param seq_name: Name of the sequence (not the same on suppliers and customers)
        :type  seq_name: str

        :return: The next value from selected sequence
        :rtype: str
        """
        #FIXME code field is type of sequence nor code, so we're oblige to search on the name (witch can be translated)
        sequence_obj = self.pool.get('ir.sequence')
        sequence_id = sequence_obj.search(cr, uid, [('code', '=', 'account.partner.third_part'), ('name', '=', seq_name)])
        if not sequence_id or len(sequence_id) != 1:
            raise osv.except_osv(_('Error !'), _('You need to define the %s sequence' % seq_name))
        sequence_data = self.pool.get('ir.sequence').get_id(cr, uid, sequence_id[0])
        return sequence_data

    #----------------------------------------------------------
    #   Private methods CUSTOMER ONLY
    #----------------------------------------------------------
    def _get_customer_account_model(self, cr, uid):
        """
        Retrieve values from template for customer account.

        :return: The account values
        :rtype: dict
        """
        parent_account = self._get_account_model(cr, uid, 'property_account_receivable')
        if not parent_account:
            return False
        customer_account_model = self._get_data_account_model(parent_account)
        customer_account_model['type'] = 'receivable'
        return customer_account_model

    def _get_customer_account_sequence(self, cr, uid):
        """
        Retrieve customer sequence next value.

        :return: The next value from selected sequence
        :rtype: str
        """
        return self._get_account_sequence(cr, uid, 'Customer account')

    #----------------------------------------------------------
    #   Private methods SUPPLIER ONLY
    #----------------------------------------------------------
    def _get_supplier_account_model(self, cr, uid):
        """
        Retrieve values from template for supplier account.

        :return: The account values
        :rtype: dict
        """
        parent_account = self._get_account_model(cr, uid, 'property_account_payable')
        if not parent_account:
            return False
        supplier_account_model = self._get_data_account_model(parent_account)
        supplier_account_model['type'] = 'payable'
        return supplier_account_model

    def _get_supplier_account_sequence(self, cr, uid):
        """
        Retrieve supplier sequence next value.

        :return: The next value from selected sequence
        :rtype: str
        """
        return self._get_account_sequence(cr, uid, 'Supplier account')

    # #########################################################
    #       O V E R L O A D     O S V
    # #########################################################
    def create(self, cr, uid, data, context=None):
        """
        When create a customer and supplier, we create the account code
        and affect it to this partner
        """
        if context is None:
            context = {}

        new_id = super(res_partner, self).create(cr, uid, data, context)
        if not context.get('skip_account_customer', False):
            if data.get('customer', 0) == 1 or data.get('supplier', 0) == 1:
                self.write(cr, uid, [new_id], {}, context=context)
        return new_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}

        # Update all ids (batch way)
        osv_stuff = super(res_partner, self).write(cr, uid, ids, vals, context)
        for partner in self.browse(cr, uid, ids, context=context):
            # Update one by one
            #partner = self.browse(cr, uid, [id])[0]
            # Customer account number
            default_receivable_account = self._get_account_model(cr, uid, 'property_account_receivable')
            if default_receivable_account and partner.customer and (partner.property_account_receivable.id == default_receivable_account.id) and not context.get('skip_account_customer', False):
                account_patern = self._get_customer_account_model(cr, uid)
                account_code = self._get_compute_account_number(cr, uid, partner, self._get_customer_account_sequence(cr, uid))
                account_patern['name'] = _('Customer : ') + partner.name  # becarefull on translat° & length
                account_patern['name'] = account_patern['name'][:128]
                account_patern['code'] = account_code
                debug(account_patern)
                customer_account_id = self.pool.get('account.account').create(cr, uid, account_patern)
                super(res_partner, self).write(cr, uid, partner.id, {'property_account_receivable': customer_account_id})
            # Supplier account number
            default_payable_account = self._get_account_model(cr, uid, 'property_account_payable')
            if default_payable_account and partner.supplier and (partner.property_account_payable.id == default_payable_account.id) and not context.get('skip_account_supplier', False):
                account_patern = self._get_supplier_account_model(cr, uid)
                account_code = self._get_compute_account_number(cr, uid, partner, self._get_supplier_account_sequence(cr, uid))
                account_patern['name'] = _('Supplier : ') + partner.name  # becarefull on translat° & length
                account_patern['name'] = account_patern['name'][:128]
                account_patern['code'] = account_code
                debug(account_patern)
                supplier_account_id = self.pool.get('account.account').create(cr, uid, account_patern)
                super(res_partner, self).write(cr, uid, partner.id, {'property_account_payable': supplier_account_id})

        return osv_stuff

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
