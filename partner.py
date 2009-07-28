# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2009 SISTHEO
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
#   AIM :   
#           generate third part accunt number on partner's view
#
##############################################################################
# Date      Author      Description
# 20090327  SYLEAM/CB   use the default parnet's account value as a patern
# 20090603  SYLEAM/CB   Add modificators
#
##############################################################################

from osv import fields, osv
from tools.translate import _
from modificators import *


class res_partner(osv.osv):
    _inherit = 'res.partner'

    _defaults = {
        'customer': lambda *a: 0,   # Do not compute account number if not necessary
    }

#----------------------------------------------------------
#   Private methods C&S
#----------------------------------------------------------
    def _get_compute_account_number(self, cr, uid, partner, seq_patern):
        """Compute account code based on partner and sequence

        @param partner: (browse/id) partner's datas
        @param seq_patern: (string) the sequence witch will be use as a patern/template

        @return: (string) the account code/number
        """
        if seq_patern.find('{') >= 0:
            prefix = seq_patern[:seq_patern.index('{')]
            suffix = seq_patern[seq_patern.index('}')+1:]
            body = seq_patern[len(prefix)+1:][:len(seq_patern)-len(prefix)-len(suffix)-2]
            
            ar_args = body.split('|')
    #        print "DEBUG: compute_account_number ar_args = %r" % ar_args
            # partner field is always first
            partner_value = getattr(partner, ar_args[0])
    #        print "DEBUG: compute_account_number partner_value = %r" % partner_value
            if partner_value:
                # Modificators
                mdf = Modificator(partner_value)
                for i in range(1, len(ar_args)):
                    mdf_funct = getattr(mdf, ar_args[i])
                    partner_value = mdf_funct()
                    mdf.setval(partner_value)
                account_number = prefix + partner_value + suffix
            else:
                account_number = prefix + suffix
        else:
            account_number = seq_patern

        # is there internal sequence ?
        pos_iseq = account_number.find('#')
        if pos_iseq >= 0:
            nzf = account_number.count('#')
            rootpart = account_number[:pos_iseq]
            # verify if root of this number is existing
            arAcc_ids = self.pool.get('account.account').search(cr, uid, [('code','like',rootpart)])
            cnt = len(arAcc_ids)
            next_inc = ("%0d" % int(cnt + 1)).zfill(nzf)
            account_number = account_number.replace('#' * nzf, next_inc)

        return account_number


    def _get_account_model(self, cr, uid, model_name):
        """Retreive default property for partner's account. This will be use as template / default values.

        @param model_name: (string) the name of the property

        @return: (browse/id) the account (object)
        """
        property_obj = self.pool.get('ir.property')
#FIXME OpenERP is creating bad properties with res_id setted, so by luck we can retreive the original one
        property_id = property_obj.search(cr, uid, [('name','=', model_name),('res_id','=',False)])
        if not property_id or len(property_id) != 1:
            #raise osv.except_osv(_('Error !'),_('You need to define ONE default account number in properties for %s' % model_name))
            return False
        property_data = self.pool.get('ir.property').browse(cr,uid, property_id)[0]
        account_id = int(property_data.value.split(',')[1])
        account_data = self.pool.get('account.account').browse(cr,uid, account_id)
        return account_data


    def _get_data_account_model(self, brobj_account):
        """Retreive account values from template.

        @param brobj_account: (browse/id) account template datas/values

        @return: (dict) the account values
        """
#FIXME there may be a better way to transfert data form parent to child's patern
        data_account_model = {
                                    'currency_id': brobj_account.currency_id.id,
                                    'user_type': brobj_account.user_type.id,
                                    'parent_id': brobj_account.id,
                                    'reconcile': brobj_account.reconcile,
                                    'shortcut': brobj_account.shortcut,
#                                    'tax_ids': parent_account.,        # not a good idea to have tax hear
#                                    'note': parent_account,            # keep it blank
                                    'company_currency_id': brobj_account.company_currency_id.id,
                                    'company_id': brobj_account.company_id.id,
                                    'active': True,
                                    'parent_left': brobj_account.parent_left,
                                    'parent_right': brobj_account.parent_right,
                                    'currency_mode': brobj_account.currency_mode,
                                    'check_history': brobj_account.check_history,
        }
        #print "_get_data_account_model %r" % data_account_model
        return data_account_model


    def _get_account_sequence(self, cr, uid, seq_name):
        """Retreive sequence value (next number).

        @param seq_name: (string) name of the sequence (not the same on suppliers and customers)

        @return: (string) the next value from selected sequence
        """
#FIXME code field is type of sequence nor code, so we're oblige to search on the name (witch can be translated)
        sequence_obj = self.pool.get('ir.sequence')
        sequence_id = sequence_obj.search(cr, uid, [('code','=', 'account.partner.third_part'), ('name','=', seq_name)])
        if not sequence_id or len(sequence_id) != 1:
            raise osv.except_osv(_('Error !'),_('You need to define the %s sequence' % seq_name))
        sequence_data = self.pool.get('ir.sequence').get_id(cr, uid, sequence_id[0])
        return sequence_data


#----------------------------------------------------------
#   Private methods CUSTOMER ONLY
#----------------------------------------------------------
    def _get_customer_account_model(self, cr, uid):
        """Retreive values from template for customer account.

        @return: (dict) the account values
        """
        parent_account = self._get_account_model(cr, uid, 'property_account_receivable')
        if not parent_account:
            return False
        customer_account_model = self._get_data_account_model(parent_account)
        customer_account_model['type'] = 'receivable'
        return customer_account_model


    def _get_customer_account_sequence(self, cr, uid):
        """Retreive customer sequence next value.

        @return: (string) the next value from selected sequence
        """
        return self._get_account_sequence(cr, uid, 'Customer account')


#----------------------------------------------------------
#   Private methods SUPPLIER ONLY
#----------------------------------------------------------
    def _get_supplier_account_model(self, cr, uid):
        """Retreive values from template for supplier account.

        @return: (dict) the account values
        """
        parent_account = self._get_account_model(cr, uid, 'property_account_payable')
        if not parent_account:
            return False
        supplier_account_model = self._get_data_account_model(parent_account)
        supplier_account_model['type'] = 'payable'
        return supplier_account_model


    def _get_supplier_account_sequence(self, cr, uid):
        """Retreive supplier sequence next value.

        @return: (string) the next value from selected sequence
        """
        return self._get_account_sequence(cr, uid, 'Supplier account')


# #########################################################
#       O V E R L O A D     O S V
# #########################################################
    def create(self, cr, uid, data, context={}):
        new_id = super(res_partner, self).create(cr, uid, data, context)
        if (('customer' in data) and (data['customer'] == 1)) or (('supplier' in data) and (data['supplier'] == 1)):
            self.write(cr, uid, [new_id], {}, context)    # fire account number computation (based on partner datas)
        return new_id


    def write(self, cr, uid, ids, vals, context={}):
        # Update all ids (batch way)
        osv_stuff = super(res_partner, self).write(cr, uid, ids, vals, context)
        for id in ids:
        # Update one by one
            partner = self.browse(cr, uid, [id])[0]
        # Customer account number
            default_receivable_account = self._get_account_model(cr, uid, 'property_account_receivable')
            if default_receivable_account and partner.customer and (partner.property_account_receivable.id == default_receivable_account.id):
                account_patern = self._get_customer_account_model(cr, uid)
                account_code = self._get_compute_account_number(cr, uid, partner, self._get_customer_account_sequence(cr, uid) )
                account_patern['name'] = str( _('Customer : ') + partner.name.encode("utf-8"))[:128]   #becarefull on translat° & length
                account_patern['code'] = account_code
                customer_account_id = self.pool.get('account.account').create(cr, uid, account_patern)
                super(res_partner, self).write(cr, uid, id, {'property_account_receivable': customer_account_id} )
        # Supplier account number
            default_payable_account = self._get_account_model(cr, uid, 'property_account_payable')
            if default_payable_account and partner.supplier and (partner.property_account_payable.id == default_payable_account.id):
                account_patern = self._get_supplier_account_model(cr, uid)
                account_code = self._get_compute_account_number(cr, uid, partner, self._get_supplier_account_sequence(cr, uid) )
                account_patern['name'] = str( _('Supplier : ') + partner.name.encode("utf-8"))[:128]   #becarefull on translat° & length
                account_patern['code'] = account_code
                supplier_account_id = self.pool.get('account.account').create(cr, uid, account_patern)
                super(res_partner, self).write(cr, uid, id, {'property_account_payable': supplier_account_id} )

        return osv_stuff

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
