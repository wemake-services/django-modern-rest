.PHONY: bench
bench:
	python run_benchmark.py

.PHONY: bench-resolver
bench-resolver:
	hyperfine --warmup 1 --shell=none -L impl django,dmr --show-output \
		-L case best,avg,worst --min-runs=5 \
		-n {impl}-{case} \
		"python features/url_resolver.py --impl {impl} --case {case}"
