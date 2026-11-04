# Everyday commands. Python 3.10+; the package has no dependencies (pip install -e . for the iab command).
PY ?= python3

.PHONY: test results clean

test:  ## run the unit tests
	$(PY) -W error::SyntaxWarning -m unittest discover -s tests -t .

results:  ## regenerate every committed dataset from the workloads (a few seconds); git diff shows any change
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 --out results/signals \
	  --title "Which signal should the autoscaler follow?" \
	  -p static-2 -p static-24 -p hpa-utilization -p hpa-concurrency -p hpa-queue -p hpa-rps
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 --out results/targets \
	  --title "Does a lower target buy the objective?" \
	  -p static-24 -p target-7.5=hpa-concurrency:target=7.5 -p target-6=hpa-concurrency:target=6 \
	  -p target-4.5=hpa-concurrency:target=4.5 -p target-3=hpa-concurrency:target=3
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 --out results/down-window \
	  --title "What does a shorter scale-down window cost, and what does it save?" \
	  -p conc-down-300=hpa-concurrency:down=300 -p conc-down-120=hpa-concurrency:down=120 \
	  -p conc-down-60=hpa-concurrency:down=60 -p conc-down-30=hpa-concurrency:down=30 \
	  -p queue-down-300=hpa-queue:down=300 -p queue-down-60=hpa-queue:down=60
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 --out results/startup \
	  --title "How much of the miss is pod startup?" \
	  -p static-24 -p startup-10s=hpa-concurrency:startup=10 -p startup-20s=hpa-concurrency:startup=20 \
	  -p startup-45s=hpa-concurrency:startup=45 -p startup-120s=hpa-concurrency:startup=120
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 --out results/scale-up-limit \
	  --title "Is the HPA's scale-up limit the bottleneck?" \
	  -p static-24 -p limit-default=hpa-concurrency -p limit-8=hpa-concurrency:up_pods=8,up_percent=200 \
	  -p limit-16=hpa-concurrency:up_pods=16,up_percent=400 -p limit-none=hpa-concurrency:up_pods=32 \
	  -p limit-none-startup-10s=hpa-concurrency:up_pods=32,startup=10
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 --out results/warm-pool \
	  --title "How much standing headroom buys the objective?" \
	  -p static-24 -p min-2=hpa-concurrency:min=2 -p min-4=hpa-concurrency:min=4 -p min-6=hpa-concurrency:min=6 \
	  -p min-8=hpa-concurrency:min=8 -p min-12=hpa-concurrency:min=12
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 --out results/sync-period \
	  --title "Is it the control loop? The decision period, with the scale-up limit lifted, and pods that start at once" \
	  -p static-24 -p sync-30s=hpa-concurrency:up_pods=32,startup=10,sync=30 \
	  -p sync-15s=hpa-concurrency:up_pods=32,startup=10,sync=15 -p sync-5s=hpa-concurrency:up_pods=32,startup=10,sync=5 \
	  -p sync-1s=hpa-concurrency:up_pods=32,startup=10,sync=1 \
	  -p instant=hpa-concurrency:up_pods=32,startup=1,sync=1

clean:
	rm -rf build dist *.egg-info
