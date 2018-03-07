import pandas as pd
import grizzly.grizzly as gr
import numpy as np
import time
import sys

passes = ["loop-fusion", "short-circuit-booleans", "predicate", "vectorize", "fix-iterate"]
years = range(1880, 2011)
pieces = []
columns = ['year', 'name', 'sex', 'births']
for year in years:
    path = 'data/ml-50m/yob%d.txt' % year
    frame = pd.read_csv(path, names=columns)
    #frame['year'] = year
    pieces.append(frame)

# Concatenate everything into a single DataFram
names = pd.concat(pieces, ignore_index=True)
print "Size of names: %d" % len(names)

def get_top1000(group):
    # Note that there is a slight difference that arises
    # with the name 'Leslyn', year '25' missing as the ordering
    # in pandas for rows with the same 'sort' value changes.
    return group.sort_values(by='births', ascending=False).slice(0, 1000)

# Time preprocessing step
start0 = time.time()
grouped = gr.DataFrameWeld(names).groupby(['year', 'sex'])
top1000 = grouped.apply(get_top1000)
# Drop the group index, not needed
top1000.reset_index(inplace=True, drop=True)
top1000 = top1000.evaluate(True, passes=passes).to_pandas()
end0 = time.time()

start1 = time.time()
top1000 = gr.DataFrameWeld(top1000)
top1000names = top1000['name']
all_names = top1000names.unique()
lesley_like = all_names.filter(all_names.lower().contains('lesl'))
lesley_like_names = top1000names.isin(lesley_like).evaluate(True, passes=passes)
lesley_like_names = gr.SeriesWeld(lesley_like_names.values, gr.WeldVec(gr.WeldBit()))

filtered = top1000.filter(lesley_like_names)

table = filtered.pivot_table('births', index='year',
                              columns='sex', aggfunc='sum')

table = table.div(table.sum(1), axis=0)
end1 = time.time()
table.evaluate(True, passes=passes)#.to_pandas()


print "Time taken by preprocess portion: %.5f" %(end0 - start0)
print "Time taken by analysis portion  : %.5f" % (end1- start1)
