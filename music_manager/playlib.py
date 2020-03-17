# Simple media independent playlist management system.

import random
import math
from collections import deque
from functools import partial


def permutation_index(l, n):
    """Generates a permutation of an array given an index. Deterministic.

    Keyword arguments:
    l - List to get a permutation of.
    n - permutation number.
    """
    s = []
    lrefs = list(range(len(l)))
    for i in range(len(l)):
        c = len(lrefs)
        f = n % math.factorial(c) // math.factorial(c-1)
        s.append(l[lrefs.pop(f)])
    return s


class LazyCalculatedList:
    """List that calculates values to fill itself as necessary. Useful for
    caching deterministic values.

    This class is indexable like an array. Use LazyCalculatedList[index] to get
    a value from it. The calculation is used to generate new values to fill the
    list.

    Keyword arguments
    calculation - Calculation to perform to generate a value. Must accept one
        positional argument.
    cache_limit - Number of cached values to save. 0 generates a new value
        every time. None saves all generated values.
    """

    def __init__(self, calculation, cache_limit=None):
        """List that calculates values to fill itself as necessary. Useful for
        caching deterministic values.

        This class is indexable like an array. Use LazyCalculatedList[index] to
        get a value from it. The calculation is used to generate new values to
        fill the list.

        Keyword arguments
        calculation - Calculation to perform to generate a value. Must accept
            one positional argument.
        cache_limit - Number of cached values to save. 0 generates a new value
            every time. None saves all generated values.
        """
        self._data = {}
        self._cache_limit = cache_limit
        self._cache = deque()
        self._calculation = calculation

    def __getitem__(self, index):
        if self._cache_limit is None or self._cache_limit > 0:
            if index in self._data.keys():
                return self._data[index]
            else:
                val = self._calculation(index)
                self._cache_value(index, val)
                return val
        else:
            return self._calculation(index)

    def _cache_value(self, index, value):
        self._cache.append(index)
        self._data[index] = value
        while len(self._cache) > self._cache_limit:
            self._data.pop(self._cache.popleft())


class Playlist:
    """This class is meant to be an abstract implementation of a playlist or
    play queue. It supports shuffling and looping, and is meant to act as an
    iterator for easy usage. It's shuffle algorithm is meant to be repeatable
    in any direction, meaning it will be able to replay all content in the
    exact same order if it is rewound. It also avoids storing as much
    information as possible, mitigating memory limit issues.
    """

    def __init__(self, items, order, shuffle_cache_limit=2):
        self.items = items
        self.length = 0
        section_patterns = []
        self.pattern = []
        self._shuffle_caches = []
        self._shuffle_section_seeds = []
        self._order = order
        self._shuffle = False
        self._loop = False
        self._loop_count = 0
        self._index = 0

        for section in self.items:
            self._shuffle_caches.append(
                LazyCalculatedList(
                    calculation=partial(permutation_index, section),
                    cache_limit=shuffle_cache_limit
                    )
                )
            self._shuffle_section_seeds.append({})
            self.length += len(section)
            section_patterns.append([])
            offset = random.uniform(0, 1/len(section))
            for i in range(0, len(section)):
                section_patterns[-1].append(offset+i/len(section))
        while True:
            loop = 2
            s = None
            for section in range(0, len(section_patterns)):
                if len(section_patterns[section]) > 0:
                    if section_patterns[section][0] < loop:
                        loop = section_patterns[section][0]
                        s = section
            if loop <= 1:
                self.pattern.append(s)
                section_patterns[s].pop(0)
            else:
                break

    def set_shuffle(self, state):
        if state:
            self._shuffle = True
        else:
            if self._shuffle:
                o = []
                for index in range(len(self._order)):
                    loop = index // len(self.pattern)
                    index = index % len(self.pattern)
                    s = self.pattern[index]
                    if loop not in self._shuffle_section_seeds[s].keys():
                        self._shuffle_section_seeds[s][loop] = \
                            random.randint(
                                0,
                                math.factorial(len(self.items[s]))-1
                                )
                    section = self._shuffle_caches[s][
                        self._shuffle_section_seeds[s][loop]
                        ]
                    item = section[self.pattern[0:index].count(s)]
                    o.append((s, self.items[s].index(item)))
                self._order = o
            self._shuffle = False

    def get_shuffle(self):
        return self._shuffle

    def set_loop(self, state):
        self._loop = state
        self.clear_loop()

    def get_loop(self):
        return self._loop

    def clear_loop(self):
        self._loop_count = 0

    def __getitem__(self, index):
        if self._shuffle:
            loop = index // len(self.pattern)
            index = index % len(self.pattern)
            s = self.pattern[index]
            if loop not in self._shuffle_section_seeds[s].keys():
                self._shuffle_section_seeds[s][loop] = \
                    random.randint(0, math.factorial(len(self.items[s]))-1)
            section = self._shuffle_caches[s][
                self._shuffle_section_seeds[s][loop]
                ]
            return section[self.pattern[0:index].count(s)]
        else:
            item = self._order[index % len(self._order)]
            return self.items[item[0]][item[1]]

    def __len__(self):
        count = 0
        for section in self.items:
            count += len(section)
        return count

    def __iter__(self):
        self._index = 0
        self.clear_loop()
        return self

    def __next__(self):
        if not self._loop:
            if self._loop_count >= len(self):
                raise StopIteration
            self._loop_count += 1
        v = self[self._index]
        self._index += 1
        return v

    #def next(self):
        #if not self._loop:
        #    self._loop_count += 1
        #self._index += 1

    def prev(self):
        if not self._loop:
            self._loop_count -= 2
        self._index -= 2


if __name__ == "__main__":
    a = ["a0", "a1", "a2", "a3", "a4"]
    b = ["b5", "b6", "b7"]
    c = ["c8", "c9"]
    p = Playlist([a, b, c], (
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (1, 0),
        (1, 1),
        (1, 2),
        (2, 0),
        (2, 1)
        ))
    print(p.pattern)
    i = 0
    from time import sleep
    p.set_shuffle(True)
    p.set_shuffle(False)
    for n in p:
        if i % len(p.pattern) <= 0:
            print("=" * 80)
        print(n)
        i += 1
        sleep(0.5)
