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
import inspect





def erzeugeFired_Methode_mit_Rfunction(command,rfunction,param_list):
    """
    """
    def Methode_fired(self):
        eval('self.dv.%s(%s)'%(command,", ".join(param_list)))
        setattr(self,rfunction.upper(),getattr(self.dv,rfunction)[0])
        
    return Methode_fired





def erzeugeFired_Methode(name,param_list):
    """
    """
    def Methode_fired(self):
        print name.upper()
        print 'self.%s(%s)'%(name,", ".join(param_list))
        print eval('self.dv.%s(%s)'%(name,", ".join(param_list)))[0]
        setattr(self,name.upper(),eval('self.dv.%s(%s)'%(name,", ".join(param_list)))[0])
        
    return Methode_fired



def _Init_fired(self):
    ini=StringIO.StringIO(self.INI)
    self.dv.Init(ini)
        
    #Alle Get Funktionen einmal aufrufen und so die Anzeige mit aktuellen Werten belegen.
    #for item in self.mainEntries:
    #    getattr(self,"_Get%s_fired"%item)()



def Erzeuge_TapiVar(typ):
            if typ == float:
                return tapi.Float()

            elif typ == int:
                return tapi.Int()
            else:
                return tapi.Str()
                

    
class Metaui(MetaHasTraits):
    
    #def __init__(cls, eins, zwei, drei):
    #    print "init %s \n\n   %s  \n\n %s"%(eins,zwei,drei)
    
    def __new__(cls, class_name, bases, class_dict):
               
        class_dict.update({'_Init_fired': _Init_fired })
        
        driverclass=class_dict.get("__driverclass__")
        _cmds=driverclass._cmds
        
        mainEntries=[]
        items_Map={} 
        
        for command_name,command in _cmds.items():
            items=""
            if command_name in mainEntries:
                continue
            
            mainEntries.append(command_name)
            
            
            items="%s tuiapi.Group("%(items)
            items="%s tuiapi.Item('%s',show_label=False),"%(items,command_name)
            
            
            if command.Rfunction():
                items="%s tuiapi.Item('%s',show_label=False),"%(items,command.Rfunction())
                items="%s tuiapi.Item('%s',label='Wert',style='readonly',width=70),"%(items,command.Rfunction().upper())
                
                class_dict[command.Rfunction().upper()]=Erzeuge_TapiVar(str)
                
                class_dict.update({
                            command_name: tapi.Button(command_name),
                            command.Rfunction(): tapi.Button(command.Rfunction()),
                            })
                
                if command.Rfunction() not in mainEntries:
                    mainEntries.append(command.Rfunction())
                
                if command.Rfunction() in items_Map.keys():
                    del items_Map[command.Rfunction()]
                
                
                
            else:
                items="%s tuiapi.Item('%s',label='Wert',style='readonly',width=70),"%(items,command_name.upper())
                class_dict.update({command_name: tapi.Button(command_name)})
                class_dict[command_name.upper()]=Erzeuge_TapiVar(str)
            
            

            param_list=[]
            for param_name,param in command.getParameter().items():
                if param.isGlobal():
                    continue
            
                if hasattr(driverclass,command_name):
                    if param_name not in inspect.getargspec(getattr(driverclass,command_name))[0]:
                        continue
                
                items="%s tuiapi.Item('param_%s_%s',label='%s',width=60),"%(items,command_name,param_name.upper(),param_name)
                class_dict['param_%s_%s'%(command_name,param_name.upper())]=Erzeuge_TapiVar(param.Getptype)
                param_list.append('self.param_%s_%s'%(command_name,param_name.upper()))
                
                
                

            if command.Rfunction():
                class_dict["_%s_fired"%command_name]=erzeugeFired_Methode_mit_Rfunction(command_name,command.Rfunction(),param_list)
                class_dict["_%s_fired"%command.Rfunction()]=erzeugeFired_Methode(command.Rfunction(),[])
            
            else:
                class_dict["%s_fired"%command_name]=erzeugeFired_Methode(command_name,param_list)
                
                
            items="%s orientation='horizontal')"%(items)
            
            items_Map[command_name]=items

        
        class_dict.update({'mainEntries': mainEntries})
        
        
        item_List=items_Map.values()
        item_List=[item_List[i:i+16] for i in range(0, len(item_List), 16)]
        
        print len(item_List[0])
        
        items=", ".join(items_Map.values())
        
        
        MAIN_grp=tuiapi.Group(eval(items),                        
                          label='Main')
        
        
        INI_grp=tuiapi.Group(tuiapi.Item('INI', style='custom',springy=True,width=500,height=200,show_label=False),
                         tuiapi.Item('Init', show_label=False),
                         label='Ini')
        
        tabs='INI_grp,MAIN_grp'
        
        #for i in class_dict:
        #    if type(class_dict.get(i)) == tuiapi.Group:
        #        tabs ='%s,class_dict.get("%s")'%(tabs,i)
        
        tabs = "tuiapi.Group(%s, layout='tabbed')"%tabs
        
        class_dict.update({'traits_view': tuiapi.View(eval(tabs),title="Spectrumanalyer", buttons=[tuim.CancelButton])})
        
        #print "Meta   %s \n\n bases\n %s \n\n dict \n %s"%(class_name,str(bases),str(class_dict))
        
        return MetaHasTraits.__new__(cls, class_name, bases, class_dict)