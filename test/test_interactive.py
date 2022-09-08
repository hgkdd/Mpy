import sys


def interactive(obj=None, banner=None, ):
    import code

    if obj is None:
        ns = vars()
    else:
        ns = vars(obj)

    code.interact(banner=banner, local=ns)


class Test:
    def __init__(self):
        self.a = 42

    def caller(self):
        print(self.a)
        interactive(obj=self)
        print(self.a)

if __name__ == "__main__":
    T = Test()
    T.caller()

