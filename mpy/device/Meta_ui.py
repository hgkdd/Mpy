# -*- coding: utf-8 -*-
"""This is :mod:`mpy.device.Metaui`: Metaclass to Build a standard GUI from the
    _setgetlist.

   :author: Christian Albrecht (main author)
   :copyright: All rights reserved
   :license: no licence yet
"""



from enthought.traits.has_traits import MetaHasTraits
import enthought.traits.api as tapi
import enthought.traits.ui.api as tuiapi
import enthought.traits.ui.menu as tuim

import StringIO
import re


def erzeugeSetMethode_fired(name, class_dict):
    """
    """
    def _Methode_fired(self):
        print "Set"+name+"_fired"
        print getattr(self,"new%s"%name.upper())
        setattr(self,name.upper(),getattr(self,"new%s"%name.upper()))
        #err,value= getattr(self.sp, "Set%s"%name)(getatter(self,"new%s"%name.upper()))
        #setattr(self,name.upper(),value)
        
    methodeName = "_Set%s_fired"%name
    class_dict[methodeName] = _Methode_fired 

def erzeugeGetMethode_fired(name, class_dict):
    """
    """
    def _Methode_fired(self):
        print "Get"+name+"_fired"
        print getattr(self,"new%s"%name.upper())
        #setattr(self,name.upper(), getattr(self.sp, "Get%s"%name)[1])
        
    methodeName = "_Get%s_fired"%name
    class_dict[methodeName] = _Methode_fired 



def _Init_fired(self):
    ini=StringIO.StringIO(self.INI)
    #self.sp.Init(ini)
        
    #Alle Get Funktionen einmal aufrufen und so die Anzeige mit aktuellen Werten belegen.
    for item in self.mainEntries:
        getattr(self,"_Get%s_fired"%item)()
    


    
class Metaui(MetaHasTraits):
    
    #def __init__(cls, eins, zwei, drei):
    #    print "init %s \n\n   %s  \n\n %s"%(eins,zwei,drei)
    
    def __new__(cls, class_name, bases, class_dict):
               
        class_dict.update({'_Init_fired': _Init_fired })
        
        mainTab=class_dict.get("__parentclass__")._setgetlist
        #mainTab in einen String schreiben.
        #Dieser String wird dann druch eval ausgewertet.
        mainEntries=[]     
        items=""
        for name,i1,i2,i3,i4,typ in mainTab:
            if typ == None:
                continue
            name = re.findall(r'Set(.*)',name)[0]
            items="%s tuiapi.Group("%(items)
            items="%s tuiapi.Item('%s',label='Wert',style='readonly',width=70),"%(items, name.upper())
            items="%s tuiapi.Item('new%s',label='Neu',width=60),"%(items,name.upper())
            items="%s tuiapi.Item('Set%s',show_label=False),"%(items,name)
            items="%s tuiapi.Item('Get%s',show_label=False),"%(items,name)
            items="%s orientation='horizontal'),"%(items)
            erzeugeSetMethode_fired(name, class_dict)
            erzeugeGetMethode_fired(name, class_dict)
            class_dict.update({
                            'Set%s'%name: tapi.Button("Set%s"%name),
                           'Get%s'%name: tapi.Button("Get%s"%name),
                           })
            if typ == float:
                class_dict.update({
                           '%s'%(name.upper()): tapi.Float(),
                           'new%s'%(name.upper()):tapi.Float()
                           })
            elif typ == int:
                class_dict.update({
                           '%s'%(name.upper()): tapi.Int(),
                           'new%s'%(name.upper()):tapi.Int()
                           })
            else:
                class_dict.update({
                           '%s'%(name.upper()): tapi.Str(),
                           'new%s'%(name.upper()):tapi.Str()
                           })
            mainEntries.append(name)
    
        class_dict.update({'mainEntries': mainEntries})
        
        
        
        
        items=items[:-1]
        MAIN_grp=tuiapi.Group(eval(items),                        
                          label='Main')
     
        INI_grp=tuiapi.Group(tuiapi.Item('INI', style='custom',springy=True,width=500,height=200,show_label=False),
                         tuiapi.Item('Init', show_label=False),
                         label='Ini')
        
        tabs='INI_grp,MAIN_grp'
        for i in class_dict:
            if type(class_dict.get(i)) == tuiapi.Group:
                tabs ='%s,class_dict.get("%s")'%(tabs,i)
        tabs = "tuiapi.Group(%s, layout='tabbed')"%tabs
        
        class_dict.update({'traits_view': tuiapi.View(eval(tabs),title="Spectrumanalyer", buttons=[tuim.CancelButton])})
        
        #print "Meta   %s \n\n bases\n %s \n\n dict \n %s"%(class_name,str(bases),str(class_dict))
        return MetaHasTraits.__new__(cls, class_name, bases, class_dict)