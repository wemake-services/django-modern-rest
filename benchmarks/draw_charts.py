from matplotlib import pyplot as plt

with plt.xkcd():
    bar_colors = ['#3fe384', '#35544c', '#35544c']
    names = ['dmr', 'ninja', 'drf']
    values = [5774.94, 3888.13, 3024.24]

    plt.figure(figsize=(8,4))
    plt.bar(names, values, color=bar_colors)
    plt.ylabel("RPS (Higher is better)")
    plt.savefig("dmr.svg", transparent=True)
