cd traces && python3 generateTrace.py cluster1.sort
cd ..
mv traces/input_trace.csv artifacts/input_trace.csv
mv traces/meminit.csv artifacts/meminit.csv