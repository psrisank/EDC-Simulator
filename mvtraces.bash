cd ../disaggregated_dc/traces && python3 generateTrace.py cluster1.sort
cd ..
mv traces/input_trace.csv ../EDC/artifacts/input_trace.csv
mv traces/meminit.csv ../EDC/artifacts/meminit.csv