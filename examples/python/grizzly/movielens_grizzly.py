import pandas as pd
import grizzly.grizzly as gr
import time
import numpy as np
# Make display smaller
pd.options.display.max_rows = 10

unames = ['user_id', 'gender', 'age', 'occupation', 'zip']
users = pd.read_table('data/ml-2m/users.dat', sep='::', header=None,
                      names=unames)

rnames = ['user_id', 'movie_id', 'rating', 'timestamp']
ratings = pd.read_table('data/ml-2m/ratings.dat', sep='::', header=None,
                        names=rnames)

mnames = ['movie_id', 'title', 'genres']
movies = pd.read_table('data/ml-2m/movies.dat', sep='::', header=None,
                       names=mnames)

start = time.time()
ratings = gr.DataFrameWeld(ratings)
users = gr.DataFrameWeld(users)
movies = gr.DataFrameWeld(movies)
data = gr.merge(gr.merge(ratings, users), movies).evaluate((True, 1)).to_pandas()
print "Time to merge:", (time.time() - start)
start = time.time()

data = gr.DataFrameWeld(data)

mean_ratings = data.pivot_table('rating', index='title', columns='gender',
                                aggfunc='mean')

print "mean ratings eval"
print mean_ratings.evaluate((True, -1)).to_pandas()
ratings_by_title = data.groupby('title').size()

#print "ratings by title eval"
#ratings_by_title.evaluate((True, -1))

active_titles = ratings_by_title.index[ratings_by_title >= 250]

#print "active titles filter"
#active_titles.evaluate((True, -1))

mean_ratings = mean_ratings.loc[active_titles]
#print "mean_ratings loc filter"
#mean_ratings.evaluate((True, -1))

diff = mean_ratings['M'] - mean_ratings['F']

#print "difference evaluate"
#diff.evaluate((True, -1))

mean_ratings['diff'] = mean_ratings['M'] - mean_ratings['F']

#print "diff and reinsert"
#mean_ratings.evaluate((True, -1))

sorted_by_diff = mean_ratings.sort_values(by='diff')

#print "sorted by diff"
#sorted_by_diff.evaluate((True, -1))

rating_std_by_title = data.groupby('title')['rating'].std()
#print "rating_std_by_title"
#rating_std_by_title.evaluate((True, -1))

rating_std_by_title = rating_std_by_title.loc[active_titles]
#print "rating_std_by title loc"
#print rating_std_by_title.evaluate((True, -1))
rating_std_by_title = rating_std_by_title.sort_values(ascending=False)[0:10]
#print "sort values"
#print rating_std_by_title.evaluate((True, -1))

#print "final eval"
sorted_by_diff, rating_std_by_title = gr.group_eval([sorted_by_diff, rating_std_by_title])

#print sorted_by_diff.evaluate((True, -1)).to_pandas()
#print rating_std_by_title.sort_values(ascending=False)[0:10].evaluate((True, -1))
end = time.time()

print "Time for analysis:", (end - start)
print sorted_by_diff
print rating_std_by_title
