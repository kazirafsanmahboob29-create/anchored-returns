# Reconstruct the expanded models and rolling predictions using base R.
args <- commandArgs(trailingOnly=TRUE)
folder <- if(length(args)) args[1] else 'reports/expanded-study'
d <- read.csv(file.path(folder,'panel.csv'),stringsAsFactors=FALSE)
for(key in c('main_eligible','change_eligible','long_eligible')) {
  d[[key]] <- tolower(as.character(d[[key]])) %in% c('true','1')
}
specs <- read.csv(file.path(folder,'model_specs.csv'),stringsAsFactors=FALSE)
expected <- read.csv(file.path(folder,'coefficients.csv'),stringsAsFactors=FALSE)
records <- list()
covariance_records <- list()
fitted_models <- list()
for(i in seq_len(nrow(specs))) {
  spec <- specs[i,]
  selected <- switch(spec$sample, main=d$main_eligible, change=d$change_eligible,
                     long=d$long_eligible, bridge=d$main_eligible & d$year>=2010)
  sample <- d[selected,]
  features <- strsplit(spec$features,';',fixed=TRUE)[[1]]
  effects <- switch(spec$effects, none='', state_year='factor(state)+factor(year)',
                    entity_year='factor(entity)+factor(year)')
  form <- as.formula(paste(spec$target,'~',paste(c(features,if(nchar(effects)) effects),collapse='+')))
  model <- lm(form,data=sample)
  X <- model.matrix(model); u <- residuals(model); n <- nrow(X); k <- ncol(X)
  stopifnot(qr(X)$rank==k,n>k+2)
  bread <- solve(crossprod(X))
  cluster <- function(group) {
    scores <- rowsum(X*as.numeric(u),group,reorder=FALSE)
    g <- nrow(scores)
    (g/(g-1))*((n-1)/(n-k))*bread%*%crossprod(scores)%*%bread
  }
  VS <- cluster(sample$state); VQ <- cluster(sample$quarter)
  V <- VS+VQ-cluster(paste(sample$state,sample$quarter,sep='|'))
  df <- min(length(unique(sample$state)),length(unique(sample$quarter)))-1
  critical <- qt(.975,df)
  fitted_models[[spec$model]] <- list(b=coef(model),two_way=V,state=VS,quarter=VQ,df=df)
  for(term in features) {
    estimate <- unname(coef(model)[term]); variance <- V[term,term]
    se <- if(variance>=0) sqrt(variance) else NA_real_
    records[[length(records)+1]] <- data.frame(model=spec$model,term=term,estimate=estimate,se=se,
                                              low=estimate-critical*se,high=estimate+critical*se)
  }
  for(covariance in c('state','quarter')) {
    matrix <- if(covariance=='state') VS else VQ
    for(term in features) {
      estimate <- unname(coef(model)[term]); variance <- matrix[term,term]
      se <- if(variance>=0) sqrt(variance) else NA_real_
      covariance_records[[length(covariance_records)+1]] <- data.frame(
        model=spec$model,covariance=covariance,term=term,estimate=estimate,se=se,
        low=estimate-critical*se,high=estimate+critical*se)
    }
  }
}
checked <- do.call(rbind,records)
stopifnot(identical(paste(checked$model,checked$term),paste(expected$model,expected$term)))
for(key in c('estimate','se','low','high')) {
  same_missing <- is.na(checked[[key]])==is.na(expected[[key]])
  stopifnot(all(same_missing),all(abs(checked[[key]]-expected[[key]])<1e-7,na.rm=TRUE))
}
write.csv(checked,file.path(folder,'r-crosscheck.csv'),row.names=FALSE,na='')
write.csv(do.call(rbind,covariance_records),file.path(folder,'r-covariance.csv'),row.names=FALSE,na='')

joint_specs <- list(equal_rise_fall_slopes=list(model='asymmetric',terms=c('rate_rise','rate_fall')),
                    equal_regional_rate_slopes=list(model='regional_slopes',terms=c('rate_midwest','rate_south','rate_west')))
joint_rows <- list()
for(name in names(joint_specs)) {
  spec <- joint_specs[[name]]; model <- fitted_models[[spec$model]]
  q <- if(name=='equal_rise_fall_slopes') 1 else 3
  contrast <- matrix(0,nrow=q,ncol=length(model$b),dimnames=list(NULL,names(model$b)))
  if(q==1) contrast[1,spec$terms] <- c(1,-1) else for(j in 1:3) contrast[j,spec$terms[j]] <- 1
  value <- contrast%*%model$b
  for(covariance in c('two_way','state','quarter')) {
    variance <- contrast%*%model[[covariance]]%*%t(contrast)
    statistic <- if(min(eigen(variance,symmetric=TRUE,only.values=TRUE)$values)>0)
      as.numeric(t(value)%*%solve(variance,value))/q else NA_real_
    joint_rows[[length(joint_rows)+1]] <- data.frame(test=name,covariance=covariance,
      statistic=statistic,p=pf(statistic,q,model$df,lower.tail=FALSE))
  }
}
write.csv(do.call(rbind,joint_rows),file.path(folder,'r-joint-tests.csv'),row.names=FALSE,na='')
slopes <- list(); model <- fitted_models[['regional_slopes']]
for(region in c('Northeast','Midwest','South','West')) {
  contrast <- setNames(rep(0,length(model$b)),names(model$b)); contrast['delta_treasury90'] <- 1
  if(region!='Northeast') contrast[paste0('rate_',tolower(region))] <- 1
  estimate <- sum(contrast*model$b); variance <- as.numeric(t(contrast)%*%model$two_way%*%contrast)
  se <- if(variance>=0) sqrt(variance) else NA_real_; critical <- qt(.975,model$df)
  slopes[[length(slopes)+1]] <- data.frame(region=region,estimate=estimate,se=se,
    low=estimate-critical*se,high=estimate+critical*se)
}
write.csv(do.call(rbind,slopes),file.path(folder,'r-regional-slopes.csv'),row.names=FALSE,na='')

for(pair in list(c('covariance_sensitivity.csv','r-covariance.csv'),
                 c('joint_test_sensitivity.csv','r-joint-tests.csv'),
                 c('regional_slopes.csv','r-regional-slopes.csv'))) {
  reference <- read.csv(file.path(folder,pair[1]),stringsAsFactors=FALSE)
  actual <- read.csv(file.path(folder,pair[2]),stringsAsFactors=FALSE)
  for(key in intersect(names(actual),c('model','covariance','term','test','region'))) stopifnot(identical(actual[[key]],reference[[key]]))
  for(key in intersect(names(actual),c('estimate','se','low','high','statistic','p'))) {
    stopifnot(identical(is.na(actual[[key]]),is.na(reference[[key]])),
              all(abs(actual[[key]]-reference[[key]])<1e-7,na.rm=TRUE))
  }
}

# Fit each earlier window independently; use saved IDs only to align the check.
saved <- read.csv(file.path(folder,'predictions.csv'),stringsAsFactors=FALSE)
main <- d[d$main_eligible,]
features <- c('treasury90','curve90','inflation','stress','duration','distribution','unemployment')
prediction_records <- list()
for(start in c(2000,2005,2010,2015,2020)) {
  train <- main[main$year<start,]; test <- main[main$year>=start & main$year<=start+4,]
  if(nrow(train)<100 || !nrow(test)) next
  stopifnot(max(train$authorized_date)<min(test$authorized_date))
  row <- data.frame(id=test$id,training_mean=mean(train$roe),previous_award=test$prior)
  for(name in c('market_case','with_prior')) {
    terms <- c(features,if(name=='with_prior') 'prior')
    model <- lm(as.formula(paste('roe ~',paste(terms,collapse='+'))),data=train)
    row[[name]] <- predict(model,newdata=test)
  }
  prediction_records[[length(prediction_records)+1]] <- row
}
predictions <- do.call(rbind,prediction_records)
stopifnot(identical(predictions$id,saved$id))
for(name in c('training_mean','previous_award','market_case','with_prior')) {
  stopifnot(all(abs(predictions[[name]]-saved[[name]])<1e-8))
}
write.csv(predictions,file.path(folder,'r-predictions.csv'),row.names=FALSE)

annual <- aggregate(cbind(roe,prior)~year,data=main,FUN=mean)
png(file.path(folder,'r-history.png'),width=1700,height=950,res=180)
par(mar=c(4.5,4.5,2.8,1),bty='l',family='sans',col.axis='#303633',col.lab='#303633')
plot(annual$year,annual$roe,type='l',lwd=2,col='#244d42',ylim=range(annual$roe,annual$prior),
     xlab='Authorization year',ylab='Allowed ROE (%)',main='Current and previous awards, expanded estimation sample')
lines(annual$year,annual$prior,lty=2,lwd=1.5,col='#808782')
legend('topright',c('Current award','Prior award'),col=c('#244d42','#808782'),lty=c(1,2),bty='n')
dev.off()
cat(sprintf('R expanded study passed: %d coefficient/SE/interval rows and %d predictions for each of four rules.\n',
            nrow(checked),nrow(predictions)))
