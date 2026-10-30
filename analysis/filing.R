# Refit the request/decision models and filing-date predictions in base R.
args <- commandArgs(trailingOnly=TRUE)
folder <- if(length(args)) args[1] else 'reports/filing-study'
d <- read.csv(file.path(folder,'panel.csv'),stringsAsFactors=FALSE)
for(key in c('stage_eligible','prior_eligible','forecast_eligible'))
  d[[key]] <- tolower(as.character(d[[key]])) %in% c('true','1')
specs <- read.csv(file.path(folder,'model_specs.csv'),stringsAsFactors=FALSE)
records <- list(); fitted <- list()
for(i in seq_len(nrow(specs))) {
  spec <- specs[i,]; s <- d[d[[spec$flag]],]
  features <- strsplit(spec$features,';',fixed=TRUE)[[1]]
  effects <- if(spec$effects=='state_year') 'factor(state)+factor(year)' else 'factor(entity)+factor(year)'
  formula <- as.formula(paste(spec$target,'~',paste(c(features,effects),collapse='+')))
  w <- if(spec$weight=='decision_days') 1/as.numeric(ave(rep(1,nrow(s)),s$decision_day_group,FUN=length)) else rep(1,nrow(s))
  model <- lm(formula,data=s,weights=w)
  X <- model.matrix(model)*sqrt(w); u <- residuals(model)*sqrt(w)
  n <- nrow(X); k <- ncol(X); stopifnot(qr(X)$rank==k,n>k+2)
  bread <- solve(crossprod(X))
  cluster <- function(group) {
    scores <- rowsum(X*as.numeric(u),group,reorder=FALSE); g <- nrow(scores)
    g/(g-1)*(n-1)/(n-k)*bread%*%crossprod(scores)%*%bread
  }
  VS <- cluster(s$state); VQ <- cluster(s$quarter)
  matrices <- list(two_way=VS+VQ-cluster(paste(s$state,s$quarter,sep='|')),state=VS,quarter=VQ)
  critical <- qt(.975,min(length(unique(s$state)),length(unique(s$quarter)))-1)
  fitted[[spec$model]] <- coef(model)
  for(covariance in names(matrices)) for(term in features) {
    estimate <- unname(coef(model)[term]); variance <- matrices[[covariance]][term,term]
    se <- if(variance>=0) sqrt(variance) else NA_real_
    records[[length(records)+1]] <- data.frame(model=spec$model,covariance=covariance,term=term,
      estimate=estimate,se=se,low=estimate-critical*se,high=estimate+critical*se)
  }
}
checked <- do.call(rbind,records)
expected <- read.csv(file.path(folder,'coefficients.csv'),stringsAsFactors=FALSE)
for(key in c('model','covariance','term')) stopifnot(identical(checked[[key]],expected[[key]]))
for(key in c('estimate','se','low','high')) stopifnot(identical(is.na(checked[[key]]),is.na(expected[[key]])),all(abs(checked[[key]]-expected[[key]])<1e-7,na.rm=TRUE))
write.csv(checked,file.path(folder,'r-coefficients.csv'),row.names=FALSE,na='')

reference <- read.csv(file.path(folder,'decomposition.csv'),stringsAsFactors=FALSE)
decomposed <- reference[,c('specification','term')]
for(target in c('request','decision_gap','award')) decomposed[[target]] <- mapply(function(spec,term)
  unname(fitted[[paste0(spec,'_',target)]][term]),reference$specification,reference$term)
stopifnot(max(abs(decomposed$award-decomposed$request-decomposed$decision_gap))<1e-9)
write.csv(decomposed,file.path(folder,'r-decomposition.csv'),row.names=FALSE)

features <- c('filing_treasury90','filing_inflation','filing_unemployment','distribution','prior_age','known_prior')
d <- d[d$forecast_eligible,]; rows <- list()
for(start in c(2000,2005,2010,2015,2020)) {
  end <- if(start==2020) 2022 else start+4
  train <- d[d$authorized_date<paste0(start,'-01-01'),]
  test <- d[d$filing_year>=start & d$filing_year<=end,]
  if(nrow(train)<100 || !nrow(test)) next
  if(any(vapply(train[,c(features,'request')],function(x) length(unique(x))<2,logical(1)))) next
  stopifnot(max(train$authorized_date)<min(test$requested_date),all(test$known_prior_date<test$requested_date))
  row <- data.frame(id=test$id,prior=test$known_prior,request=test$request,
    request_adjusted=test$request+mean(train$decision_gap),prior_adjusted=test$known_prior+mean(train$award_change))
  for(name in c('market_prior','with_request')) {
    terms <- c(features,if(name=='with_request') 'request')
    model <- lm(as.formula(paste('award ~',paste(terms,collapse='+'))),data=train)
    row[[name]] <- predict(model,newdata=test)
  }
  rows[[length(rows)+1]] <- row
}
predictions <- do.call(rbind,rows)
saved <- read.csv(file.path(folder,'predictions.csv'),stringsAsFactors=FALSE)
stopifnot(identical(predictions$id,saved$id))
for(key in setdiff(names(predictions),'id')) stopifnot(all(abs(predictions[[key]]-saved[[key]])<1e-8))
write.csv(predictions,file.path(folder,'r-predictions.csv'),row.names=FALSE)
cat(sprintf('R filing study passed: %d coefficient/covariance rows, %d decomposition terms and %d predictions under six rules.\n',nrow(checked),nrow(decomposed),nrow(predictions)))
