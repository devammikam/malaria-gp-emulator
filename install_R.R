# Run in the R library normally used by your group.
# The verified handoff used R 4.6.1 and malariasimulation 3.0.0.
options(repos=c(mrcide='https://mrc-ide.r-universe.dev',CRAN='https://cloud.r-project.org'))
install.packages('malariasimulation')
stopifnot(requireNamespace('malariasimulation',quietly=TRUE))
if (as.character(packageVersion('malariasimulation')) != '3.0.0') {
  stop(paste('This handoff was checked against 3.0.0. Installed',
    packageVersion('malariasimulation'),
    'Pin source commit 5f63ccd61c8e893892fd12e7580fc22a7c882285 or validate the new version before use.'))
}
capture.output(sessionInfo(),file='R_install_session.txt')
