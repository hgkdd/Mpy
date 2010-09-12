# -*- coding: utf-8 -*-
import re

class IN_RANGE(object):
    
    def __init__(self,min,max,message=''):
        self.min=min
        self.max=max
        if message != '':
            self.message='Argument out of Range. Argument must be between %s and %s'%(self.min,self.max)
        else:
            self.message=message
    
    def __call__(self,value):
        if not isinstance(value, (int, float,long)):
            return (value,'The Validator IN_RANGE can only used for int, long or float')
        if value > self.max or value < self.min:
            return (value,self.message)
        return (value,None)
    

class IS_LOWER_THAN(object):
    def __init__(self,max,message=''):
        self.max=max
        if message != '':
            self.message='Argument is greater than or equal %s. Argument must be lower.'%(self.max)
        else:
            self.message=message
    
    def __call__(self,value):
        if not isinstance(value, (int, float,long)):
            return (value,'The Validator IS_LOWER_THAN can only used for int, long or float')
        if value >= self.max:
            return (value,self.message)
        return (value,None)


class IS_GREATER_THAN(object):
    def __init__(self,min,message=''):
        self.min=min
        if message != '':
            self.message='Argument is lower than or equal %s. Argument must be greater.'%(self.min)
        else:
            self.message=message
    
    def __call__(self,value):
        if not isinstance(value, (int, float,long)):
            return (value,'The Validator IS_GREATER_THAN can only used for int, long or float')
        if value <= self.min:
            return (value,self.message)
        return (value,None)


class IS_LOWER_EQUAL_THAN(object):
    def __init__(self,max,message=''):
        self.max=max
        if message != '':
            self.message='Argument is greater than %s. Argument must be lower or equal.'%(self.max)
        else:
            self.message=message
    
    def __call__(self,value):
        if not isinstance(value, (int, float,long)):
            return (value,'The Validator IS_LOWER_THAN can only used for int, long or float')
        if value > self.max:
            return (value,self.message)
        return (value,None)


class IS_GREATER_EQUAL_THAN(object):
    def __init__(self,min,message=''):
        self.min=min
        if message != '':
            self.message='Argument is lower than %s. Argument must be greater or equal.'%(self.min)
        else:
            self.message=message
    
    def __call__(self,value):
        if not isinstance(value, (int, float,long)):
            return (value,'The Validator IS_GREATER_THAN can only used for int, long or float')
        if value < self.min:
            return (value,self.message)
        return (value,None)


class  IS_IN_SET(object):
    def __init__(self,set,message=''):
        self.set=set
        if message != '':
            self.message='Argument must be in Set %s.'%(self.set)
        else:
            self.message=message
            
    def __call__(self,value):
        if not value in self.set:
            return (value,self.message)
        return (value,None)
    
#IS_MATCH, 
    