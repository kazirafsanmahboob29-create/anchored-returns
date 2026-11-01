# Refit the Treasury comparison using the same saved inputs in base R.
args <- commandArgs(trailingOnly=TRUE)
folder <- if(length(args)) args[1] else 'reports/treasury-comparison'
filing <- read.csv('reports/filing-study/panel.csv', stringsAsFactors=FALSE)
earlier <- read.csv('reports/factor-study/estimation.csv', stringsAsFactors=FALSE)
stopifnot(!anyDuplicated(filing$id), !anyDuplicated(earlier$id))
full <- filing[tolower(as.character(filing$prior_eligible)) %in% c('true','1'),]
recent <- full[full$year>=2010 & full$year<=2024,]
common <- recent[recent$id %in% earlier$id,]
matched <- earlier[match(common$id,earlier$id),]
stopifnot(identical(common$id,matched$id),
          identical(common$state,matched$state),
          identical(common$authorized_date,matched$authorized_date),
          identical(common$requested_date,matched$requested_date),
          max(abs(common$award-matched$roe))<1e-12)
for(key in c('treasury90','curve90','inflation','stress','prior')) {
  common[[paste0('old_',key)]] <- matched[[key]]
  earlier[[paste0('old_',key)]] <- earlier[[key]]
}
earlier$award <- earlier$roe
samples <- list(full=full, recent=recent, common=common, original=earlier)
specs <- read.csv(file.path(folder,'models.csv'),stringsAsFactors=FALSE)
results <- list()
for(i in seq_len(nrow(specs))) {
  spec <- specs[i,]
  d <- samples[[spec$sample]]
  terms <- strsplit(spec$features,';',fixed=TRUE)[[1]]
  formula <- as.formula(paste('award ~',paste(c(terms,'factor(state)','factor(year)'),collapse='+')))
  model <- lm(formula,data=d)
  X <- model.matrix(model); u <- as.numeric(residuals(model))
  n <- nrow(X); k <- ncol(X)
  stopifnot(n==spec$n,qr(X)$rank==k,n>k+2)
  bread <- solve(crossprod(X))
  clustered <- function(group) {
    scores <- rowsum(X*u,group,reorder=FALSE)
    g <- nrow(scores)
    g/(g-1)*(n-1)/(n-k)*bread%*%crossprod(scores)%*%bread
  }
  V <- clustered(d$state)+clustered(d$quarter)-clustered(paste(d$state,d$quarter,sep='|'))
  critical <- qt(.975,min(length(unique(d$state)),length(unique(d$quarter)))-1)
  for(term in terms) {
    estimate <- unname(coef(model)[term]); variance <- V[term,term]
    se <- if(variance>=0) sqrt(variance) else NA_real_
    results[[length(results)+1]] <- data.frame(model=spec$model,term=term,
      estimate=estimate,se=se,low=estimate-critical*se,high=estimate+critical*se)
  }
}
checked <- do.call(rbind,results)
reference <- read.csv(file.path(folder,'coefficients.csv'),stringsAsFactors=FALSE)
stopifnot(identical(checked$model,reference$model),identical(checked$term,reference$term))
for(key in c('estimate','se','low','high')) stopifnot(
  identical(is.na(checked[[key]]),is.na(reference[[key]])),
  all(abs(checked[[key]]-reference[[key]])<1e-7,na.rm=TRUE))
write.csv(checked,file.path(folder,'r-coefficients.csv'),row.names=FALSE,na='')
cat(sprintf('R Treasury comparison passed: %d models and %d coefficient rows.\n',nrow(specs),nrow(checked)))
