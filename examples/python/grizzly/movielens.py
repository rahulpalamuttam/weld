import pandas as pd
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
data = pd.merge(pd.merge(ratings, users), movies)
title_column = data["title"]

#print data
print "Time to merge:", (time.time() - start)
start = time.time()
mean_ratings = data.pivot_table('rating', index='title', columns='gender',
                                aggfunc='mean')

print "mean ratings"
print mean_ratings
#print "Time for mean ratings:", (time.time() - start)
groupby_start = time.time()
ratings_by_title = data.groupby('title').size()

#print "Time for groupby: ", (time.time() - groupby_start)

filter_ratings = time.time()
active_titles = ratings_by_title.index[ratings_by_title >= 250]
#print "TIme filtering ratings: ", (time.time() - filter_ratings)

filter_mean_ratings = time.time()
mean_ratings = mean_ratings.loc[active_titles]
#print "Mean ratings : ", (time.time() - filter_mean_ratings)

mean_ratings_diff = time.time()
mean_ratings['diff'] = mean_ratings['M'] - mean_ratings['F']
#print "Mean ratings diff and insert : ", (time.time() - mean_ratings_diff)

sorted_timings = time.time()
sorted_by_diff = mean_ratings.sort_values(by='diff')
#print "sorted by diff timing: ", (time.time() - sorted_timings)

groupby_title_rating_std = time.time()
rating_std_by_title = data.groupby('title')['rating'].std()
#print "groupby title rating std", (time.time() - groupby_title_rating_std)

filter_rating_active = time.time()
rating_std_by_title = rating_std_by_title.loc[active_titles]
#print "filter rating active title", (time.time() - filter_rating_active)

sort_slice = time.time()                                     
rating_std_by_title = rating_std_by_title.sort_values(ascending=False)[:10]
#print "Sort slice rating", (time.time() - sort_slice)

end = time.time()

print "Time for analysis:", (end - start)
print sorted_by_diff
print rating_std_by_title
