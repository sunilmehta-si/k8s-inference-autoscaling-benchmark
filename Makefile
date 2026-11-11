# Everyday commands. Python 3.10+; the package has no dependencies (pip install -e . for the iab command).
PY ?= python3

.PHONY: test results results-pod-queues results-ramps results-keda results-predictive clean

test:  ## run the unit tests
	$(PY) -W error::SyntaxWarning -m unittest discover -s tests -t .

define DATASETS
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 $(2) --out $(1)/signals \
	  --title "Which signal should the autoscaler follow?" \
	  -p static-2 -p static-24 -p hpa-utilization -p hpa-concurrency -p hpa-queue -p hpa-rps
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 $(2) --out $(1)/targets \
	  --title "Does a lower target buy the objective?" \
	  -p static-24 -p target-7.5=hpa-concurrency:target=7.5 -p target-6=hpa-concurrency:target=6 \
	  -p target-4.5=hpa-concurrency:target=4.5 -p target-3=hpa-concurrency:target=3
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 $(2) --out $(1)/down-window \
	  --title "What does a shorter scale-down window cost, and what does it save?" \
	  -p conc-down-300=hpa-concurrency:down=300 -p conc-down-120=hpa-concurrency:down=120 \
	  -p conc-down-60=hpa-concurrency:down=60 -p conc-down-30=hpa-concurrency:down=30 \
	  -p queue-down-300=hpa-queue:down=300 -p queue-down-60=hpa-queue:down=60
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 $(2) --out $(1)/startup \
	  --title "How much of the miss is pod startup?" \
	  -p static-24 -p startup-10s=hpa-concurrency:startup=10 -p startup-20s=hpa-concurrency:startup=20 \
	  -p startup-45s=hpa-concurrency:startup=45 -p startup-120s=hpa-concurrency:startup=120
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 $(2) --out $(1)/scale-up-limit \
	  --title "Is the HPA's scale-up limit the bottleneck?" \
	  -p static-24 -p limit-default=hpa-concurrency -p limit-8=hpa-concurrency:up_pods=8,up_percent=200 \
	  -p limit-16=hpa-concurrency:up_pods=16,up_percent=400 -p limit-none=hpa-concurrency:up_pods=32 \
	  -p limit-none-startup-10s=hpa-concurrency:up_pods=32,startup=10
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 $(2) --out $(1)/warm-pool \
	  --title "How much standing headroom buys the objective?" \
	  -p static-24 -p min-2=hpa-concurrency:min=2 -p min-4=hpa-concurrency:min=4 -p min-6=hpa-concurrency:min=6 \
	  -p min-8=hpa-concurrency:min=8 -p min-12=hpa-concurrency:min=12
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 $(2) --out $(1)/sync-period \
	  --title "Is it the control loop? The decision period, with the scale-up limit lifted, and pods that start at once" \
	  -p static-24 -p sync-30s=hpa-concurrency:up_pods=32,startup=10,sync=30 \
	  -p sync-15s=hpa-concurrency:up_pods=32,startup=10,sync=15 -p sync-5s=hpa-concurrency:up_pods=32,startup=10,sync=5 \
	  -p sync-1s=hpa-concurrency:up_pods=32,startup=10,sync=1 \
	  -p instant=hpa-concurrency:up_pods=32,startup=1,sync=1
endef

results:  ## regenerate every committed dataset from the workloads (a few seconds); git diff shows any change
	$(call DATASETS,results,)

results-pod-queues:  ## the same datasets with a queue per pod, in results/pod-queues
	$(call DATASETS,results/pod-queues,--route pod)

results-ramps:  ## the same deployment on ramps of 30, 120, 300 and 600 s, in results/ramps
	for r in 30 120 300 600; do \
	  $(PY) -m inference_autoscaling_bench matrix workloads/ramp-$$r.json --runs 8 --out results/ramps/ramp-$$r \
	    --title "A ramp from 3 to 20 requests per second over $$r s" \
	    -p static-24 -p hpa-concurrency -p hpa-utilization -p cluster-like=hpa-concurrency:route=pod,lag=30 || exit 1; \
	done

results-keda:  ## the HPA and KEDA on each signal in the model, with a queue per pod and the scraped pipeline, in results/keda/model
	$(PY) -m inference_autoscaling_bench matrix workloads/burst.json --runs 8 --out results/keda/model \
	  --title "Does the autoscaler KEDA creates decide differently? The model, before the cluster" \
	  -p hpa-concurrency=hpa-concurrency:route=pod,scrape=15 -p keda-concurrency=keda-concurrency:route=pod,scrape=15 \
	  -p hpa-queue=hpa-queue:route=pod,scrape=15 -p keda-queue=keda-queue:route=pod,scrape=15 \
	  -p hpa-utilization=hpa-utilization:route=pod,scrape=15 -p keda-utilization=keda-utilization:route=pod,scrape=15

results-predictive:  ## the HPA beside a policy that forecasts the rate one pod startup ahead, on the burst and the ramps
	for w in burst ramp-30 ramp-120 ramp-300 ramp-600; do \
	  $(PY) -m inference_autoscaling_bench matrix workloads/$$w.json --runs 8 --out results/predictive/$$w \
	    --title "Does scaling ahead of the load beat reacting to it? ($$w)" \
	    -p static-24 -p hpa-concurrency -p predict-concurrency -p hpa-rps -p predict-rps -p warm-12=hpa-concurrency:min=12 \
	    -p cluster-like=hpa-concurrency:route=pod,scrape=15 -p predict-cluster-like=predict-concurrency:route=pod,scrape=15 \
	    || exit 1; \
	done

clean:
	rm -rf build dist *.egg-info
