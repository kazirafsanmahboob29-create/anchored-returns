# Refit the peer regressions and block predictions with base R.
args <- commandArgs(trailingOnly=TRUE)
folder <- if(length(args)) args[1] else 'reports/peer-study'
d <- read.csv(file.path(folder,'panel.csv'),stringsAsFactors=FALSE)
for(key in c('prior_eligible','forecast_eligible'))
  d[[key]] <- tolower(as.character(d[[key]])) %in% c('true','1')
specs <- read.csv(file.path(folder,'models.csv'),stringsAsFactors=FALSE)
records <- list()
for(i in seq_len(nrow(specs))) {
  spec <- specs[i,]
  selected <- d[d$prior_eligible & !is.na(d$peer12),]
  if(grepl('six_common',spec$model)) selected <- selected[!is.na(selected$peer6),]
  features <- strsplit(spec$features,';',fixed=TRUE)[[1]]
  selected$trend <- selected$year-1985
  effects <- c('factor(state)',if(spec$effects=='state_year') 'factor(year)',
               if(spec$effects=='state_trend') 'trend')
  model <- lm(as.formula(paste('award ~',paste(c(features,effects),collapse='+'))),data=selected)
  X <- model.matrix(model); u <- residuals(model); n <- nrow(X); k <- ncol(X)
  stopifnot(nrow(selected)==spec$n,qr(X)$rank==k)
  bread <- solve(crossprod(X))
  cluster <- function(group) {
    scores <- rowsum(X*as.numeric(u),group,reorder=FALSE); g <- nrow(scores)
    g/(g-1)*(n-1)/(n-k)*bread%*%crossprod(scores)%*%bread
  }
  V <- cluster(selected$state)+cluster(selected$quarter)-cluster(paste(selected$state,selected$quarter,sep='|'))
  critical <- qt(.975,min(length(unique(selected$state)),length(unique(selected$quarter)))-1)
  for(term in features) {
    estimate <- unname(coef(model)[term]); se <- if(V[term,term]>=0) sqrt(V[term,term]) else NA_real_
    records[[length(records)+1]] <- data.frame(model=spec$model,term=term,estimate=estimate,se=se,
                                              low=estimate-critical*se,high=estimate+critical*se)
  }
}
actual <- do.call(rbind,records)
expected <- read.csv(file.path(folder,'coefficients.csv'),stringsAsFactors=FALSE)
for(key in c('model','term')) stopifnot(identical(actual[[key]],expected[[key]]))
for(key in c('estimate','se','low','high')) stopifnot(
  identical(is.na(actual[[key]]),is.na(expected[[key]])),
  all(abs(actual[[key]]-expected[[key]])<1e-7,na.rm=TRUE))
write.csv(actual,file.path(folder,'r-coefficients.csv'),row.names=FALSE,na='')

eligible <- d[d$forecast_eligible & !is.na(d$peer12),]
features <- c('filing_treasury90','filing_inflation','filing_unemployment','distribution','prior_age','known_prior')
rows <- list()
for(start in c(2000,2005,2010,2015,2020)) {
  end <- if(start==2020) 2022 else start+4
  train <- eligible[eligible$authorized_date<paste0(start,'-01-01'),]
  test <- eligible[eligible$filing_year>=start & eligible$filing_year<=end,]
  if(nrow(train)<100 || !nrow(test)) next
  if(any(vapply(train[,c(features,'request','peer12')],function(x) length(unique(x))<2,logical(1)))) next
  row <- data.frame(id=test$id,prior=test$known_prior)
  for(name in c('market_prior','with_request','market_peer')) {
    terms <- c(features,if(name=='with_request') 'request',if(name=='market_peer') 'peer12')
    model <- lm(as.formula(paste('award ~',paste(terms,collapse='+'))),data=train)
    stopifnot(model$rank==length(coef(model)),max(train$authorized_date)<min(test$requested_date),
              all(test$peer12_last<test$requested_date))
    row[[name]] <- predict(model,newdata=test)
  }
  rows[[length(rows)+1]] <- row
}
predictions <- do.call(rbind,rows)
saved <- read.csv(file.path(folder,'predictions.csv'),stringsAsFactors=FALSE)
stopifnot(identical(predictions$id,saved$id))
for(key in setdiff(names(predictions),'id')) stopifnot(all(abs(predictions[[key]]-saved[[key]])<1e-8))
write.csv(predictions,file.path(folder,'r-predictions.csv'),row.names=FALSE)
comparisons <- read.csv(file.path(folder,'prediction_comparisons.csv'),stringsAsFactors=FALSE)
for(i in seq_len(nrow(comparisons))) {
  r <- comparisons[i,]
  gain <- saved[[paste0('loss_',r$baseline)]]-saved$loss_market_peer
  residual <- gain-mean(gain); n <- nrow(saved)
  cluster <- function(group) {
    scores <- rowsum(matrix(residual,ncol=1),group,reorder=FALSE); g <- nrow(scores)
    g/(g-1)*sum(scores^2)/n^2
  }
  variance <- cluster(saved$state)+cluster(saved$quarter)-cluster(paste(saved$state,saved$quarter,sep='|'))
  se <- sqrt(variance)
  critical <- qt(.975,min(length(unique(saved$state)),length(unique(saved$quarter)))-1)
  stopifnot(abs(mean(gain)-r$estimate)<1e-8,abs(se-r$se)<1e-8,
            abs(mean(gain)-critical*se-r$low)<1e-8,abs(mean(gain)+critical*se-r$high)<1e-8)
}
cat(sprintf('R peer study passed: %d coefficient rows and %d predictions under four rules.\n',nrow(actual),nrow(predictions)))
