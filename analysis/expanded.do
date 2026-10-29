* Historical expansion. Uses built-in Stata commands, with no external packages.
* Prepared for native replication; execution requires a licensed Stata installation.
version 17.0
clear all
set more off
args folder
if "`folder'" == "" local folder "reports/expanded-study"
use "`folder'/panel.dta", clear
encode state, gen(state_id)
encode entity, gen(entity_id)
encode quarter, gen(quarter_id)
egen state_quarter = group(state_id quarter_id)
frame create specifications
frame specifications: import delimited "`folder'/model_specs.csv", clear stringcols(_all)
frame specifications: count
local models = r(N)
tempname results
postfile `results' str40 model str32 term double estimate se low high using "`folder'/stata-coefficients.dta", replace
forvalues i=1/`models' {
    frame specifications: local model = model[`i']
    frame specifications: local sample = sample[`i']
    frame specifications: local target = target[`i']
    frame specifications: local features = features[`i']
    frame specifications: local effects = effects[`i']
    local predictors = subinstr("`features'",";"," ",.)
    local controls ""
    if "`effects'" == "state_year" local controls "i.state_id i.year"
    if "`effects'" == "entity_year" local controls "i.entity_id i.year"
    preserve
    if "`sample'" == "main" keep if main_eligible
    if "`sample'" == "bridge" keep if main_eligible & year>=2010
    if "`sample'" == "change" keep if change_eligible
    if "`sample'" == "long" keep if long_eligible
    quietly regress `target' `predictors' `controls', vce(cluster state_id)
    matrix b = e(b)
    matrix VS = e(V)
    quietly levelsof state_id if e(sample), local(states)
    local gs: word count `states'
    quietly regress `target' `predictors' `controls', vce(cluster quarter_id)
    matrix VQ = e(V)
    quietly levelsof quarter_id if e(sample), local(quarters)
    local gq: word count `quarters'
    quietly regress `target' `predictors' `controls', vce(cluster state_quarter)
    matrix VI = e(V)
    matrix Vboth = VS + VQ - VI
    scalar critical = invttail(min(`gs',`gq')-1,.025)
    foreach term of local predictors {
        local j = colnumb(b,"`term'")
        scalar value = b[1,`j']
        scalar variance = Vboth[`j',`j']
        scalar se = cond(variance>=0,sqrt(variance),.)
        post `results' ("`model'") ("`term'") (value) (se) (value-critical*se) (value+critical*se)
    }
    restore
}
postclose `results'

* Expanding windows use earlier training years only. Coefficients stay fixed in a block.
local market treasury90 curve90 inflation stress duration distribution unemployment
foreach name in training_mean previous_award market_case with_prior {
    generate double p_`name' = .
}
foreach start in 2000 2005 2010 2015 2020 {
    quietly count if main_eligible & year<`start'
    if r(N)<100 continue
    local end = `start'+4
    quietly summarize roe if main_eligible & year<`start', meanonly
    replace p_training_mean = r(mean) if main_eligible & inrange(year,`start',`end')
    replace p_previous_award = prior if main_eligible & inrange(year,`start',`end')
    foreach name in market_case with_prior {
        local terms "`market'"
        if "`name'" == "with_prior" local terms "`market' prior"
        quietly regress roe `terms' if main_eligible & year<`start'
        tempvar prediction
        quietly predict double `prediction', xb
        replace p_`name' = `prediction' if main_eligible & inrange(year,`start',`end')
        drop `prediction'
    }
}
preserve
keep if !missing(p_with_prior)
keep id p_training_mean p_previous_award p_market_case p_with_prior
foreach name in training_mean previous_award market_case with_prior {
    rename p_`name' `name'
}
export delimited using "`folder'/stata-predictions.csv", replace
tempfile native_predictions
save `native_predictions'
restore
preserve
import delimited "`folder'/predictions.csv", clear
keep id training_mean previous_award market_case with_prior
foreach name in training_mean previous_award market_case with_prior {
    rename `name' expected_`name'
}
merge 1:1 id using `native_predictions', assert(match) nogen
foreach name in training_mean previous_award market_case with_prior {
    assert abs(`name'-expected_`name')<1e-8
}
restore

twoway scatter delta_roe delta_treasury90 if change_eligible, msize(vsmall) mcolor(forest_green%30) ///
    xtitle("Treasury change between decisions (pp)") ytitle("Allowed ROE change (pp)") ///
    legend(off) graphregion(color(white))
graph export "`folder'/stata-adjustments.png", replace width(1700)

* Compare point estimates and intervals with the checked Python export.
import delimited "`folder'/coefficients.csv", clear
keep model term estimate se low high
foreach key in estimate se low high {
    rename `key' expected_`key'
}
tempfile expected
save `expected'
use "`folder'/stata-coefficients.dta", clear
merge 1:1 model term using `expected', assert(match) nogen
foreach key in estimate se low high {
    assert missing(`key')==missing(expected_`key')
    assert abs(`key'-expected_`key')<1e-7 if !missing(`key')
}
export delimited using "`folder'/stata-crosscheck.csv", replace
display "Expanded-study coefficient and interval checks passed."
