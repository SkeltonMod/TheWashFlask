import random as rd


def Entries(arr):  # ACCEPTS LIST
    dates = list()
    for x in range(len(arr)):
        dates.append(
            f"{arr[x].get('sort_id')}, {arr[x].get('date').strftime('%B')}, {arr[x].get('date').year}")

    return tally_months(dates)

def tally_months(arr):
    arr.sort()
    prev = ""
    a = list()
    b = list()
    # glued together

    c = list()
    for x in arr:
        if x != prev:
            a.append(x)
            b.append(1)
        else:
            b[len(b) - 1] += 1
        prev = x

    # now that we're done counting let's piece them together
    for x in range(len(a)):
        split = a[x].split(", ")
        c.append({"tally": f"{split[1]}, {split[2]} ({b[x]})", "sort_id": split[0]})

    return c
