
import sys
from colored import stylize, fore, back, style


def yprint(*args, **kwargs):
    print(stylize(*args, back('yellow_1')), **kwargs)

def gprint(*args, **kwargs):
    print(stylize(*args, back('green_yellow')), **kwargs)


if __name__ == "__main__":

    yellows = ['yellow', 'light_yellow', 'yellow_4a', 'yellow_4b', 'yellow_3a', 'green_yellow', 'yellow_3b', 'yellow_2', 'yellow_1', ]

    for yellow in yellows:
        print(stylize(f"Hello {yellow}", back(yellow)))

