# Reproducibility and scenario checks (improvement I5).
# Run from the repository root: Rscript tests/test_reproducible.R
suppressPackageStartupMessages(library(malariasimulation))
source(file.path('R', 'scenario.R'))

check <- function(ok, label) {
  cat(if (ok) 'PASS' else 'FAIL', label, '\n')
  if (!ok) quit(status=1)
}

# D5 schedule: baseline campaigns in burn-in, option campaigns every 3 years after.
s <- net_schedule(0.7, burn=730, horizon=1825)
check(identical(s$timesteps, c(1L, 731L, 1826L)), 'net campaign days are 1, 731, 1826')
check(identical(s$coverages, c(.5, .7, .7)), 'baseline 0.5 then option coverage')
s <- net_schedule(0.3, burn=1460, horizon=1825)
check(identical(s$timesteps, c(1L, 1096L, 1461L, 2556L)), 'longer burn-in adds a baseline campaign')

p <- build_parameters(eir=20, net=0.7, population=200, burn=730, horizon=1825)
check(identical(p$bednet_timesteps, c(1L, 731L, 1826L)), 'schedule reaches the parameter object')
check(identical(p$bednet_coverages, c(.5, .7, .7)), 'coverages reach the parameter object')

# Same seed gives identical output; a different seed does not.
p <- build_parameters(eir=20, net=0.5, population=200, burn=60, horizon=60)
run <- function(seed) { set.seed(seed); run_simulation(timesteps=120, parameters=p) }
a <- run(42); b <- run(42); d <- run(43)
check(identical(a, b), 'same seed reproduces the run exactly')
check(!identical(a, d), 'different seed gives a different run')

s <- summarise_run(a, burn=60, population=200)
check(s$mean_lm_prevalence_2to10 >= 0 && s$mean_lm_prevalence_2to10 <= 1, 'prevalence in [0,1]')
check(s$prevalence_denominator_person_days > 0, 'prevalence denominator positive')
cat('All reproducibility checks passed\n')
