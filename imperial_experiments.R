# Imperial College London malariasimulation experiments.
# From the portfolio root: Rscript shared/imperial_experiments.R smoke evidence/imperial
# Modes: smoke, vaccine, budget, emulator, observation, all.
# These are uncalibrated implementation examples, not country estimates.
args <- commandArgs(trailingOnly=TRUE)
options(warn=1)
mode <- if(length(args)) args[1] else 'smoke'
outroot <- if(length(args)>1) args[2] else 'evidence/imperial'
if (dir.exists('work/rlib')) .libPaths(c('work/rlib', .libPaths()))
if (!requireNamespace('malariasimulation',quietly=TRUE)) {
  stop('Install malariasimulation from the official MRC IDE R universe. See README.')
}
suppressPackageStartupMessages(library(malariasimulation))
stopifnot(mode %in% c('smoke','vaccine','budget','emulator','observation','all'))
dir.create(outroot,recursive=TRUE,showWarnings=FALSE)
year <- 365L
burn <- if(mode=='smoke') 180L else 2L*year
horizon <- if(mode=='smoke') 180L else if(mode=='vaccine'||mode=='budget'||mode=='all') 5L*year else 2L*year
population <- if(mode=='smoke') 300L else 500L
base <- function(eir=20, treatment=.45) {
  p <- get_parameters(list(human_population=population,
    clinical_incidence_rendering_min_ages=c(0,0),
    clinical_incidence_rendering_max_ages=c(5*year,100*year),
    severe_incidence_rendering_min_ages=c(0,0),
    severe_incidence_rendering_max_ages=c(5*year,100*year),
    prevalence_rendering_min_ages=2*year,
    prevalence_rendering_max_ages=10*year,
    individual_mosquitoes=FALSE))
  p <- set_drugs(p,list(AL_params))
  p <- set_clinical_treatment(p,drug=1,timesteps=1,coverages=treatment)
  set_equilibrium(p,init_EIR=eir)
}
nets <- function(p,coverage,times=1) {
  n <- length(times)
  set_bednets(p,timesteps=times,coverages=rep(coverage,length.out=n),
    dn0=matrix(.40,nrow=n,ncol=1),rn=matrix(.20,nrow=n,ncol=1),
    rnm=matrix(.05,nrow=n,ncol=1),gamman=rep(2*year,n),retention=3*year)
}
design <- data.frame(family=character(),policy=character(),eir=numeric(),
                    treatment=numeric(),net=numeric(),primary=numeric(),booster=numeric())
add <- function(family,policy,eir=20,treatment=.45,net=.5,primary=NA,booster=NA) {
  design <<- rbind(design,data.frame(family,policy,eir,treatment,net,primary,booster))
}
if(mode %in% c('vaccine','all')) {
  add('vaccine','current',primary=.70,booster=.65)
  add('vaccine','reach',primary=.82,booster=.65)
  add('vaccine','completion',primary=.70,booster=.85)
}
if(mode %in% c('budget','all')) {
  add('budget','funded',net=.70,treatment=.45)
  add('budget','proportional',net=.45,treatment=.30)
  add('budget','treatment_floor',net=.40,treatment=.45)
}
if(mode %in% c('emulator','all')) {
  for(e in c(5,20,50)) for(n in c(.3,.5,.7))
    add('emulator',paste0('eir',e,'_net',n),eir=e,net=n)
}
if(mode %in% c('observation','all')) {
  for(e in c(5,15,30)) for(t in c(.25,.5,.75))
    add('observation',paste0('eir',e,'_treat',t),eir=e,treatment=t,net=.5)
}
if(mode=='smoke') add('smoke','reference')
replicates <- if(mode=='smoke') 1L else 2L
rows <- list(); r <- 0L
for(i in seq_len(nrow(design))) for(rep in seq_len(replicates)) {
  x <- design[i,]; seed <- 231000L + rep
  p <- base(x$eir,if(x$family=='budget') .45 else x$treatment)
  p <- nets(p, .5, times=1)
  if(x$family=='vaccine') {
    p <- set_pev_epi(p,profile=r21_profile,timesteps=burn+1,
      coverages=x$primary,age=5*30,min_wait=0,booster_spacing=12*30,
      booster_coverage=matrix(x$booster),booster_profile=list(r21_booster_profile))
  } else if(x$family=='budget') {
    p <- set_clinical_treatment(p,drug=1,timesteps=c(1,burn+1,burn+2*year+1),
      coverages=c(.45,x$treatment,.45))
    p <- nets(p,coverage=c(.70,x$net,.70),times=c(1,burn+1,burn+3*year+1))
  } else p <- nets(p,x$net,times=c(1,burn+1))
  set.seed(seed)
  timing <- system.time(o <- run_simulation(timesteps=burn+horizon,parameters=p))
  post <- o[o$timestep>burn,,drop=FALSE]
  stopifnot(all(is.finite(post$n_inc_clinical_0_36500)),all(post$n_inc_clinical_0_36500>=0))
  if(!all(abs(rowSums(o[,c('S_count','A_count','D_count','U_count','Tr_count')])-population)<1e-6))
    stop('Human state totals do not match simulated population')
  folder <- file.path(outroot,x$family);dir.create(folder,recursive=TRUE,showWarnings=FALSE)
  file <- paste0(x$policy,'_rep',rep,'_daily.csv')
  write.csv(o,file.path(folder,file),row.names=FALSE)
  r <- r+1L
  rows[[r]] <- data.frame(x,rep=rep,seed=seed,population=population,burn_days=burn,
    horizon_days=horizon,clinical_under5=sum(post$n_inc_clinical_0_1825),
    clinical_all=sum(post$n_inc_clinical_0_36500),
    severe_under5=sum(post$n_inc_severe_0_1825),severe_all=sum(post$n_inc_severe_0_36500),
    under5_person_years=sum(post$n_age_0_1825)/year,
    all_person_years=sum(post$n_age_0_36500)/year,
    mean_lm_prevalence_2to10=sum(post$n_detect_lm_730_3650)/sum(post$n_age_730_3650),
    elapsed_seconds=unname(timing['elapsed']),calibrated=FALSE)
  write.csv(do.call(rbind,rows),file.path(outroot,'integration_summary.csv'),row.names=FALSE)
  cat('Completed',x$family,x$policy,rep,'in',timing['elapsed'],'seconds\n');flush.console()
}
writeLines(c('UNCALIBRATED IMPERIAL IMPLEMENTATION CHECK',
  paste('malariasimulation',packageVersion('malariasimulation')),
  'These few replicates are not sufficient for scientific comparisons.',
  'Vaccine dose accounting, capacity matching and programme costs are separate analyses.',
  'Budget examples test joint schedules, not an empirically costed allocation.',
  'No result in these files establishes country-specific impact or novelty.'),
  file.path(outroot,'STATUS.txt'))
capture.output(sessionInfo(),file=file.path(outroot,'sessionInfo.txt'))
