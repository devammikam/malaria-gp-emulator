# Scenario builder shared by native_runner.R and tests (decision D5).
# Net coverage = proportion of the population receiving a net at a mass
# distribution (malariasimulation's own definition in set_bednets()).

YEAR <- 365L
NET_SCENARIO <- 'D5_campaign_v1'
BASELINE_NET <- 0.5
TREATMENT <- 0.45
CAMPAIGN_INTERVAL <- 3L * YEAR

net_schedule <- function(net, burn, horizon) {
  # Baseline campaigns during burn-in, then option campaigns every 3 years.
  # set_bednets() overwrites earlier calls, so the whole schedule goes in one call.
  burn <- as.integer(burn); horizon <- as.integer(horizon)
  base_times <- as.integer(seq(1L, burn, by=CAMPAIGN_INTERVAL))
  option_times <- as.integer(seq(burn + 1L, burn + horizon, by=CAMPAIGN_INTERVAL))
  list(timesteps=c(base_times, option_times),
       coverages=c(rep(BASELINE_NET, length(base_times)), rep(net, length(option_times))))
}

build_parameters <- function(eir, net, population, burn, horizon) {
  p <- malariasimulation::get_parameters(list(
    human_population=population,
    clinical_incidence_rendering_min_ages=c(0, 0),
    clinical_incidence_rendering_max_ages=c(5 * YEAR, 100 * YEAR),
    severe_incidence_rendering_min_ages=c(0, 0),
    severe_incidence_rendering_max_ages=c(5 * YEAR, 100 * YEAR),
    prevalence_rendering_min_ages=2 * YEAR,
    prevalence_rendering_max_ages=10 * YEAR,
    individual_mosquitoes=FALSE))
  p <- malariasimulation::set_drugs(p, list(malariasimulation::AL_params))
  p <- malariasimulation::set_clinical_treatment(p, drug=1, timesteps=1, coverages=TREATMENT)
  p <- malariasimulation::set_equilibrium(p, init_EIR=eir)
  s <- net_schedule(net, burn, horizon)
  n <- length(s$timesteps)
  malariasimulation::set_bednets(p, timesteps=s$timesteps, coverages=s$coverages,
    dn0=matrix(.40, nrow=n, ncol=1), rn=matrix(.20, nrow=n, ncol=1),
    rnm=matrix(.05, nrow=n, ncol=1), gamman=rep(2 * YEAR, n), retention=3 * YEAR)
}

summarise_run <- function(o, burn, population) {
  post <- o[o$timestep > burn, , drop=FALSE]
  if (!all(is.finite(post$n_inc_clinical_0_36500)) || any(post$n_inc_clinical_0_36500 < 0))
    stop('Non-finite or negative clinical incidence')
  states <- rowSums(o[, c('S_count', 'A_count', 'D_count', 'U_count', 'Tr_count')])
  if (!all(abs(states - population) < 1e-6)) stop('Human state totals do not match population')
  denominator <- sum(post$n_age_730_3650)
  if (!(denominator > 0)) stop('Prevalence denominator is not positive')
  list(clinical_under5=sum(post$n_inc_clinical_0_1825),
       clinical_all=sum(post$n_inc_clinical_0_36500),
       severe_under5=sum(post$n_inc_severe_0_1825),
       severe_all=sum(post$n_inc_severe_0_36500),
       under5_person_years=sum(post$n_age_0_1825) / YEAR,
       all_person_years=sum(post$n_age_0_36500) / YEAR,
       prevalence_numerator_person_days=sum(post$n_detect_lm_730_3650),
       prevalence_denominator_person_days=denominator,
       mean_lm_prevalence_2to10=sum(post$n_detect_lm_730_3650) / denominator)
}
