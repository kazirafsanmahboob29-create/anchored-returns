# Reproduce the core OLS estimates, clustered intervals and figures using base R.
args <- commandArgs(trailingOnly=TRUE)
folder <- if(length(args)) args[1] else 'reports/factor-study'
d <- read.csv(file.path(folder,'estimation.csv'),stringsAsFactors=FALSE)
expected <- read.csv(file.path(folder,'coefficients.csv'),stringsAsFactors=FALSE)
variables <- c('treasury90','curve90','inflation','stress','duration','distribution','prior')
specs <- list(market_case=variables[1:6],with_prior=variables,state_year=variables,entity_year=variables)
records <- list()
for(name in names(specs)) {
  controls <- if(name=='state_year') 'factor(state)+factor(year)' else if(name=='entity_year') 'factor(entity)+factor(year)' else ''
  form <- as.formula(paste('roe ~',paste(c(specs[[name]],if(nchar(controls)) controls),collapse='+')))
  model <- lm(form,data=d)
  X <- model.matrix(model); u <- residuals(model); bread <- solve(crossprod(X)); n <- nrow(X); k <- ncol(X)
  cluster <- function(group) {
    scores <- rowsum(X*as.numeric(u),group,reorder=FALSE)
    g <- nrow(scores)
    (g/(g-1))*((n-1)/(n-k))*bread%*%crossprod(scores)%*%bread
  }
  V <- cluster(d$state)+cluster(d$quarter)-cluster(paste(d$state,d$quarter,sep='|'))
  for(term in specs[[name]]) {
    value <- unname(coef(model)[term]); variance <- V[term,term]
    se <- if(variance>0) sqrt(variance) else NA_real_
    reference <- expected[expected$model==name & expected$term==term,]
    stopifnot(nrow(reference)==1,abs(value-reference$estimate)<1e-7,abs(se-reference$se)<1e-7)
    records[[length(records)+1]] <- data.frame(model=name,term=term,estimate=value,se=se)
  }
}
crosscheck <- do.call(rbind,records)
write.csv(crosscheck,file.path(folder,'r-crosscheck.csv'),row.names=FALSE)
rho <- cor(d$roe,d$prior,method='pearson'); rank_rho <- cor(d$roe,d$prior,method='spearman')
write.csv(data.frame(n=nrow(d),pearson=rho,spearman=rank_rho),file.path(folder,'r-correlations.csv'),row.names=FALSE)

ink <- '#2f3339'; blue <- '#345e78'; pale <- '#cedbe3'
png(file.path(folder,'persistence.png'),width=1700,height=1000,res=180)
par(mar=c(4.5,4.5,2.4,1),fg=ink,col.axis=ink,col.lab=ink,bty='l',family='sans')
plot(d$prior,d$roe,pch=16,cex=.65,col=adjustcolor(blue,alpha.f=.35),xlab='Previous recorded award (%)',ylab='Authorized ROE (%)',main='How closely do awards track the previous recorded return?')
abline(a=0,b=1,col='#9aa7b0',lty=2)
legend('topleft',legend=c(paste(nrow(d),'complete observations'),sprintf('Pearson r = %.3f',rho),'Dashed line: unchanged award'),bty='n',cex=.8)
dev.off()

png(file.path(folder,'coefficients.png'),width=1800,height=1150,res=180)
par(mar=c(6,7.6,3,1),fg=ink,col.axis=ink,col.lab=ink,bty='n',family='sans')
z <- subset(expected,term %in% c('treasury90','prior') & model %in% names(specs))
positions <- c(7,6,5,4,2,1,0)
order <- match(paste(c(rep('treasury90',4),rep('prior',3)),c(names(specs),names(specs)[2:4])),paste(z$term,z$model))
z <- z[order,]
labels <- c('Market + case','Add prior award','State + year','Utility-state + year','Add prior award','State + year','Utility-state + year')
plot(NA,xlim=range(c(z$low,z$high,0),na.rm=TRUE),ylim=c(-.8,8.4),xlab='ROE percentage points per one percentage-point increase',ylab='',yaxt='n',main='Market and prior-award coefficients')
abline(v=0,col=pale,lty=2)
segments(z$low,positions,z$high,positions,col=blue,lwd=1.5)
points(z$estimate,positions,pch=16,col=blue,cex=.8)
axis(2,at=positions,labels=labels,las=1,tick=FALSE,cex.axis=.8)
text(par('usr')[1],8,'10-year Treasury yield',adj=0,font=2,cex=.85)
text(par('usr')[1],3,'Previous recorded award',adj=0,font=2,cex=.85)
mtext('95% intervals, clustered by state and authorization quarter. Same 533 observations.',side=1,line=4.6,cex=.65)
dev.off()
cat(sprintf('R crosscheck passed: %d coefficient and clustered-SE pairs; Pearson %.12f; Spearman %.12f.\n',nrow(crosscheck),rho,rank_rho))
