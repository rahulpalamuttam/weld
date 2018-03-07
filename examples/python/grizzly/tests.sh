echo "pandas" > pandas.tt
# echo "grizzly_clo" > grizzly_clo.tt
# echo "grizzly_clo infer_length" > grizzly_clo_infer_length.tt
# echo "grizzly_clo prediaction" > grizzly_clo_predication.tt
# echo "grizzly_clo vectorize" > grizzly_clo_vectorize.tt
# echo "grizzly_clo loop fusion" > grizzly_clo_loop_fusion.tt

# echo "grizzly_clo parallel" > grizzly_clo8.tt
# echo "grizzly_clo infer_length parallel" > grizzly_clo_infer_length8.tt
# echo "grizzly_clo predication parallel" > grizzly_clo_predication8.tt
# echo "grizzly_clo vectorize parallel" > grizzly_clo_vectorize8.tt
# echo "grizzly_clo loop fusion parallel" > grizzly_clo_loop_fusion8.tt

echo "grizzly_clo clo" > grizzly_clo.tt
echo "grizzly_clo infer_length clo" > grizzly_clo_infer_length.tt
echo "grizzly_clo predication clo" > grizzly_clo_predication.tt
echo "grizzly_clo vectorize clo" > grizzly_clo_vectorize.tt
echo "grizzly_clo loop fusion clo" > grizzly_clo_loop_fusion.tt

echo "grizzly_clo parallel clo" > grizzly_clo8.tt
echo "grizzly_clo infer_length parallel clo" > grizzly_clo_infer_length8.tt
echo "grizzly_clo predication parallel clo" > grizzly_clo_predication8.tt
echo "grizzly_clo vectorize parallel clo" > grizzly_clo_vectorize8.tt
echo "grizzly_clo loop fusion parallel clo" > grizzly_clo_loop_fusion8.tt

NUM_ITERATIONS=5
for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_clo.tt
	 python birth_analysis_grizzly_clo.py >> grizzly_clo.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_clo_infer_length.tt
	 python birth_analysis_grizzly_clo_infer_length.py >> grizzly_clo_infer_length.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_clo_predication.tt
	 python birth_analysis_grizzly_clo_predication.py >> grizzly_clo_predication.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_clo_vectorize.tt
	 python birth_analysis_grizzly_clo_vectorize.py >> grizzly_clo_vectorize.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_clo_loop_fusion.tt
	 python birth_analysis_grizzly_clo_loop_fusion.py >> grizzly_clo_loop_fusion.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> pandas.tt
	 python birth_analysis.py >> pandas.tt
done

export WELD_NUM_THREADS=8
for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_clo8.tt
	 python birth_analysis_grizzly_clo.py >> grizzly_clo8.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_clo_infer_length8.tt
	 python birth_analysis_grizzly_clo_infer_length.py >> grizzly_clo_infer_length8.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_clo_predication8.tt
	 python birth_analysis_grizzly_clo_predication.py >> grizzly_clo_predication8.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_clo_vectorize8.tt
	 python birth_analysis_grizzly_clo_vectorize.py >> grizzly_clo_vectorize8.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> grizzly_clo_loop_fusion8.tt
	 python birth_analysis_grizzly_clo_loop_fusion.py >> grizzly_clo_loop_fusion8.tt
done

for i in $(seq "$NUM_ITERATIONS"):
do
	 echo $i >> pandas.tt
	 python birth_analysis.py >> pandas.tt
done
