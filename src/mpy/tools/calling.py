import inspect


def get_calling_sequence(prefixes=None):
    if prefixes is None:
        prefixes = ['return', 'print']
    prefixes.append('')
    try:
        frame = inspect.currentframe()  # this function
        outerframes = inspect.getouterframes(frame)  # all outerframes
        cmds=[]
        for obj,name,lno,func,code,index in outerframes[1:]:
            if name == '<string>':   # exec
                #print type(obj)
                module=obj
                candidate=name  # probably, we will not get more information. But we try further...
            else:
                module=inspect.getmodule(obj) # 'code' from outerframes is only one line. We need more...
            #print type(module)
            try:
                slines, _ = inspect.getsourcelines(module) # so, get the module
            except IOError:  # can not get the source
                slines = []
            except TypeError:
                continue
            clen = len(slines)
            mname,mlno,mfunc,mcode,mindex = inspect.getframeinfo(obj,clen)  #we need mcode and mindex
            if mcode:
                candidate=''
                for line in mcode[mindex::-1]:  # start with the line where the command ends. Then go up
                    candidate = line+candidate
                    cstripped=candidate.lstrip()
                    compiles=False
                    for pf in prefixes:
                        if not cstripped.startswith(pf):
                            continue   # next prefix
                        try:
                            compile(cstripped[len(pf):].lstrip(), '<string>', 'exec')
                        except SyntaxError:
                            continue   # next prefix
                        else:
                            compiles=True
                            break  # found snipplet
                    if compiles:
                        break  # exit for loop
            cmds.append(candidate.strip())
    finally:
        del frame
        del outerframes
        del obj
    return cmds[1:]


if __name__ == '__main__':
    def t1(*args, **kwargs):
        l = get_calling_sequence()
        return l

    def t2(*arg, **kwargs):
        l=t1('a', 'b', 'c',
             t=1,
             l=2)
        return l

    print("--------------------------")
    print(t2(1, 2, 4, t=0))
    print("--------------------------")
    l = None
    c = 'l=t1()'
    exec(c)
    print("--------------------------")
    print(l)
    print("--------------------------")

