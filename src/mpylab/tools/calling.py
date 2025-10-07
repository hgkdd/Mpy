# -*- coding: utf-8 -*-
"""
This is :mod:`mpylab.tools.calling`.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""


import inspect
from collections.abc import Iterable

def get_calling_sequence(prefixes: Iterable[str] | None = None) -> Iterable[str]:
    """
    Get the sequence of calls to this function.

    Parameter:
        - prefixes (Iterable[str] | None): prefixes that are lstripted from possible cmds, None -> ['return']
    """
    candidate = ''
    if prefixes is None:
        prefixes = ['return']
    prefixes.append('')
    try:
        frame = inspect.currentframe()  # this function
        outerframes = inspect.getouterframes(frame)  # all outerframes
        cmds=[]
        for _frameinfo_tuple_or_object in outerframes[1:]:    # index 0 is current frame; index -1: outermost frame; 3.5: list of named tuple; 3.11: list of FrameInfo objects
            obj = _frameinfo_tuple_or_object.frame
            name = _frameinfo_tuple_or_object.filename
            lno = _frameinfo_tuple_or_object.lineno
            func = _frameinfo_tuple_or_object.function
            code = _frameinfo_tuple_or_object.code_context
            index = _frameinfo_tuple_or_object.index

            if name == '<string>':   # exec
                #print type(obj)
                module=obj
                candidate=name  # probably, we will not get more information. But we try further...
            else:
                module=inspect.getmodule(obj) # 'code' from outerframes is only one line. We need more...
            #print type(module)
            try:
                slines, _ = inspect.getsourcelines(module) # so, get the module
            except OSError:  # can not get the source
                slines = []
            except TypeError:   # build-in module, class or function
                continue

            clen = len(slines)
            traceback_object = inspect.getframeinfo(obj, context=clen)  #we need mcode and mindex
            mname = traceback_object.filename
            mlno = traceback_object.lineno
            mfunc = traceback_object.function
            mcode = traceback_object.code_context
            mindex = traceback_object.index

            if mcode:
                candidate=''
                for line in mcode[mindex:]:  # start with the line where the command ends. Then go down
                    candidate = candidate + line
                    cstripped = candidate.lstrip()
                    compiles = False
                    for pf in prefixes:
                        if not cstripped.startswith(pf):
                            continue   # next prefix
                        try:
                            compile(cstripped[len(pf):].lstrip(), '<string>', 'exec')
                        except SyntaxError:
                            continue   # next prefix
                        else:
                            compiles = True
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
    from pprint import pprint
    def t1(*args, **kwargs):
        l = get_calling_sequence()
        return l

    def t2(*arg, **kwargs):
        l = t1('a', 'b', 'c',
             t=1,
             l=2)
        return l

    print("--------------------------")
    pprint(t2(1, 2, 4, t=0))
    print("--------------------------")
    l = None
    c = 'l=t1()'
    exec(c)
    print("--------------------------")
    pprint(l)
    print("--------------------------")

