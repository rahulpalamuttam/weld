echo "pandas" > pandas.tt
echo "grizzly" > grizzly.tt
echo "grizzly infer_length" > grizzly_infer_length.tt
echo "grizzly prediaction" > grizzly_predication.tt
echo "grizzly vectorize" > grizzly_vectorize.tt
echo "grizzly loop fusion" > grizzly_loop_fusion.tt
echo "grizzly clo" > grizzly_clo.tt

echo "grizzly parallel" > grizzly8.tt
echo "grizzly infer_length parallel" > grizzly_infer_length8.tt
echo "grizzly predication parallel" > grizzly_predication8.tt
echo "grizzly vectorize parallel" > grizzly_vectorize8.tt
echo "grizzly loop fusion parallel" > grizzly_loop_fusion8.tt
echo "grizzly clo parallel" > grizzly_clo8.tt

NUM_ITERATIONS=5
# for i in $(seq "$NUM_ITERATIONS"):
# do
# 	 echo $i >> grizzly.tt
# 	 python movielens_grizzly.py >> grizzly.tt
# done

# for i in $(seq "$NUM_ITERATIONS"):
# do
# 	 echo $i >> grizzly_infer_length.tt
# 	 python movielens_grizzly_infer_length.py >> grizzly_infer_length.tt
# done

# for i in $(seq "$NUM_ITERATIONS"):
# do
# 	 echo $i >> grizzly_predication.tt
# 	 python movielens_grizzly_predication.py >> grizzly_predication.tt
# done

# for i in $(seq "$NUM_ITERATIONS"):
# do
# 	 echo $i >> grizzly_vectorize.tt
# 	 python movielens_grizzly_vectorize.py >> grizzly_vectorize.tt
# done

# for i in $(seq "$NUM_ITERATIONS"):
# do
# 	 echo $i >> grizzly_loop_fusion.tt
# 	 python movielens_grizzly_loop_fusion.py >> grizzly_loop_fusion.tt
# done

# for i in $(seq "$NUM_ITERATIONS"):
# do
# 	 echo $i >> grizzly_clo.tt
# 	 python movielens_grizzly_clo.py >> grizzly_clo.tt
# done


# for i in $(seq "$NUM_ITERATIONS"):
# do
# 	 echo $i >> pandas.tt
# 	 python movielens.py >> pandas.tt
# done

export WELD_NUM_THREADS=8
for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly8.tt
	 python movielens_grizzly.py >> grizzly8.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_infer_length8.tt
	 python movielens_grizzly_infer_length.py >> grizzly_infer_length8.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_predication8.tt
	 python movielens_grizzly_predication.py >> grizzly_predication8.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_vectorize8.tt
	 python movielens_grizzly_vectorize.py >> grizzly_vectorize8.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_clo8.tt
	 python movielens_grizzly_clo.py >> grizzly_clo8.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> pandas.tt
	 python movielens.py >> pandas.tt
done
