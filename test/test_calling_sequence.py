from mpylab.tools.calling import get_calling_sequence


def test2():
    return test()


def test():
    return get_calling_sequence()


if __name__ == '__main__':
    print(test()[-1])
    print(test2()[-1])