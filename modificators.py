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
#           library to generate account codes
#
##############################################################################
# Date      Author      Description
# 20090603  SYLEAM/CB   modificators
#
##############################################################################
import string


class Modificator(object):

    def __init__(self, strVal):
        self.strVal = strVal
                
    def setval(self, strVal):
        self.strVal = strVal
                
    def rmspace(self):
        return self.strVal.replace(' ','')

    def rmponct(self):
        newval = self.strVal
        for i in range(len(string.punctuation)):
            newval = newval.replace(string.punctuation[i], '')
        return newval

    def rmaccent(self):
        newval = self.strVal.encode('utf-8')
        oldchar = "àäâéèëêïîöôüûùÿÄÂËÊÏÎÖÔÜÛ".decode('utf-8')
        newchar = "aaaeeeeiioouuuyAAEEIIOOUU"
        for i in range(len(oldchar)):
            newval = newval.replace(oldchar[i].encode('utf-8'), newchar[i])
        return newval

    def truncate1(self):
        return self.strVal[:1]

    def truncate2(self):
        return self.strVal[:2]

    def truncate4(self):
#        print "DEBUG: Modificator::truncate4 --> %r" % self.strVal[:4]
        return self.strVal[:4]

    def truncate6(self):
#        print "DEBUG: Modificator::truncate6 --> %r" % self.strVal[:6]
        return self.strVal[:6]

    def charnum(self):
        first_letter = self.strVal[0]
        if first_letter.isalpha():
            num = ord(first_letter.upper()) - 64
            return ("%d" % num).zfill(2)
        else:
            return "00"

    def capitalize(self):
#        print "DEBUG: Modificator::capitalize --> %r" % self.strVal.upper()
        return self.strVal.upper()

    def zfill2(self):
        return self.strVal.zfill(2)

    def zfill4(self):
        return self.strVal.zfill(4)

    def zfill6(self):
        return self.strVal.zfill(6)

