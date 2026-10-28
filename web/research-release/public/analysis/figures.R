# Anchored Returns | Kazi Rafsan Mahboob
# Base R figures from validated real-record exports. No package installation.
# Rscript --vanilla analysis/figures.R INPUT_DIRECTORY OUTPUT_DIRECTORY
args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 2L) stop("Supply the data directory and a figure directory")
input <- normalizePath(args[1], mustWork=TRUE)
output <- args[2]
dir.create(output, recursive=TRUE, showWarnings=FALSE)
read_table <- function(name) read.csv(file.path(input, paste0(name, ".csv")),
                                    stringsAsFactors=FALSE, na.strings=c("", "NA"))
outcomes <- read_table("outcomes")
coding <- read_table("coding")
benchmarks <- read_table("benchmarks")
stopifnot(!anyDuplicated(outcomes$case_id), !anyDuplicated(paste(coding$case_id,coding$code)))
stopifnot(all(coding$relied+coding$considered+coding$rejected+coding$absent == coding$denominator))
pairs <- subset(outcomes, !is.na(request_pct) & !is.na(award_pct))
gap <- (pairs$award_pct-pairs$request_pct)*100
stopifnot(all(abs(gap-pairs$gap_bp)<1e-8))
write.csv(data.frame(case_id=pairs$case_id,gap_bp=gap),file.path(output,"checks.csv"),row.names=FALSE)
ink <- "#263638"; teal <- "#207A77"; gold <- "#D09550"; muted <- "#687D99"
stance_colors <- c(teal,"#A9C6C2","#BE7959","#EEF1F0")
figure <- function(name, width, height, draw) {
  for (type in c("pdf", "png")) {
    file <- file.path(output,paste0(name,".",type))
    if (type == "pdf") pdf(file,width=width,height=height,family="Helvetica",useDingbats=FALSE)
    else png(file,width=width,height=height,units="in",res=200,type="cairo")
    par(fg=ink,col.axis=ink,col.lab=ink,col.main=ink,bg="white",family="sans",las=1)
    draw()
    dev.off()
  }
}
figure("request_award",11,7.2,function() {
  d <- outcomes[order(outcomes$order_date,outcomes$case_id),]
  n <- nrow(d); y <- rev(seq_len(n))
  values <- c(d$request_pct,d$award_pct)
  limits <- c(floor(min(values,na.rm=TRUE)*2)/2-.2,ceiling(max(values,na.rm=TRUE)*2)/2+.8)
  par(mar=c(6.5,9.2,5.7,3),xpd=NA)
  plot(NA,xlim=limits,ylim=c(.4,n+.6),xlab="Return on equity (%)",ylab="",yaxt="n",bty="n")
  abline(v=pretty(limits),col="#EBEFED",lwd=1)
  docket_label <- sub("^.* / ","",d$docket)
  shared_ct <- grepl("CAND-CT-23-11-02",d$case_id)
  docket_label[shared_ct] <- paste(docket_label[shared_ct],ifelse(grepl("CNG$",d$case_id[shared_ct]),"CNG","SCG"))
  axis(2,at=y,labels=paste(d$state,docket_label,sep=" / "),tick=FALSE,cex.axis=.85)
  ok <- !is.na(d$request_pct)&!is.na(d$award_pct)
  segments(d$request_pct[ok],y[ok],d$award_pct[ok],y[ok],col="#9FAFAF",lwd=2)
  points(d$request_pct,y,pch=1,col=teal,cex=1.3,lwd=2)
  is_settlement <- !is.na(d$award_kind)&d$award_kind=="approved_settlement"
  points(d$award_pct[!is_settlement],y[!is_settlement],pch=16,col=gold,cex=1.3)
  points(d$award_pct[is_settlement],y[is_settlement],pch=18,col=muted,cex=1.5)
  labels <- ifelse(is.na(d$gap_bp),"Request missing",ifelse(d$gap_bp==0,"0 bp",sprintf("%+.0f bp",d$gap_bp)))
  text(rep(limits[2]-.01,n),y,labels,adj=1,cex=.82,col=ink)
  title("Requested and allowed returns",adj=0,line=3.8,cex.main=1.3)
  mtext(sprintf("%d entered decisions | %d complete request-award pairs | provisional evidence",n,nrow(pairs)),
        side=3,line=2.6,adj=0,cex=.86)
  legend("topleft",inset=c(0,-.085),legend=c("Company request","Commission award","Approved settlement"),
         pch=c(1,16,18),col=c(teal,gold,muted),horiz=TRUE,bty="n",cex=.8)
  mtext("Sources: original written orders; viewer pages, URLs and fingerprints in outcomes.csv.",
        side=1,line=4.2,adj=0,cex=.75)
  mtext("Differences include performance adjustments where recorded. Missing requests are not zero. No causal effect is estimated.",
        side=1,line=5.2,adj=0,cex=.75)
})
figure("evidence_stances",11,7.5,function() {
  layout(matrix(c(1,1,1,2,3,4,5,5,5),nrow=3,byrow=TRUE),heights=c(.75,5.7,.65))
  par(mar=c(0,0,0,0),oma=c(0,0,0,0))
  plot.new()
  text(.04,.76,"Evidence categories and stance",adj=0,font=2,cex=1.25)
  legend("bottom",inset=.02,legend=c("Relied on","Considered","Rejected","Not present"),
         fill=stance_colors,border=NA,horiz=TRUE,bty="n",cex=.85)
  par(mar=c(4.5,4.7,3,1.2))
  code_names <- c(MKT="Market evidence",PEER="Other regulators' awards",OWN="Own prior awards")
  for (code in c("MKT","PEER","OWN")) {
    d <- coding[coding$code==code,]
    d <- d[order(match(d$state,c("NH","ME","VT"))),]
    d <- d[nrow(d):1,]
    values <- as.matrix(d[,c("relied","considered","rejected","absent")])/d$denominator*100
    heights <- barplot(t(values),horiz=TRUE,col=stance_colors,border=NA,xlim=c(0,100),axes=FALSE,
                      names.arg=paste0(d$state,"\nn=",d$denominator),cex.names=.85,space=.6)
    axis(1,at=c(0,25,50,75,100),cex.axis=.8)
    for (i in seq_len(nrow(d))) {
      widths <- values[i,]; mid <- cumsum(widths)-widths/2
      for (j in which(widths>=8)) text(mid[j],heights[i],d[i,c("relied","considered","rejected","absent")][[j]],
                                     cex=.8,col=if(j==1) "white" else ink)
    }
    title(code_names[code],adj=0,line=2,cex.main=1)
    mtext("Share of units (%)",side=1,line=3.1,cex=.8)
  }
  par(mar=c(0,0,0,0))
  plot.new()
  text(.04,.72,"Counts are printed inside sufficiently wide segments. Exact counts remain in coding.csv.",adj=0,cex=.8)
  text(.04,.36,"First-pass codes; 45 units in three orders. Units are clustered, codes can overlap, and independent agreement is unmeasured.",
       adj=0,cex=.8)
})
figure("verified_benchmarks",10.5,5.7,function() {
  d <- benchmarks
  d$date <- as.Date(d$period_end)
  par(mar=c(7,5,5,2))
  plot(d$date,d$mean_pct,type="n",ylim=range(d$mean_pct)+c(-.10,.15),
       xlab="Covered half-year",ylab="Mean authorized ROE (%)",bty="n",xaxt="n")
  periods <- sort(unique(d$date))
  period_labels <- paste(format(periods,"%Y"),ifelse(as.integer(format(periods,"%m"))<=6,"H1","H2"))
  axis.Date(1,at=periods,labels=period_labels)
  abline(h=pretty(range(d$mean_pct)),col="#EBEFED")
  for (service in c("Electric","Gas")) {
    sub <- d[d$service==service,]
    color <- if(service=="Electric") teal else gold
    points(sub$date,sub$mean_pct,pch=if(service=="Electric") 16 else 17,col=color,cex=1.2)
    other <- d[d$service!=service,]
    other_values <- other$mean_pct[match(sub$period_end,other$period_end)]
    positions <- ifelse(sub$mean_pct >= other_values,3,1)
    text(sub$date,sub$mean_pct,labels=sprintf("%.2f",sub$mean_pct),pos=positions,cex=.8,col=color)
  }
  title("Verified national comparison points",adj=0,line=2.8,cex.main=1.2)
  legend("topleft",inset=c(0,-.085),legend=c("Electric","Gas"),pch=c(16,17),col=c(teal,gold),horiz=TRUE,bty="n",xpd=NA)
  mtext("Sources: original RRA reports reproduced in commission filings. General rate cases excluding riders; legacy dataset vintage.",
        side=1,line=4.1,adj=0,cex=.75)
  mtext("H2 2019 is reconstructed from complete case rows. Other means are publisher reported; missing periods are not interpolated.",
        side=1,line=5.1,adj=0,cex=.75)
})
cat(R.version.string,"\n")
