* Native Stata reproduction. Point estimates and two-way state/quarter covariance.
* Supplied for reproduction; not executed in this release.
clear all
set more off
args folder
if "`folder'" == "" local folder "reports/factor-study"
import delimited "`folder'/estimation.csv", clear varnames(1)
encode state, gen(state_id)
encode entity, gen(entity_id)
encode quarter, gen(quarter_id)
egen state_quarter = group(state_id quarter_id)
local predictors treasury90 curve90 inflation stress duration distribution prior
pwcorr roe `predictors', obs
spearman roe prior
foreach model in pooled state_year entity_year {
    local effects ""
    if "`model'" == "state_year" local effects "i.state_id i.year"
    if "`model'" == "entity_year" local effects "i.entity_id i.year"
    quietly regress roe `predictors' `effects', vce(cluster state_id)
    matrix VA = e(V)
    quietly regress roe `predictors' `effects', vce(cluster quarter_id)
    matrix VB = e(V)
    quietly regress roe `predictors' `effects', vce(cluster state_quarter)
    matrix VAB = e(V)
    matrix Vboth = VA + VB - VAB
    ereturn repost V=Vboth
    estimates store `model'
    * The paper uses normal Wald intervals; Stata's default table uses t intervals.
    display "`model': coefficient and two-way clustered standard errors"
    matrix list e(b)
    matrix list e(V)
}
twoway (scatter roe prior, msize(vsmall) mcolor(navy%35)) (function y=x, range(7 13) lpattern(dash) lcolor(gs9)), xtitle("Previous recorded award (%)") ytitle("Authorized ROE (%)") legend(off) graphregion(color(white))
graph export "`folder'/persistence-stata.png", replace width(1700)
