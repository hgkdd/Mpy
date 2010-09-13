# -*- coding: utf-8 -*-
import re

from mpy_exceptions import *

class R_TYPES(object):
   
    def __init__(self):
        pass


class R_DEFAULT(R_TYPES):
    
    def __init__(self,type,command=None):
        self.type = type
        self.command=command
        if type == float:
            self.validator=R_FLOAT(command=command)
        elif type == int:
            self.validator=R_INT(command=command)
        elif type == str:
            self.validator=R_STR(command=command) 
        
        elif type == bool:
            self.validator=R_BOOL(command=command)   
        
        else:
            mess=''
            if self.command:
                mess='in Command:  %s'%self.command.getName()
            raise Return_TypesError('Return Type %s not defined in R_DEFAULT \n    %s'%(self.type,mess))
    
    def __call__(self,value):
        return self.validator(value)
    

class R_FLOAT(R_TYPES):
    def __init__(self,tmpl=r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?',command=None):
        self.tmpl=tmpl
        self.command = command
        
    def __call__(self,value):
            #print value
            
            m=re.match(self.tmpl, value)
            if m:
                ans=m.group(0)
                try:
                    value=float(ans)
                    return value
                except:
                    pass
            
            mess=''
            if self.command:
                mess='in Command:  %s'%self.command.getName()
            raise Return_TypesError('Can not convert received value to float \n           %s'%mess)
            return None
        
class R_INT(R_TYPES):
    def __init__(self,tmpl=r'^\d+$',command=None):
        self.tmpl=tmpl
        self.command = command
        
    def __call__(self,value):
            m=re.match(self.tmpl, value)
            if m:
                ans=m.group(0)
                try:
                    value=int(ans)
                    return value
                except:
                    pass
            
            mess=''
            if self.command:
                mess='Command:  %s'%self.command.getName()
            raise Return_TypesError('Can not convert received value to int \n           %s'%mess)
            return None
        
        
        
class R_STR(R_TYPES):
    def __init__(self,tmpl=r'.*',command=None):
        self.tmpl=tmpl
        self.command = command
        
    def __call__(self,value):
            m=re.match(self.tmpl, value)
            if m:
                ans=m.group(0)
                try:
                    value=str(ans)
                    return value
                except:
                    pass
            
            mess=''
            if self.command:
                mess='Command:  %s'%self.command.getName()
            raise Return_TypesError('Can not convert received value to str \n           %s'%mess)
            return None


        
class R_BOOL(R_TYPES):
    def __init__(self,values_false=('off', '0','false'), values_true=('on','1','true'), command=None):
        self.values_true=values_true
        self.values_false=values_false
        self.command = command
        
    def __call__(self,value):
            #print value
            ans=str(value).lower()
            if ans in self.values_false:
                return False
            elif ans in self.values_true:
                return True
            
            mess=''
            if self.command:
                mess='Command:  %s'%self.command.getName()
            raise Return_TypesError('Can not convert received value to boolean \n           %s'%mess)
            return None





class TUPLE_OF_FLOAT(R_TYPES):
    def __init__(self,tmpl=r'([-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?,?)+',command=None):
        self.tmpl=tmpl
        self.command = command
        
    def __call__(self,value):
            m=re.match(self.tmpl, value)
            if m:
                ans=m.group(0)
                try:
                    temp=re.split(',', ans)
                    temp2=[]
                    for i in temp:
                        temp2.append(float(i))
                    return tuple(temp2)
                except:
                    pass
            
            mess=''
            if self.command:
                mess='Command:  %s'%self.command.getName()
            raise Return_TypesError('Can not convert received value to a tuple of float \n           %s'%mess)
            
            
            return None
    
        
