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
#           install module / create defaults parameters
#
##############################################################################
# Date      Author      Description
# 20090713  SYLEAM/CB   update default 3rd part account numbers
#
##############################################################################
#   TECHNICAL DETAILS : 
##############################################################################
from osv import fields,osv,orm
import tools    #for translations
import types


class wizard_install_third_part_accounts(osv.osv_memory):
    """
    """
    _name='wizard.install.third.part.accounts'

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
#        'code_digits': fields.integer('# of Digits',required=True,help="No. of Digits to use for account code"),
#        'seq_journal': fields.boolean('Separated Journal Sequences',help="Check this box if you want to use a different sequence for each created journal. Otherwise, all will use the same sequence."),
        'receivable_id': fields.many2one('account.account', 'Account receivable', domain="[('type', '=', 'view')]", required=True),     #,('user_type','=','receivable')
        'payable_id': fields.many2one('account.account', 'Account payable', domain="[('type', '=', 'view')]", required=True),
    }


    def _default_account_id(self, cr, uid, account_type, context={}):
        account_type_id = self.pool.get('account.account.type').search(cr, uid, [('code','=',account_type)])    #, context
        srch_args = [('type', '=', 'view'),('user_type','in',account_type_id)]
        account_id = self.pool.get('account.account').search(cr, uid, srch_args)    #[0]    #, limit=1, order='code')
        if account_id:
            if type(account_id) is types.IntType:
                return account_id
            elif type(account_id) is types.ListType:
                return account_id[0]
        return False

    def _default_receivable_id(self, cr, uid, context={}):
        receivable_id = self._default_account_id(cr, uid,'receivable', context)
        return receivable_id

    def _default_payable_id(self, cr, uid, context={}):
        payable_id = self._default_account_id(cr, uid, 'payable', context)
        return payable_id


    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr,uid,[uid],c)[0].company_id.id,
#        'code_digits': lambda *a:6,
        'receivable_id': _default_receivable_id,
        'payable_id': _default_payable_id,
    }


    def action_start_install(self, cr, uid, ids, context=None):
        """ Create the properties : specify default account (payable and receivable) for partners
        """
        wiz_data = self.browse(cr,uid,ids[0])
        todo_list = [
            ('property_account_receivable','res.partner','account.account', wiz_data.receivable_id.id),
            ('property_account_payable','res.partner','account.account', wiz_data.payable_id.id),
        ]
        property_obj = self.pool.get('ir.property')
        fields_obj = self.pool.get('ir.model.fields')
        for record in todo_list:
            r = property_obj.search(cr, uid, [('name','=', record[0] ),('company_id','=',wiz_data.company_id.id)])
            if r:   #the property exist: modify it
                vals = {
                    'value': record[3] and 'account.account,'+str(record[3]) or False,
                }
                property_obj.write(cr, uid, r, vals)
            else:   #create the property
                field = fields_obj.search(cr, uid, [('name','=',record[0]),('model','=',record[1]),('relation','=',record[2])])
                vals = {
                    'name': record[0],
                    'company_id': wiz_data.company_id.id,
                    'fields_id': field[0],
                    'value': record[3] and 'account.account,'+str(record[3]) or False,
                }
                property_obj.create(cr, uid, vals)
        next_action = {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.actions.configuration.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target':'new',
       }
        return next_action


    def action_cancel(self,cr,uid,ids,conect=None):
        return {'type':'ir.actions.act_window_close' }

wizard_install_third_part_accounts()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

