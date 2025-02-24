all: run

run: simulator/Simulator.py
	python3 simulator/Simulator.py artifacts/input_trace.csv artifacts/meminit.csv artifacts/output_trace.csv