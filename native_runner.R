# Research runner for native malariasimulation (improvements I3, I4).
#
# Usage:
#   Rscript native_runner.R --manifest manifests/pilot.csv --out runs/pilot [--shard 1 --of 4]
#                           [--daily all|first|none]
#
# Runs every manifest row whose position falls in this shard, skipping run_ids
# already in this shard's summary file, so an interrupted run can be restarted.
# To run in parallel, start N processes with --shard 1..N --of N (decision D3).
# imperial_experiments.R is kept unchanged as provenance for the demonstration data.

options(warn=1)
script_dir <- local({
  f <- sub('^--file=', '', grep('^--file=', commandArgs(FALSE), value=TRUE))
  if (length(f)) dirname(normalizePath(f)) else getwd()
})
if (dir.exists(file.path(script_dir, 'work/rlib')))
  .libPaths(c(file.path(script_dir, 'work/rlib'), .libPaths()))
if (!requireNamespace('malariasimulation', quietly=TRUE))
  stop('Install malariasimulation 3.0.0 (Rscript install_R.R)')
source(file.path(script_dir, 'R', 'scenario.R'))

arg <- function(name, default=NULL) {
  a <- commandArgs(trailingOnly=TRUE)
  i <- match(paste0('--', name), a)
  if (is.na(i)) { if (is.null(default)) stop('Missing --', name); default } else a[i + 1]
}
manifest_path <- arg('manifest')
outroot <- arg('out')
shard <- as.integer(arg('shard', '1'))
shards <- as.integer(arg('of', '1'))
daily <- arg('daily', 'all')
stopifnot(shard >= 1, shard <= shards, daily %in% c('all', 'first', 'none'))

manifest <- read.csv(manifest_path, stringsAsFactors=FALSE)
required <- c('run_id', 'partition', 'context', 'eir', 'net', 'rep', 'seed',
              'population', 'burn_days', 'horizon_days')
missing <- setdiff(required, names(manifest))
if (length(missing)) stop('Manifest is missing columns: ', paste(missing, collapse=', '))
if (anyDuplicated(manifest$run_id)) stop('Duplicate run_id in manifest')
mine <- manifest[(seq_len(nrow(manifest)) - 1L) %% shards == shard - 1L, , drop=FALSE]

for (d in c('daily', 'params')) dir.create(file.path(outroot, d), recursive=TRUE, showWarnings=FALSE)
summary_path <- file.path(outroot, sprintf('summary_shard%02d.csv', shard))
done <- if (file.exists(summary_path)) read.csv(summary_path)$run_id else character()

# Version record (I4): one per shard so parallel processes never write the same file.
json_str <- function(x) paste0('"', gsub('(["\\\\])', '\\\\\\1', x), '"')
git_commit <- tryCatch(system2('git', c('-C', shQuote(script_dir), 'rev-parse', 'HEAD'),
                               stdout=TRUE, stderr=FALSE)[1], error=function(e) NA)
git_dirty <- tryCatch(length(system2('git', c('-C', shQuote(script_dir), 'status', '--porcelain'),
                                     stdout=TRUE, stderr=FALSE)) > 0, error=function(e) NA)
manifest_hash <- tryCatch(unname(tools::sha256sum(manifest_path)),
                          error=function(e) paste0('md5:', unname(tools::md5sum(manifest_path))))
desc <- utils::packageDescription('malariasimulation')
record <- c(
  r_version=R.version.string,
  malariasimulation_version=as.character(utils::packageVersion('malariasimulation')),
  malariasimulation_source_sha=if (is.null(desc$RemoteSha)) NA else desc$RemoteSha,
  git_commit=git_commit, git_dirty=as.character(git_dirty),
  manifest=basename(manifest_path), manifest_hash=manifest_hash,
  net_scenario=NET_SCENARIO, shard=sprintf('%d/%d', shard, shards),
  platform=R.version$platform, started=format(Sys.time(), tz='UTC', usetz=TRUE))
writeLines(c('{', paste0('  ', json_str(names(record)), ': ',
                         ifelse(is.na(record), 'null', json_str(record)),
                         c(rep(',', length(record) - 1), '')), '}'),
           file.path(outroot, sprintf('version_record_shard%02d.json', shard)))
capture.output(sessionInfo(), file=file.path(outroot, sprintf('sessionInfo_shard%02d.txt', shard)))

todo <- mine[!mine$run_id %in% done, , drop=FALSE]
cat(sprintf('Shard %d/%d: %d runs, %d already done, %d to run\n',
            shard, shards, nrow(mine), nrow(mine) - nrow(todo), nrow(todo)))
for (i in seq_len(nrow(todo))) {
  x <- todo[i, ]
  p <- build_parameters(x$eir, x$net, x$population, x$burn_days, x$horizon_days)
  scenario_key <- sub('-r[0-9]+$', '', x$run_id)
  param_file <- file.path(outroot, 'params', paste0(scenario_key, '.rds'))
  if (!file.exists(param_file)) saveRDS(p, param_file)
  set.seed(x$seed)
  timing <- system.time(o <- malariasimulation::run_simulation(
    timesteps=x$burn_days + x$horizon_days, parameters=p))
  s <- summarise_run(o, x$burn_days, x$population)
  if (daily == 'all' || (daily == 'first' && x$rep == 1)) {
    con <- gzfile(file.path(outroot, 'daily', paste0(x$run_id, '.csv.gz')), 'w')
    write.csv(o, con, row.names=FALSE); close(con)
  }
  row <- data.frame(x[required], s, net_scenario=NET_SCENARIO,
    elapsed_seconds=unname(timing['elapsed']),
    cpu_seconds=unname(timing['user.self'] + timing['sys.self']),
    malariasimulation_version=record[['malariasimulation_version']], calibrated=FALSE)
  write.table(row, summary_path, sep=',', row.names=FALSE, qmethod='double',
              col.names=!file.exists(summary_path), append=file.exists(summary_path))
  cat(sprintf('[%d/%d] %s prevalence=%.4f in %.1fs\n', i, nrow(todo), x$run_id,
              s$mean_lm_prevalence_2to10, timing['elapsed']))
  flush.console()
}
cat('Shard complete\n')
