* Request and decision models using built-in Stata 17+ commands.
* Run from the repository root: do analysis/filing.do
version 17
clear all
set more off
local folder "reports/filing-study"
import delimited "`folder'/panel.csv", clear varnames(1) case(preserve) bindquote(strict)
foreach flag in stage_eligible prior_eligible forecast_eligible {
    capture confirm string variable `flag'
    if !_rc replace `flag' = lower(`flag')
}
encode state, gen(state_id)
encode entity, gen(entity_id)
encode quarter, gen(quarter_id)
egen intersection = group(state_id quarter_id)
gen filing_day = daily(requested_date,"YMD")
gen decision_day = daily(authorized_date,"YMD")
gen prior_day = daily(known_prior_date,"YMD")
assert prior_day < filing_day if known_prior < .
tempfile panel
save `panel'
frame create specifications
frame specifications: import delimited "`folder'/model_specs.csv", clear varnames(1) stringcols(_all)
frame specifications: count
local count = r(N)
tempname output
postfile `output' str60 model str30 term double estimate se low high using "`folder'/stata-coefficients.dta", replace
forvalues i = 1/`count' {
    foreach key in model flag target features effects weight {
        frame specifications: local `key' = `key'[`i']
    }
    use `panel', clear
    keep if `flag' == "true"
    local terms : subinstr local features ";" " ", all
    local fixed "i.state_id i.year"
    if "`effects'" == "entity_year" local fixed "i.entity_id i.year"
    bysort decision_day_group: gen inverse_group = 1/_N
    local weight_option ""
    if "`weight'" == "decision_days" local weight_option "[aw=inverse_group]"
    quietly regress `target' `terms' `fixed' `weight_option', vce(cluster state_id)
    matrix VS = e(V)
    matrix B = e(b)
    local gs = e(N_clust)
    quietly regress `target' `terms' `fixed' `weight_option', vce(cluster quarter_id)
    matrix VQ = e(V)
    local gq = e(N_clust)
    quietly regress `target' `terms' `fixed' `weight_option', vce(cluster intersection)
    matrix V = VS + VQ - e(V)
    local critical = invttail(min(`gs',`gq')-1,.025)
    foreach term of local terms {
        local j = colnumb(B,"`term'")
        local b = B[1,`j']
        local se = cond(V[`j',`j']>=0,sqrt(V[`j',`j']),.)
        post `output' ("`model'") ("`term'") (`b') (`se') (`b'-`critical'*`se') (`b'+`critical'*`se')
    }
}
postclose `output'
use "`folder'/stata-coefficients.dta", clear
export delimited using "`folder'/stata-coefficients.csv", replace
import delimited "`folder'/annual.csv", clear varnames(1)
twoway (line mean_request year, lcolor(black)) (line mean_award year, lcolor(forest_green)), ///
    ytitle("Return on equity (%)") xtitle("Authorization year") ///
    legend(order(1 "Requested" 2 "Authorized")) graphregion(color(white))
graph export "`folder'/stata-requests-awards.png", replace width(1800)
display "Native Stata output requires comparison with coefficients.csv before being reported as verified."
