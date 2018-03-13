import pandas as pd
import grizzly.grizzly as gr
import time

passes = ["loop-fusion", "infer-size", "short-circuit-booleans", "predicate", "fix-iterate"]

# Make display smaller
pd.options.display.max_rows = 10

unames = ['user_id', 'gender', 'age', 'occupation', 'zip']
users = pd.read_table('data/ml-5m/users.dat', sep='::', header=None,
                      names=unames)

rnames = ['user_id', 'movie_id', 'rating', 'timestamp']
ratings = pd.read_table('data/ml-5m/ratings.dat', sep='::', header=None,
                        names=rnames)

mnames = ['movie_id', 'title', 'genres']
movies = pd.read_table('data/ml-5m/movies.dat', sep='::', header=None,
                       names=mnames)

start = time.time()
ratings = gr.DataFrameWeld(ratings)
users = gr.DataFrameWeld(users)
movies = gr.DataFrameWeld(movies)
data = gr.merge(gr.merge(ratings, users), movies).evaluate((True, 1), passes=passes).to_pandas()
print "Time to merge:", (time.time() - start)
start = time.time()
data = gr.DataFrameWeld(data)
mean_ratings = data.pivot_table('rating', index='title', columns='gender',
                                aggfunc='mean')


ratings_by_title = data.groupby('title').size()
active_titles = ratings_by_title.index[ratings_by_title >= 250]
mean_ratings = mean_ratings.loc[active_titles]
mean_ratings['diff'] = mean_ratings['M'] - mean_ratings['F']
sorted_by_diff = mean_ratings.sort_values(by='diff')
rating_std_by_title = data.groupby('title')['rating'].std()
rating_std_by_title = rating_std_by_title.loc[active_titles]
rating_std_by_title = rating_std_by_title.sort_values(ascending=False)[0:10]
sorted_by_diff, rating_std_by_title = gr.group_eval([sorted_by_diff, rating_std_by_title], passes=passes)
#print sorted_by_diff.evaluate((True, -1)).to_pandas()
#print rating_std_by_title.sort_values(ascending=False)[0:10].evaluate((True, -1))
end = time.time()

print "Time for analysis:", (end - start)

